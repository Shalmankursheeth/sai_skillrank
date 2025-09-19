# backend/app/services/matcher.py
from typing import List, Tuple, Dict, Set
import re

# Small synonym map to canonicalize common variants.
_SYNONYMS = {
    "js": "javascript",
    "nodejs": "node.js",
    "node": "node.js",
    "nlp": "natural language processing",
    "aws s3": "aws",
}

def canonicalize(skills: List[str]) -> List[str]:
    out = []
    for s in skills:
        if not s:
            continue
        s2 = s.strip().lower()
        # remove extra punctuation
        s2 = re.sub(r"[^\w.+# ]", " ", s2)
        s2 = re.sub(r"\s+", " ", s2).strip()
        # map synonyms
        if s2 in _SYNONYMS:
            s2 = _SYNONYMS[s2]
        out.append(s2)
    # dedupe preserving order
    seen = set()
    dedup = []
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup

def jaccard_score(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 100.0
    if not a or not b:
        return 0.0
    inter = a.intersection(b)
    union = a.union(b)
    return (len(inter) / len(union)) * 100.0

def match_resume_to_job(candidate_skills: List[str], job_skills: List[str]) -> Dict[str, any]:
    """
    Returns:
      {
        "score": float (0-100),
        "matching_skills": [...],
        "missing_skills": [...],
        "candidate_skills_canonical": [...],
        "job_skills_canonical": [...]
      }
    """
    cand = canonicalize(candidate_skills)
    job = canonicalize(job_skills)

    set_cand = set(cand)
    set_job = set(job)

    score = jaccard_score(set_cand, set_job)

    matching = sorted(list(set_cand.intersection(set_job)))
    missing = sorted(list(set_job.difference(set_cand)))

    return {
        "score": round(score, 2),
        "matching_skills": matching,
        "missing_skills": missing,
        "candidate_skills_canonical": cand,
        "job_skills_canonical": job,
    }

