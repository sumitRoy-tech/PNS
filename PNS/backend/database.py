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
    
    # Relationship to functional assessments
    assessments = relationship("FunctionalAssessment", back_populates="project")
    
    # Relationship to technical committee reviews
    technical_reviews = relationship("TechnicalCommitteeReview", back_populates="project")
    
    # Relationship to generated RFPs
    generated_rfps = relationship("GeneratedRFP", back_populates="project")
    
    # Relationship to tender drafts
    tender_drafts = relationship("TenderDraft", back_populates="project")
    
    # Relationship to publish RFPs
    publish_rfps = relationship("PublishRFP", back_populates="project")
    
    # Relationship to vendor bids
    vendor_bids = relationship("VendorBid", back_populates="project")


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


class FunctionalAssessment(Base):
    __tablename__ = "functional_assessments"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)  # Business ID for easy lookup

    # ASSESSMENT FIELDS
    functional_fit_assessment = Column(Text, nullable=False)
    technical_feasibility = Column(Text, nullable=False)
    risk_assessment = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=False)

    # STATUS
    status = Column(String(50), default="submitted")  # submitted, reviewed, approved, rejected

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="assessments")


class TechnicalCommitteeReview(Base):
    __tablename__ = "technical_committee_reviews"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)  # Business ID for easy lookup

    # REVIEW FIELDS
    architecture_review = Column(Text, nullable=False)
    security_assessment = Column(Text, nullable=False)
    integration_complexity = Column(Text, nullable=False)
    rbi_compliance_check = Column(Text, nullable=False)
    technical_committee_recommendation = Column(Text, nullable=False)

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="technical_reviews")


class GeneratedRFP(Base):
    __tablename__ = "generated_rfps"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)

    # RFP CONTENT
    rfp_content = Column(Text, nullable=False)  # Full RFP text content
    rfp_filename = Column(String(255), nullable=False)  # PDF filename
    rfp_filepath = Column(String(500), nullable=False)  # Full path to PDF

    # VERSION CONTROL
    version = Column(Integer, default=1)

    # METADATA
    generated_by = Column(String(100), default="Claude AI")
    file_size_kb = Column(Float, nullable=True)

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="generated_rfps")


class TenderDraft(Base):
    __tablename__ = "tender_drafts"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)

    # TENDER FIELDS
    rfp_template = Column(String(255), nullable=False)  # Select RFP Template
    bid_validity_period = Column(Integer, nullable=False)  # Days only (e.g., 60, 90)
    submission_deadline = Column(DateTime, nullable=False)  # Date
    emd_amount = Column(Float, nullable=False)  # Number only
    eligibility_criteria = Column(Text, nullable=False)

    # AUTHORITY DECISION (0 = Rejected, 1 = Approved)
    authority_decision = Column(Integer, nullable=True, default=None)

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="tender_drafts")


class PublishRFP(Base):
    __tablename__ = "publish_rfps"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)

    # PUBLICATION CHANNELS (0 = No, 1 = Yes)
    bank_website = Column(Integer, nullable=False, default=0)
    cppp = Column(Integer, nullable=False, default=0)
    newspaper_publication = Column(Integer, nullable=False, default=0)
    gem_portal = Column(Integer, nullable=False, default=0)

    # DATES
    publication_date = Column(DateTime, nullable=True)
    pre_bid_meeting = Column(DateTime, nullable=True)
    query_last_date = Column(DateTime, nullable=True)
    bid_opening_date = Column(DateTime, nullable=True)

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="publish_rfps")


class VendorBid(Base):
    __tablename__ = "vendor_bids"

    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # FOREIGN KEY to project_credentials
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)

    # VENDOR INFO
    vendor_name = Column(String(255), nullable=False)

    tech_score = Column(Float, nullable=True)     # e.g. 45.6
    comm_score = Column(Float, nullable=True)     # e.g. 42.3
    total_score = Column(Float, nullable=True)
    
    # BID VALUES
    commercial_bid = Column(Float, nullable=False)  # Random value between 15000000-95000000
    technical_score = Column(Integer, nullable=False)  # Technical percentage (no % sign)
    
    # RANKING
    rank = Column(Integer, nullable=False)  # Rank based on commercial bid (lowest = 1)

    # TIMESTAMPS
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to project
    project = relationship("ProjectCredential", back_populates="vendor_bids")


def init_db():
    Base.metadata.create_all(bind=engine)
