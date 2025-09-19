import json, sys
from sqlmodel import create_engine, Session
from backend.app.models import Candidate, SQLModel
from backend.app.services.llm_client import extract_skills

CID = 2  # change to the candidate id you want to process

engine = create_engine("sqlite:///./llm_job_portal.db", echo=False)
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    cand = session.get(Candidate, CID)
    if not cand:
        print("candidate not found:", CID); sys.exit(1)
    text = cand.resume_text or ""
    if not text.strip():
        print("no resume_text to extract"); sys.exit(1)
    skills = extract_skills(text)
    cand.extracted_skills = json.dumps(skills)
    session.add(cand)
    session.commit()
    print("Updated candidate", CID, "with skills:", skills)
