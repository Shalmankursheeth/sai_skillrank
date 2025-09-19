from sqlmodel import create_engine, Session, SQLModel, select
from backend.app.models import Job, Candidate
import json

engine = create_engine("sqlite:///./llm_job_portal.db", echo=True)
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    # insert job if none
    res = session.exec(select(Job)).all()
    if not res:
        job = Job(
            title="ML Engineer",
            company="Acme",
            description="Experience with python, pytorch, nlp, aws",
            extracted_skills=json.dumps(["python","pytorch","natural language processing","aws"])
        )
        session.add(job)
        session.commit()
        print("Inserted job id", job.id)
    else:
        print("Job exists, id:", res[0].id)

    # insert candidate if none
    res = session.exec(select(Candidate)).all()
    if not res:
        cand = Candidate(
            name="Test Candidate",
            email="test@example.com",
            resume_text="Experienced with python and pytorch for NLP projects.",
            extracted_skills=json.dumps(["python","pytorch","nlp"])
        )
        session.add(cand)
        session.commit()
        print("Inserted candidate id", cand.id)
    else:
        print("Candidate exists, id:", res[0].id)
