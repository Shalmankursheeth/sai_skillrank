import json
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from typing import Optional
from sqlmodel import Session, create_engine
from pypdf import PdfReader
from backend.app.db import get_session
from backend.app.models import Candidate, SQLModel
from backend.app.services.llm_client import extract_skills

router = APIRouter()

def _extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        reader = PdfReader(stream=data)
    except Exception:
        # older pypdf uses PdfReader(BytesIO(data)) fallback
        from io import BytesIO
        reader = PdfReader(BytesIO(data))
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            # ignore per-page extraction errors
            continue
    return "\n".join(texts).strip()

def _background_extract_and_save(cid: int):
    # run LLM extraction and save to DB (background)
    import json
    from sqlmodel import Session as DBSession
    from sqlmodel import create_engine as _create_engine
    from backend.app.models import Candidate as DBCandidate
    from backend.app.services.llm_client import extract_skills as _extract_skills

    engine = _create_engine("sqlite:///./llm_job_portal.db", echo=False)
    with DBSession(engine) as s:
        c = s.get(DBCandidate, cid)
        if not c or not (c.resume_text and c.resume_text.strip()):
            return
        try:
            skills = _extract_skills(c.resume_text)
            c.extracted_skills = json.dumps(skills)
            s.add(c)
            s.commit()
        except Exception as e:
            import sys
            print(f"Background extraction failed for candidate {cid}: {e}", file=sys.stderr)

@router.post("/resumes")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    run_extract: Optional[bool] = Form(False),
    session: Session = Depends(get_session),
):
    """
    Upload a PDF resume, extract text, create Candidate.
    If run_extract=true (form field), schedule background skill extraction.
    """
    # validate content type (simple check)
    if not (file.content_type and ("pdf" in file.content_type.lower())):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = await file.read()
    text = _extract_text_from_pdf_bytes(data)
    if not text:
        raise HTTPException(status_code=400, detail="Unable to extract text from PDF")

    # create candidate
    cand = Candidate(name=name or "Uploaded Candidate", email=email, resume_text=text)
    session.add(cand)
    session.commit()
    session.refresh(cand)

    # schedule background extraction if requested
    if run_extract:
        background_tasks.add_task(_background_extract_and_save, cand.id)

    # return basic candidate info (extracted_skills may be null initially)
    try:
        skills = json.loads(cand.extracted_skills) if cand.extracted_skills else None
    except Exception:
        skills = None

    return {
        "id": cand.id,
        "name": cand.name,
        "email": cand.email,
        "resume_text_snippet": (cand.resume_text[:800] + "...") if len(cand.resume_text) > 800 else cand.resume_text,
        "extracted_skills": skills,
        "uploaded_at": str(cand.uploaded_at),
    }
