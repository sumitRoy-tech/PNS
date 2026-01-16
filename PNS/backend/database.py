import logging
from sqlalchemy import (
    create_engine, Column, String, Float, DateTime,
    Integer, Text, ForeignKey, text, Boolean
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
    progress = relationship("TrackProgress", back_populates="project", uselist=False)


logger.info("Model defined: ProjectCredential (table: project_credentials)")
logger.info("  - Columns: pk_id, id, title, department, category, priority, estimated_amount, business_justification, submitted_by, technical_specification, expected_timeline, email, phone_number, created_at")
logger.info("  - Relationships: files, assessments, technical_reviews, generated_rfps, tender_drafts, publish_rfps, vendor_bids, purchase_data, agreement_documents, progress")


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
    version = Column(Integer, nullable=False, default=1)
    rfp_content = Column(Text, nullable=True)
    rfp_filename = Column(String(255), nullable=True)
    rfp_filepath = Column(String(500), nullable=True)
    file_size_kb = Column(Float, nullable=True)
    generated_by = Column(String(100), default="Claude AI")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="generated_rfps")


logger.info("Model defined: GeneratedRFP (table: generated_rfps)")
logger.info("  - Columns: id, project_pk_id, project_id, version, rfp_content, rfp_filename, rfp_filepath, file_size_kb, generated_by, created_at")
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


# ==================== NEW TABLE: TRACK PROGRESS ====================

class TrackProgress(Base):
    """
    Track the progress of each project through the procurement workflow.
    Each project has one progress record tracking completion of all 10 pages/stages.
    """
    __tablename__ = "track_progress"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_pk_id = Column(Integer, ForeignKey("project_credentials.pk_id"), nullable=False, unique=True, index=True)
    project_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # Page completion status (Boolean for each page)
    page_1_requirement = Column(Boolean, default=False)          # Requirement Submission
    page_2_functional = Column(Boolean, default=False)           # Functional Assessment
    page_3_technical = Column(Boolean, default=False)            # Technical Committee Review
    page_4_rfp_generation = Column(Boolean, default=False)       # RFP Generation
    page_5_tender_draft = Column(Boolean, default=False)         # Tender Drafting
    page_6_authority_approval = Column(Boolean, default=False)   # Authority Approval
    page_7_publish_rfp = Column(Boolean, default=False)          # RFP Publishing
    page_8_vendor_bidding = Column(Boolean, default=False)       # Vendor Bidding
    page_9_vendor_evaluation = Column(Boolean, default=False)    # Vendor Evaluation
    page_10_purchase_order = Column(Boolean, default=False)      # Purchase Order
    
    # Completion timestamps for each page
    page_1_completed_at = Column(DateTime, nullable=True)
    page_2_completed_at = Column(DateTime, nullable=True)
    page_3_completed_at = Column(DateTime, nullable=True)
    page_4_completed_at = Column(DateTime, nullable=True)
    page_5_completed_at = Column(DateTime, nullable=True)
    page_6_completed_at = Column(DateTime, nullable=True)
    page_7_completed_at = Column(DateTime, nullable=True)
    page_8_completed_at = Column(DateTime, nullable=True)
    page_9_completed_at = Column(DateTime, nullable=True)
    page_10_completed_at = Column(DateTime, nullable=True)
    
    # Current active page (1-10)
    current_page = Column(Integer, default=1)
    
    # Overall progress percentage (0-100)
    overall_progress = Column(Float, default=0.0)
    
    # Status: 'in_progress', 'completed', 'on_hold', 'rejected'
    status = Column(String(50), default="in_progress")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectCredential", back_populates="progress")


logger.info("Model defined: TrackProgress (table: track_progress)")
logger.info("  - Columns: id, project_pk_id, project_id")
logger.info("  - Page tracking: page_1 through page_10 (Boolean)")
logger.info("  - Completion timestamps: page_1_completed_at through page_10_completed_at")
logger.info("  - Progress tracking: current_page, overall_progress, status")
logger.info("  - Timestamps: created_at, updated_at")
logger.info("  - Foreign Key: project_pk_id -> project_credentials.pk_id (unique)")


# ==================== NEW TABLE: REJECTED PROJECTS ====================

class RejectedProject(Base):
    """
    Track rejected project IDs.
    Simple table to store project_ids that were rejected at ApprovalGate.
    """
    __tablename__ = "rejected_projects"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_id = Column(String(50), nullable=False, unique=True, index=True)
    rejected_at = Column(DateTime, default=datetime.utcnow)


logger.info("Model defined: RejectedProject (table: rejected_projects)")
logger.info("  - Columns: id, project_id, rejected_at")


# ==================== NEW TABLE: PROJECT NAVIGATION ====================

class ProjectNavigation(Base):
    """
    Track the current navigation state for each project.
    Stores the current stage (case number) and component name for easy navigation.
    """
    __tablename__ = "project_navigation"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # Current stage in App.js switch case (0-9)
    current_stage = Column(Integer, default=0)
    
    # Component name (e.g., "RequirementForm", "FunctionalAnalysis", etc.)
    current_page_component = Column(String(100), nullable=False)
    
    # Human-readable page name
    current_page_name = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


logger.info("Model defined: ProjectNavigation (table: project_navigation)")
logger.info("  - Columns: id, project_id, current_stage, current_page_component, current_page_name, created_at, updated_at")


# ==================== STAGE TO COMPONENT MAPPING ====================
# This maps App.js case numbers to component names
STAGE_COMPONENT_MAP = {
    0: {"component": "RequirementForm", "name": "Requirement Submission"},
    1: {"component": "FunctionalAnalysis", "name": "Functional Analysis"},
    2: {"component": "TechnicalReview", "name": "Technical Review"},
    3: {"component": "TenderDrafting", "name": "Tender Drafting"},
    4: {"component": "ApprovalGate", "name": "Authority Approval"},
    5: {"component": "PublishRFP", "name": "Publish RFP"},
    6: {"component": "ReceiveBids", "name": "Receive Bids"},
    7: {"component": "VendorEvaluation", "name": "Vendor Evaluation"},
    8: {"component": "PurchaseOrder", "name": "Purchase Order"},
    9: {"component": "ContractSigning", "name": "Contract Signing"},
}

# Reverse mapping: Component name to stage number
COMPONENT_STAGE_MAP = {v["component"]: k for k, v in STAGE_COMPONENT_MAP.items()}

logger.info("Stage-Component mapping defined:")
for stage, info in STAGE_COMPONENT_MAP.items():
    logger.info(f"  - Case {stage}: {info['component']} ({info['name']})")


# ==================== WORKFLOW PAGE DEFINITIONS ====================
WORKFLOW_PAGES = {
    1: {"name": "requirement", "label": "Requirement Submission", "field": "page_1_requirement"},
    2: {"name": "functional", "label": "Functional Assessment", "field": "page_2_functional"},
    3: {"name": "technical", "label": "Technical Review", "field": "page_3_technical"},
    4: {"name": "rfp_generation", "label": "RFP Generation", "field": "page_4_rfp_generation"},
    5: {"name": "tender_draft", "label": "Tender Drafting", "field": "page_5_tender_draft"},
    6: {"name": "authority_approval", "label": "Authority Approval", "field": "page_6_authority_approval"},
    7: {"name": "publish_rfp", "label": "RFP Publishing", "field": "page_7_publish_rfp"},
    8: {"name": "vendor_bidding", "label": "Vendor Bidding", "field": "page_8_vendor_bidding"},
    9: {"name": "vendor_evaluation", "label": "Vendor Evaluation", "field": "page_9_vendor_evaluation"},
    10: {"name": "purchase_order", "label": "Purchase Order", "field": "page_10_purchase_order"}
}

logger.info("Workflow pages defined:")
for num, info in WORKFLOW_PAGES.items():
    logger.info(f"  - Page {num}: {info['label']} ({info['name']})")


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
    logger.info("  11. track_progress")
    logger.info("  12. rejected_projects")
    logger.info("  13. project_navigation")
    
    Base.metadata.create_all(bind=engine)
    
    logger.info("All database tables created/verified successfully")
    logger.info("=" * 60)
    logger.info("DATABASE INITIALIZATION COMPLETE")
    logger.info("=" * 60)


logger.info("=" * 60)
logger.info("DATABASE MODULE LOADED SUCCESSFULLY")
logger.info("Total Models: 13")
logger.info("=" * 60)
