import logging
from sqlalchemy import (
    create_engine, Column, String, Float, DateTime,
    Integer, Text, ForeignKey, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("DATABASE MODULE INITIALIZATION STARTED")
logger.info("=" * 60)

DB_NAME = "RFP_Creation_Project"
DB_USER = "root"
DB_PASSWORD = "12345"
DB_HOST = "localhost"

logger.info(f"Database Configuration:")
logger.info(f"  - Database Name: {DB_NAME}")
logger.info(f"  - Database Host: {DB_HOST}")
logger.info(f"  - Database User: {DB_USER}")

# Engine WITHOUT database
logger.info("Creating engine without database for initial setup...")
engine_no_db = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}"
)
logger.info("Engine without database created successfully")

# Create DB if not exists
logger.info(f"Checking/Creating database '{DB_NAME}'...")
with engine_no_db.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
logger.info(f"Database '{DB_NAME}' is ready")

# Engine WITH database
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
logger.info("Creating main database engine with database connection...")
engine = create_engine(DATABASE_URL)
logger.info("Main database engine created successfully")

logger.info("Creating SessionLocal factory...")
SessionLocal = sessionmaker(bind=engine)
logger.info("SessionLocal factory created")

logger.info("Creating declarative base...")
Base = declarative_base()
logger.info("Declarative base created")

logger.info("-" * 60)
logger.info("DEFINING DATABASE MODELS")
logger.info("-" * 60)


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


logger.info("Model defined: ProjectCredential (table: project_credentials)")
logger.info("  - Columns: pk_id, id, title, department, category, priority, estimated_amount, business_justification, submitted_by, technical_specification, expected_timeline, email, phone_number, created_at")
logger.info("  - Relationships: files, assessments, technical_reviews, generated_rfps, tender_drafts, publish_rfps, vendor_bids, purchase_data, agreement_documents")


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


logger.info("Model defined: UploadedFile (table: uploaded_files)")
logger.info("  - Columns: id, project_pk_id, project_id, label, original_filename, saved_filename, file_extension, file_size_kb, content_type, faiss_index_id, text_extracted, uploaded_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: FunctionalAssessment (table: functional_assessments)")
logger.info("  - Columns: id, project_pk_id, project_id, functional_fit_assessment, technical_feasibility, risk_assessment, recommendations, status, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: TechnicalCommitteeReview (table: technical_committee_reviews)")
logger.info("  - Columns: id, project_pk_id, project_id, architecture_review, security_assessment, integration_complexity, rbi_compliance_check, technical_committee_recommendation, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: GeneratedRFP (table: generated_rfps)")
logger.info("  - Columns: id, project_pk_id, project_id, rfp_content, rfp_filename, rfp_filepath, version, generated_by, file_size_kb, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: TenderDraft (table: tender_drafts)")
logger.info("  - Columns: id, project_pk_id, project_id, rfp_template, bid_validity_period, submission_deadline, emd_amount, eligibility_criteria, authority_decision, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: PublishRFP (table: publish_rfps)")
logger.info("  - Columns: id, project_pk_id, project_id, bank_website, cppp, newspaper_publication, gem_portal, publication_date, pre_bid_meeting, query_last_date, bid_opening_date, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: VendorBid (table: vendor_bids)")
logger.info("  - Columns: id, project_pk_id, project_id, vendor_name, tech_score, comm_score, total_score, commercial_bid, technical_score, rank, created_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: PurchaseData (table: purchase_data)")
logger.info("  - Columns: id, project_pk_id, project_id, purchase_order_number, vendor, po_value, delivery_period, payment_terms, warranty_period, penalty_clause, po_content, po_filename, po_filepath, file_size_kb, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")


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


logger.info("Model defined: AgreementDocument (table: agreement_documents)")
logger.info("  - Columns: id, project_pk_id, project_id, purchase_order_number, agreement_type, content, filename, filepath, file_size_kb, vendor_name, po_value, generated_by, created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id")
logger.info("  - Agreement Types: MSA, SLA, NDA, DPA, ANNEXURES")

logger.info("-" * 60)
logger.info("ALL DATABASE MODELS DEFINED SUCCESSFULLY")
logger.info("-" * 60)


def init_db():
    """Initialize database tables"""
    logger.info("=" * 60)
    logger.info("INITIALIZING DATABASE TABLES")
    logger.info("=" * 60)
    
    logger.info("Creating all tables from Base metadata...")
    logger.info("Tables to be created:")
    logger.info("  1. project_credentials")
    logger.info("  2. uploaded_files")
    logger.info("  3. functional_assessments")
    logger.info("  4. technical_committee_reviews")
    logger.info("  5. generated_rfps")
    logger.info("  6. tender_drafts")
    logger.info("  7. publish_rfps")
    logger.info("  8. vendor_bids")
    logger.info("  9. purchase_data")
    logger.info("  10. agreement_documents")
    
    Base.metadata.create_all(bind=engine)
    
    logger.info("All database tables created/verified successfully")
    logger.info("=" * 60)
    logger.info("DATABASE INITIALIZATION COMPLETE")
    logger.info("=" * 60)


logger.info("=" * 60)
logger.info("DATABASE MODULE LOADED SUCCESSFULLY")
logger.info("Total Models: 10")
logger.info("=" * 60)
