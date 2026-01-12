from sqlalchemy import (
    create_engine, Column, String, Float, DateTime,
    Integer, Text, ForeignKey, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DB_NAME = "RFP_Creation_Project"
DB_USER = "root"
DB_PASSWORD = "12345"
DB_HOST = "localhost"

engine_no_db = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}"
)

with engine_no_db.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ProjectCredential(Base):
    __tablename__ = "project_credentials"

    pk_id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    id = Column(String(50), unique=True, index=True)

    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False)
    estimated_amount = Column(Float, nullable=False)
    business_justification = Column(String(1000), nullable=False)
    submitted_by = Column(String(255), nullable=False)

    technical_specification = Column(String(1000), nullable=True)
    expected_timeline = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("UploadedFile", back_populates="project")
    
    assessments = relationship("FunctionalAssessment", back_populates="project")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)  

    label = Column(String(10), nullable=False) 
    original_filename = Column(String(255), nullable=False)
    saved_filename = Column(String(255), nullable=False, unique=True)
    file_extension = Column(String(20), nullable=False)
    file_size_kb = Column(Float, nullable=False)
    content_type = Column(String(100), nullable=True)

    faiss_index_id = Column(Integer, nullable=True)  
    text_extracted = Column(Text, nullable=True)  


    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="files")


class FunctionalAssessment(Base):
    __tablename__ = "functional_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True) 

    functional_fit_assessment = Column(Text, nullable=False)
    technical_feasibility = Column(Text, nullable=False)
    risk_assessment = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=False)

    status = Column(String(50), default="submitted")  

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    project = relationship("ProjectCredential", back_populates="assessments")


def init_db():
    Base.metadata.create_all(bind=engine)
