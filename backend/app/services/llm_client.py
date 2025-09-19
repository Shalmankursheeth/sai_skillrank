# backend/app/services/llm_client.py
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment (.env)")

# Initialize client (uses the new OpenAI python client)
_client = OpenAI(api_key=API_KEY)

# Choose models mindfully. For skill extraction use a cheaper model.
SKILL_EXTRACT_MODEL = "gpt-4o-mini"    # replace with available model in your account
EXPLAIN_MODEL = "gpt-4o-mini"

def _call_model(prompt: str, model: str = SKILL_EXTRACT_MODEL, max_tokens: int = 256) -> str:
    """
    Calls the OpenAI Responses API and returns the raw text output.
    Keeps the wrapper centralized so we can add retry/backoff later.
    """
    # The OpenAI python client returns structured objects; use `content` extraction.
    resp = _client.responses.create(model=model, input=prompt, max_output_tokens=max_tokens, temperature=0.0)
    # response structure: resp.output[0].content[0].text  OR resp.output_text
    # Newer SDKs have resp.output[0].content[0].text or resp.output_text; we try both.
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    # fallback parse
    try:
        outputs = resp.output
        if outputs and len(outputs) > 0:
            first = outputs[0]
            if hasattr(first, "content") and first.content:
                # content is a list of dicts with 'text'
                for c in first.content:
                    if isinstance(c, dict) and "text" in c:
                        return c["text"]
    except Exception:
        pass

    # last fallback: convert to string
    return str(resp)

# ---------- Skill extraction ----------
SKILL_PROMPT_TEMPLATE = """You are a compact skill extractor. Given the following text (resume or job description), return a JSON array (only the JSON array) of canonical skill phrases or technologies mentioned. Make each item short (single technology or concept), lowercase, and deduplicated.

Text:
\"\"\"{text}\"\"\"

Output (example): ["python", "fastapi", "sql", "unit testing"]
"""

def extract_skills(text: str, model: str = SKILL_EXTRACT_MODEL) -> List[str]:
    """
    Returns a list of extracted skills from text. Uses LLM and then does a safe JSON parse.
    """
    prompt = SKILL_PROMPT_TEMPLATE.format(text=text[:3000])  # keep prompt reasonably sized
    raw = _call_model(prompt, model=model, max_tokens=256)

    # Try to find JSON array in the output and parse it.
    # Be defensive: model may add backticks or explanation.
    try:
        # Find first '[' and last ']' and parse substring
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            arr_text = raw[start:end+1]
            parsed = json.loads(arr_text)
            if isinstance(parsed, list):
                # normalize whitespace and lowercase
                skills = [s.strip().lower() for s in parsed if isinstance(s, str)]
                # dedupe while preserving order
                seen = set()
                deduped = []
                for s in skills:
                    if s not in seen:
                        seen.add(s)
                        deduped.append(s)
                return deduped
    except Exception:
        pass

    # fallback: simple newline split heuristic
    lines = [l.strip().strip("-•* ") for l in raw.splitlines() if l.strip()]
    # keep only short tokens
    candidates = []
    for l in lines:
        if 1 <= len(l) <= 60:
            candidates.append(l.lower())
    # dedupe
    seen = set()
    out = []
    for s in candidates:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

# ---------- Explanation generator ----------
EXPLANATION_PROMPT = """
You are an assistant that writes concise match explanations between a candidate and a job.

Candidate skills: {candidate_skills}
Job skills: {job_skills}
Match score (0-100): {score}

Provide a JSON object only with these keys:
- explanation: a 1-2 sentence plain-language summary of fit.
- recommendations: an array of 1-4 short recommendations (skills to learn or steps).

Example output:
{{"explanation":"...","recommendations":["...","..."]}}
"""

def explain_match(candidate_skills: List[str], job_skills: List[str], score: float, model: str = EXPLAIN_MODEL) -> Dict[str, Any]:
    prompt = EXPLANATION_PROMPT.format(
        candidate_skills=candidate_skills,
        job_skills=job_skills,
        score=round(score, 2),
    )
    raw = _call_model(prompt, model=model, max_tokens=220)

    # Try to parse JSON object
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj_text = raw[start:end+1]
            parsed = json.loads(obj_text)
            return parsed
    except Exception:
        pass

    # fallback: return weakly structured result
    return {"explanation": raw.strip()[:400], "recommendations": []}

