import json
from fastapi import FastAPI, Depends, UploadFile, File, APIRouter,  HTTPException
from backend.app.api.matches import router as matches_router
from backend.app.api.candidates import router as candidates_router
from .services.llm_client import extract_skills, explain_match
from .services.matcher import match_resume_to_job
from sqlmodel import Session, select
from .db import init_db, get_session
from .models import Job, Candidate
from fastapi.middleware.cors import CORSMiddleware
import pypdf

app = FastAPI()
router = APIRouter()

app.include_router(matches_router)
app.include_router(candidates_router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def root():
    return {"message": "LLM Job Portal backend is running 🚀"}

@app.post("/jobs")
def create_job(job: Job, session: Session = Depends(get_session)):
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

@app.get("/jobs")
def list_jobs(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job)).all()
    return jobs

@app.post("/resumes")
async def upload_resume(file: UploadFile = File(...), session: Session = Depends(get_session)):
    text = ""
    if file.filename.endswith(".pdf"):
        reader = pypdf.PdfReader(file.file)
        for page in reader.pages:
            text += page.extract_text() or ""
    candidate = Candidate(name=file.filename, resume_text=text)
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return {"id": candidate.id, "resume_text_preview": text[:200]}

@router.post("/matches/simple")
def compute_match(candidate_id: int, job_id: int, session = Depends(get_session)):
    candidate = session.get(Candidate, candidate_id)
    job = session.get(Job, job_id)
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="candidate or job not found")

    # ensure we have extracted skills (lazy)
    if not candidate.extracted_skills:
        skills_cand = extract_skills(candidate.resume_text or "")
        candidate.extracted_skills = json.dumps(skills_cand)
        session.add(candidate)
        session.commit()
    else:
        skills_cand = json.loads(candidate.extracted_skills)

    if not job.extracted_skills:
        skills_job = extract_skills(job.description or "")
        job.extracted_skills = json.dumps(skills_job)
        session.add(job)
        session.commit()
    else:
        skills_job = json.loads(job.extracted_skills)

    match = match_resume_to_job(skills_cand, skills_job)
    explanation = explain_match(skills_cand, skills_job, match["score"])
    return {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "score": match["score"],
        "matching_skills": match["matching_skills"],
        "missing_skills": match["missing_skills"],
        "explanation": explanation.get("explanation"),
        "recommendations": explanation.get("recommendations"),
    }
# include candidates router
from backend.app.api.candidates import router as candidates_router
app.include_router(candidates_router)

# include resumes router
from backend.app.api.resumes import router as resumes_router
app.include_router(resumes_router)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # change to ["*"] only for dev if you prefer
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)