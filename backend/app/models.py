from sqlmodel import SQLModel, Field
from typing import Optional
import datetime

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    company: str
    location: Optional[str] = None
    description: str
    # New field: to store skills extracted by OpenAI
    extracted_skills: Optional[str] = None   # store JSON string
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    resume_text: Optional[str] = None
    # New field: to store extracted skills from resume
    extracted_skills: Optional[str] = None   # store JSON string
    uploaded_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidate.id")
    job_id: int = Field(foreign_key="job.id")
    score: float
    explanation: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
