import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Any
from backend.app.db import get_session
from backend.app.models import Candidate, Job, Match
from backend.app.services.llm_client import explain_match
from backend.app.services.matcher import match_resume_to_job

router = APIRouter()

@router.post("/matches/simple")
def compute_match(
    candidate_id: int,
    job_id: int,
    explain: bool = Query(False, description="If true, call LLM to generate explanation"),
    session: Session = Depends(get_session),
) -> Any:
    candidate = session.get(Candidate, candidate_id)
    job = session.get(Job, job_id)
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="candidate or job not found")

    try:
        skills_cand = json.loads(candidate.extracted_skills) if candidate.extracted_skills else []
    except Exception:
        skills_cand = []

    try:
        skills_job = json.loads(job.extracted_skills) if job.extracted_skills else []
    except Exception:
        skills_job = []

    match = match_resume_to_job(skills_cand, skills_job)

    explanation_text = None
    recommendations = []
    if explain:
        # will call the LLM (ensure OPENAI_API_KEY in .env and server restarted)
        explanation = explain_match(skills_cand, skills_job, match["score"])
        explanation_text = explanation.get("explanation")
        recommendations = explanation.get("recommendations") or []

    # persist match
    m = Match(candidate_id=candidate.id, job_id=job.id, score=match["score"], explanation=explanation_text or "explanation-skipped")
    session.add(m)
    session.commit()
    session.refresh(m)

    return {
        "match_id": m.id,
        "job_id": job.id,
        "candidate_id": candidate.id,
        "score": match["score"],
        "matching_skills": match["matching_skills"],
        "missing_skills": match["missing_skills"],
        "explanation": explanation_text or "explanation-skipped",
        "recommendations": recommendations,
    }
