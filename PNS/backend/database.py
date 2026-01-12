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

# Engine WITHOUT database
engine_no_db = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}"
)

# Create DB if not exists
with engine_no_db.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))

# Engine WITH database
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ProjectCredential(Base):
    __tablename__ = "project_credentials"

    # DATABASE-GENERATED PRIMARY KEY
    pk_id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # BUSINESS ID (HUMAN READABLE)
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

    # Relationship to uploaded files
    files = relationship("UploadedFile", back_populates="project")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)  # Business ID for easy lookup

    # FILE INFO
    label = Column(String(10), nullable=False)  # a, b, c, ...
    original_filename = Column(String(255), nullable=False)
    saved_filename = Column(String(255), nullable=False, unique=True)
    file_extension = Column(String(20), nullable=False)
    file_size_kb = Column(Float, nullable=False)
    content_type = Column(String(100), nullable=True)

    # VECTOR DB INFO
    faiss_index_id = Column(Integer, nullable=True)  # Position in FAISS index
    text_extracted = Column(Text, nullable=True)  # Extracted text for reference

    # TIMESTAMPS
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="files")


def init_db():
    Base.metadata.create_all(bind=engine)
