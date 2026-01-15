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
    technical_reviews = relationship("TechnicalCommitteeReview", back_populates="project")
    generated_rfps = relationship("GeneratedRFP", back_populates="project")
    tender_drafts = relationship("TenderDraft", back_populates="project")
    publish_rfps = relationship("PublishRFP", back_populates="project")
    vendor_bids = relationship("VendorBid", back_populates="project")
    purchase_data = relationship("PurchaseData", back_populates="project")
    agreement_documents = relationship("AgreementDocument", back_populates="project")


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


class TechnicalCommitteeReview(Base):
    __tablename__ = "technical_committee_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    architecture_review = Column(Text, nullable=False)
    security_assessment = Column(Text, nullable=False)
    integration_complexity = Column(Text, nullable=False)
    rbi_compliance_check = Column(Text, nullable=False)
    technical_committee_recommendation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="technical_reviews")


class GeneratedRFP(Base):
    __tablename__ = "generated_rfps"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    rfp_content = Column(Text, nullable=False)
    rfp_filename = Column(String(255), nullable=False)
    rfp_filepath = Column(String(500), nullable=False)
    version = Column(Integer, default=1)
    generated_by = Column(String(100), default="Claude AI")
    file_size_kb = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="generated_rfps")


class TenderDraft(Base):
    __tablename__ = "tender_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    rfp_template = Column(String(255), nullable=False)
    bid_validity_period = Column(Integer, nullable=False)
    submission_deadline = Column(DateTime, nullable=False)
    emd_amount = Column(Float, nullable=False)
    eligibility_criteria = Column(Text, nullable=False)
    authority_decision = Column(Integer, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="tender_drafts")


class PublishRFP(Base):
    __tablename__ = "publish_rfps"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    bank_website = Column(Integer, nullable=False, default=0)
    cppp = Column(Integer, nullable=False, default=0)
    newspaper_publication = Column(Integer, nullable=False, default=0)
    gem_portal = Column(Integer, nullable=False, default=0)
    publication_date = Column(DateTime, nullable=True)
    pre_bid_meeting = Column(DateTime, nullable=True)
    query_last_date = Column(DateTime, nullable=True)
    bid_opening_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="publish_rfps")


class VendorBid(Base):
    __tablename__ = "vendor_bids"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    vendor_name = Column(String(255), nullable=False)
    tech_score = Column(Float, nullable=True)
    comm_score = Column(Float, nullable=True)
    total_score = Column(Float, nullable=True)
    commercial_bid = Column(Float, nullable=False)
    technical_score = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="vendor_bids")


class PurchaseData(Base):
    __tablename__ = "purchase_data"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    purchase_order_number = Column(String(100), nullable=False, unique=True)
    vendor = Column(String(255), nullable=True)
    po_value = Column(Float, nullable=True)
    delivery_period = Column(String(100), nullable=True)
    payment_terms = Column(String(100), nullable=True)
    warranty_period = Column(String(50), nullable=True)
    penalty_clause = Column(String(255), nullable=True)
    po_content = Column(Text, nullable=True)
    po_filename = Column(String(255), nullable=True)
    po_filepath = Column(String(500), nullable=True)
    file_size_kb = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="purchase_data")


class AgreementDocument(Base):
    __tablename__ = "agreement_documents"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, index=True)
    project_id = Column(String(50), nullable=False, index=True)
    purchase_order_number = Column(String(100), nullable=True)

    # Agreement Type: MSA, SLA, NDA, DPA, ANNEXURES
    agreement_type = Column(String(50), nullable=False)

    # Document Content
    content = Column(Text, nullable=True)
    filename = Column(String(255), nullable=True)
    filepath = Column(String(500), nullable=True)
    file_size_kb = Column(Float, nullable=True)

    # Metadata
    vendor_name = Column(String(255), nullable=True)
    po_value = Column(Float, nullable=True)
    generated_by = Column(String(100), default="Claude AI")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="agreement_documents")


def init_db():
    Base.metadata.create_all(bind=engine)
