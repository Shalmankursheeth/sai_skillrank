import json
import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlmodel import Session
from typing import Optional, List
from backend.app.db import get_session
from backend.app.models import Candidate
from backend.app.services.llm_client import extract_skills

router = APIRouter()

class CandidateCreate(BaseModel):
    name: str = Field(..., example="Jane Doe")
    email: Optional[str] = Field(None, example="jane@example.com")
    resume_text: Optional[str] = Field(None, example="Experienced in python and fastapi")

class CandidateRead(BaseModel):
    id: int
    name: str
    email: Optional[str]
    resume_text: Optional[str]
    extracted_skills: Optional[List[str]] = None
    uploaded_at: Optional[str] = None

def _run_extraction_and_save(candidate_id: int):
    """
    Background worker: load candidate, call extract_skills, save JSON string to DB.
    Runs in-process; keep it small and guarded.
    """
    # local import to avoid circular issues in background threads
    from sqlmodel import create_engine, Session, select
    from backend.app.models import Candidate
    engine = create_engine("sqlite:///./llm_job_portal.db", echo=False)
    with Session(engine) as session:
        cand = session.get(Candidate, candidate_id)
        if not cand:
            return
        text = cand.resume_text or ""
        if not text.strip():
            return
        try:
            skills = extract_skills(text)
            cand.extracted_skills = json.dumps(skills)
            session.add(cand)
            session.commit()
        except Exception as e:
            # swallow exceptions in background task; log to stderr
            import sys
            print("Background extraction failed:", e, file=sys.stderr)

@router.post("/candidates", response_model=CandidateRead)
def create_candidate(
    payload: CandidateCreate,
    background_tasks: BackgroundTasks,
    run_extract: bool = False,
    session: Session = Depends(get_session),
):
    cand = Candidate(
        name=payload.name,
        email=payload.email,
        resume_text=payload.resume_text,
    )
    session.add(cand)
    session.commit()
    session.refresh(cand)

    # schedule background extraction if requested
    if run_extract and (cand.resume_text and cand.resume_text.strip()):
        background_tasks.add_task(_run_extraction_and_save, cand.id)

    # return candidate info (extracted_skills may be null initially)
    out = CandidateRead(
        id=cand.id,
        name=cand.name,
        email=cand.email,
        resume_text=cand.resume_text,
        extracted_skills=json.loads(cand.extracted_skills) if cand.extracted_skills else None,
        uploaded_at=str(cand.uploaded_at),
    )
    return out

@router.get("/candidates", response_model=List[CandidateRead])
def list_candidates(session: Session = Depends(get_session)):
    candidates = session.exec(select(Candidate)).all()
    out = []
    for c in candidates:
        try:
            skills = json.loads(c.extracted_skills) if c.extracted_skills else None
        except Exception:
            skills = None
        out.append(
            CandidateRead(
                id=c.id,
                name=c.name,
                email=c.email,
                resume_text=c.resume_text,
                extracted_skills=skills,
                uploaded_at=str(c.uploaded_at),
            )
        )
    return out

# ---- trigger extraction for an existing candidate ----
from fastapi import BackgroundTasks, status
from sqlmodel import create_engine, Session as DBSession

@router.put("/candidates/{candidate_id}/extract", status_code=202)
def trigger_candidate_extraction(candidate_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """
    Schedule skill extraction for an existing candidate.
    Returns 202 Accepted and schedules background extraction.
    """
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")
    if not (candidate.resume_text and candidate.resume_text.strip()):
        raise HTTPException(status_code=400, detail="candidate has no resume_text to extract")

    def _do_extract(cid: int):
        # local imports so background thread can safely import project modules
        import json
        from backend.app.services.llm_client import extract_skills
        # create a separate DB session for background work
        engine = create_engine("sqlite:///./llm_job_portal.db", echo=False)
        with DBSession(engine) as s:
            c = s.get(Candidate, cid)
            if not c or not (c.resume_text and c.resume_text.strip()):
                return
            try:
                skills = extract_skills(c.resume_text)
                c.extracted_skills = json.dumps(skills)
                s.add(c)
                s.commit()
            except Exception as e:
                # log to stderr so it appears in uvicorn logs
                import sys
                print(f"Background extraction failed for candidate {cid}: {e}", file=sys.stderr)

    background_tasks.add_task(_do_extract, candidate_id)
    return {"status": "scheduled", "candidate_id": candidate_id}
