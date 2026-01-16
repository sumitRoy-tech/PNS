import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database import (
    SessionLocal, ProjectCredential, PurchaseData, GeneratedRFP,
    AgreementDocument, TenderDraft, PublishRFP, VendorBid,
    FunctionalAssessment, TechnicalCommitteeReview
)
from datetime import datetime
import random
import os
import anthropic
import requests
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from fastapi.responses import StreamingResponse

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("PURCHASE MODULE INITIALIZATION STARTED")
logger.info("=" * 60)

# Load environment variables
logger.info("Loading environment variables...")
load_dotenv()
logger.info("Environment variables loaded")

router = APIRouter(prefix="/purchase", tags=["Purchase Order"])
logger.info("Router created with prefix: /purchase")
logger.info("Tags: ['Purchase Order']")

# Directories for storing generated documents
PO_STORAGE_DIR = "generated_purchase_orders"
MSA_STORAGE_DIR = "generated_agreements/master_service_agreement"
SLA_STORAGE_DIR = "generated_agreements/service_level_agreement"
NDA_STORAGE_DIR = "generated_agreements/non_disclosure_agreement"
DPA_STORAGE_DIR = "generated_agreements/data_processing_agreement"
ANNEXURES_STORAGE_DIR = "generated_agreements/annexures_schedules"

logger.info("Storage directories configured:")
logger.info(f"  - PO_STORAGE_DIR: {PO_STORAGE_DIR}")
logger.info(f"  - MSA_STORAGE_DIR: {MSA_STORAGE_DIR}")
logger.info(f"  - SLA_STORAGE_DIR: {SLA_STORAGE_DIR}")
logger.info(f"  - NDA_STORAGE_DIR: {NDA_STORAGE_DIR}")
logger.info(f"  - DPA_STORAGE_DIR: {DPA_STORAGE_DIR}")
logger.info(f"  - ANNEXURES_STORAGE_DIR: {ANNEXURES_STORAGE_DIR}")

# Create directories
logger.info("Creating storage directories...")
for directory in [PO_STORAGE_DIR, MSA_STORAGE_DIR, SLA_STORAGE_DIR, NDA_STORAGE_DIR, DPA_STORAGE_DIR, ANNEXURES_STORAGE_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"  Directory ensured: {directory}")
logger.info("All storage directories created/verified")

# Agreement types
AGREEMENT_TYPES = {
    "MSA": {"name": "Master Service Agreement", "dir": MSA_STORAGE_DIR},
    "SLA": {"name": "Service Level Agreement", "dir": SLA_STORAGE_DIR},
    "NDA": {"name": "Non Disclosure Agreement", "dir": NDA_STORAGE_DIR},
    "DPA": {"name": "Data Processing Agreement", "dir": DPA_STORAGE_DIR},
    "ANNEXURES": {"name": "Annexures & Schedules", "dir": ANNEXURES_STORAGE_DIR}
}
logger.info(f"Agreement types configured: {list(AGREEMENT_TYPES.keys())}")

logger.info("=" * 60)
logger.info("PURCHASE MODULE INITIALIZED SUCCESSFULLY")
logger.info("=" * 60)


# ==================== PYDANTIC MODELS ====================

class PurchaseDataRequest(BaseModel):
    project_id: str
    purchase_order_number: str
    vendor: str
    po_value: float
    delivery_period: str
    payment_terms: str
    warranty_period: str
    penalty_clause: str


class WinnerInfo(BaseModel):
    vendor_name: str
    commercial_bid: float
    publication_date: Optional[str] = None


class VendorBidInfo(BaseModel):
    vendor_name: str
    tech_score: Optional[float] = None
    comm_score: Optional[float] = None
    total_score: Optional[float] = None
    commercial_bid: float
    technical_score: int
    rank: int


class VendorEvaluationRequest(BaseModel):
    message: Optional[str] = None
    project_id: str
    project_title: Optional[str] = None
    total_vendors_received: Optional[int] = None
    total_qualified_vendors: Optional[int] = None
    winner: WinnerInfo
    vendor_bids: Optional[List[VendorBidInfo]] = None


class PurchaseDataInfo(BaseModel):
    purchase_order_number: str
    vendor: str
    po_value: float
    delivery_period: str
    payment_terms: str
    warranty_period: str
    penalty_clause: str


class GenerateAgreementsRequest(BaseModel):
    message: Optional[str] = None
    purchase_id: Optional[int] = None
    project_id: str
    project_title: Optional[str] = None
    data: PurchaseDataInfo
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ==================== VALIDATION HELPERS ====================

VALID_PAYMENT_TERMS = [
    "100% Advance",
    "50% Advance, 50% on Delivery",
    "30 Days from Delivery",
    "60 Days from Delivery",
    "Milestone Based"
]

VALID_WARRANTY_PERIODS = ["1 year", "2 year", "3 year", "5 year"]

logger.info(f"Valid payment terms: {VALID_PAYMENT_TERMS}")
logger.info(f"Valid warranty periods: {VALID_WARRANTY_PERIODS}")


def validate_payment_terms(value: str) -> str:
    logger.debug(f"Validating payment terms: {value}")
    if value not in VALID_PAYMENT_TERMS:
        logger.error(f"Invalid payment terms: {value}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment terms: {value}. Valid options: {', '.join(VALID_PAYMENT_TERMS)}"
        )
    logger.debug(f"Payment terms validated: {value}")
    return value


def validate_warranty_period(value: str) -> str:
    logger.debug(f"Validating warranty period: {value}")
    if value not in VALID_WARRANTY_PERIODS:
        logger.error(f"Invalid warranty period: {value}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid warranty period: {value}. Valid options: {', '.join(VALID_WARRANTY_PERIODS)}"
        )
    logger.debug(f"Warranty period validated: {value}")
    return value


def generate_purchase_order_number(project_id: str) -> str:
    logger.info(f"Generating purchase order number for project: {project_id}")
    random_suffix = random.randint(1000, 9999)
    po_number = f"PO-{project_id}-{random_suffix}"
    logger.info(f"Generated purchase order number: {po_number}")
    return po_number


# ==================== GET RFP ID API ====================

@router.get("/rfp/{project_id}")
def get_rfp_by_project_id(project_id: str):
    """Get RFP ID from generated_rfps table using project_id"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /purchase/rfp/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        # Get the latest RFP for the project
        logger.info(f"Querying latest RFP for project pk_id: {project.pk_id}")
        rfp = db.query(GeneratedRFP).filter(
            GeneratedRFP.project_pk_id == project.pk_id
        ).order_by(GeneratedRFP.version.desc()).first()
        
        if not rfp:
            logger.warning(f"No RFP found for project: {project_id}")
            logger.error("Raising HTTPException 404: No RFP found for this project")
            raise HTTPException(status_code=404, detail="No RFP found for this project")
        
        logger.info(f"RFP found: id={rfp.id}, version={rfp.version}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /purchase/rfp/{project_id} - SUCCESS")
        logger.info(f"Returning RFP id: {rfp.id}")
        logger.info("=" * 60)
        
        return {
            "rfp_id": rfp.id,
            "project_id": project.id,
            "project_title": project.title,
            "version": rfp.version,
            "filename": rfp.rfp_filename,
            "filepath": rfp.rfp_filepath,
            "created_at": rfp.created_at.isoformat() if rfp.created_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_rfp_by_project_id: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


# ==================== HELPER FUNCTIONS ====================

def get_all_project_data(db, project_id: str) -> Dict[str, Any]:
    """Gather all project data from all tables"""
    logger.info("-" * 40)
    logger.info(f"HELPER: get_all_project_data called for project_id: {project_id}")
    logger.info("-" * 40)
    
    logger.info("Querying ProjectCredential...")
    project = db.query(ProjectCredential).filter(
        ProjectCredential.id == project_id
    ).first()
    
    if not project:
        logger.error(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    
    logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
    
    # Get all related data from all tables
    logger.info("Querying FunctionalAssessment...")
    functional_assessment = db.query(FunctionalAssessment).filter(
        FunctionalAssessment.project_pk_id == project.pk_id
    ).first()
    logger.info(f"  FunctionalAssessment: {'Found' if functional_assessment else 'Not found'}")
    
    logger.info("Querying TechnicalCommitteeReview...")
    technical_review = db.query(TechnicalCommitteeReview).filter(
        TechnicalCommitteeReview.project_pk_id == project.pk_id
    ).first()
    logger.info(f"  TechnicalCommitteeReview: {'Found' if technical_review else 'Not found'}")
    
    logger.info("Querying TenderDraft...")
    tender_draft = db.query(TenderDraft).filter(
        TenderDraft.project_pk_id == project.pk_id
    ).first()
    logger.info(f"  TenderDraft: {'Found' if tender_draft else 'Not found'}")
    
    logger.info("Querying PublishRFP...")
    publish_rfp = db.query(PublishRFP).filter(
        PublishRFP.project_pk_id == project.pk_id
    ).first()
    logger.info(f"  PublishRFP: {'Found' if publish_rfp else 'Not found'}")
    
    logger.info("Querying VendorBid (rank=1 winner)...")
    vendor_bid = db.query(VendorBid).filter(
        VendorBid.project_pk_id == project.pk_id,
        VendorBid.rank == 1
    ).first()
    logger.info(f"  VendorBid (winner): {'Found - ' + vendor_bid.vendor_name if vendor_bid else 'Not found'}")
    
    # Get all vendor bids
    logger.info("Querying all VendorBids...")
    all_vendor_bids = db.query(VendorBid).filter(
        VendorBid.project_pk_id == project.pk_id
    ).order_by(VendorBid.rank).all()
    logger.info(f"  All VendorBids count: {len(all_vendor_bids)}")
    
    logger.info("Querying GeneratedRFP (latest version)...")
    generated_rfp = db.query(GeneratedRFP).filter(
        GeneratedRFP.project_pk_id == project.pk_id
    ).order_by(GeneratedRFP.version.desc()).first()
    logger.info(f"  GeneratedRFP: {'Found - v' + str(generated_rfp.version) if generated_rfp else 'Not found'}")
    
    logger.info("Querying PurchaseData...")
    purchase_data = db.query(PurchaseData).filter(
        PurchaseData.project_pk_id == project.pk_id
    ).first()
    logger.info(f"  PurchaseData: {'Found - ' + purchase_data.purchase_order_number if purchase_data else 'Not found'}")
    
    # Get existing agreement documents
    logger.info("Querying AgreementDocuments...")
    agreement_documents = db.query(AgreementDocument).filter(
        AgreementDocument.project_pk_id == project.pk_id
    ).all()
    logger.info(f"  AgreementDocuments count: {len(agreement_documents)}")
    
    logger.info("-" * 40)
    logger.info("HELPER: get_all_project_data completed")
    logger.info("-" * 40)
    
    return {
        "project": project,
        "functional_assessment": functional_assessment,
        "technical_review": technical_review,
        "tender_draft": tender_draft,
        "publish_rfp": publish_rfp,
        "vendor_bid": vendor_bid,
        "all_vendor_bids": all_vendor_bids,
        "generated_rfp": generated_rfp,
        "purchase_data": purchase_data,
        "agreement_documents": agreement_documents
    }


def fetch_rfp_content(rfp_id: int) -> Optional[str]:
    """Fetch RFP content from the technical-review API"""
    logger.info(f"HELPER: fetch_rfp_content called for rfp_id: {rfp_id}")
    try:
        url = f"http://localhost:8003/technical-review/rfp/content/{rfp_id}"
        logger.info(f"Fetching RFP content from: {url}")
        response = requests.get(url, timeout=30)
        logger.info(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            logger.info(f"RFP content fetched successfully, length: {len(content)} chars")
            return content
        else:
            logger.warning(f"Failed to fetch RFP content, status: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching RFP content: {str(e)}")
    return None


def build_comprehensive_context(project_data: Dict[str, Any], rfp_content: Optional[str] = None) -> str:
    """Build comprehensive context from ALL project data for AI generation"""
    logger.info("-" * 40)
    logger.info("HELPER: build_comprehensive_context called")
    logger.info("-" * 40)
    
    project = project_data["project"]
    functional_assessment = project_data.get("functional_assessment")
    technical_review = project_data.get("technical_review")
    tender_draft = project_data.get("tender_draft")
    publish_rfp = project_data.get("publish_rfp")
    vendor_bid = project_data.get("vendor_bid")
    all_vendor_bids = project_data.get("all_vendor_bids", [])
    generated_rfp = project_data.get("generated_rfp")
    purchase_data = project_data.get("purchase_data")
    agreement_documents = project_data.get("agreement_documents", [])
    
    logger.info("Building context sections:")
    logger.info("  Section 1: Project Credentials")
    
    context = f"""
================================================================================
                    COMPREHENSIVE PROJECT DATA FOR AGREEMENT GENERATION
================================================================================

SECTION 1: PROJECT CREDENTIALS (from project_credentials table)
--------------------------------------------------------------------------------
- Project ID: {project.id}
- Project PK ID: {project.pk_id}
- Project Title: {project.title}
- Department: {project.department}
- Category: {project.category}
- Priority: {project.priority}
- Estimated Amount: ₹{project.estimated_amount:,.2f}
- Business Justification: {project.business_justification}
- Submitted By: {project.submitted_by}
- Technical Specification: {project.technical_specification or 'N/A'}
- Expected Timeline: {project.expected_timeline or 'N/A'}
- Contact Email: {project.email or 'N/A'}
- Phone Number: {project.phone_number or 'N/A'}
- Created At: {project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else 'N/A'}

BANK DETAILS:
- Bank Name: Punjab & Sind Bank
- Head Office: 21, Rajendra Place, New Delhi - 110008
- CIN: L65110PB1908GOI002217
- Regulated By: Reserve Bank of India (RBI)
"""

    # Functional Assessment Section
    logger.info("  Section 2: Functional Assessment")
    if functional_assessment:
        context += f"""
SECTION 2: FUNCTIONAL ASSESSMENT (from functional_assessments table)
--------------------------------------------------------------------------------
- Assessment ID: {functional_assessment.id}
- Status: {functional_assessment.status}
- Created At: {functional_assessment.created_at.strftime('%Y-%m-%d %H:%M:%S') if functional_assessment.created_at else 'N/A'}
- Updated At: {functional_assessment.updated_at.strftime('%Y-%m-%d %H:%M:%S') if functional_assessment.updated_at else 'N/A'}

FUNCTIONAL FIT ASSESSMENT:
{functional_assessment.functional_fit_assessment or 'N/A'}

TECHNICAL FEASIBILITY:
{functional_assessment.technical_feasibility or 'N/A'}

RISK ASSESSMENT:
{functional_assessment.risk_assessment or 'N/A'}

RECOMMENDATIONS:
{functional_assessment.recommendations or 'N/A'}
"""
    else:
        context += """
SECTION 2: FUNCTIONAL ASSESSMENT
--------------------------------------------------------------------------------
No functional assessment data available for this project.
"""

    # Technical Committee Review Section
    logger.info("  Section 3: Technical Committee Review")
    if technical_review:
        context += f"""
SECTION 3: TECHNICAL COMMITTEE REVIEW (from technical_committee_reviews table)
--------------------------------------------------------------------------------
- Review ID: {technical_review.id}
- Created At: {technical_review.created_at.strftime('%Y-%m-%d %H:%M:%S') if technical_review.created_at else 'N/A'}
- Updated At: {technical_review.updated_at.strftime('%Y-%m-%d %H:%M:%S') if technical_review.updated_at else 'N/A'}

ARCHITECTURE REVIEW:
{technical_review.architecture_review or 'N/A'}

SECURITY ASSESSMENT:
{technical_review.security_assessment or 'N/A'}

INTEGRATION COMPLEXITY:
{technical_review.integration_complexity or 'N/A'}

RBI COMPLIANCE CHECK:
{technical_review.rbi_compliance_check or 'N/A'}

TECHNICAL COMMITTEE RECOMMENDATION:
{technical_review.technical_committee_recommendation or 'N/A'}
"""
    else:
        context += """
SECTION 3: TECHNICAL COMMITTEE REVIEW
--------------------------------------------------------------------------------
No technical committee review data available for this project.
"""

    # Tender Draft Section
    logger.info("  Section 4: Tender Draft")
    if tender_draft:
        context += f"""
SECTION 4: TENDER DRAFT (from tender_drafts table)
--------------------------------------------------------------------------------
- Tender ID: {tender_draft.id}
- RFP Template: {tender_draft.rfp_template}
- Bid Validity Period: {tender_draft.bid_validity_period} days
- Submission Deadline: {tender_draft.submission_deadline.strftime('%Y-%m-%d %H:%M:%S') if tender_draft.submission_deadline else 'N/A'}
- EMD Amount: ₹{tender_draft.emd_amount:,.2f}
- Authority Decision: {'Approved' if tender_draft.authority_decision == 1 else 'Rejected' if tender_draft.authority_decision == 0 else 'Pending'}
- Created At: {tender_draft.created_at.strftime('%Y-%m-%d %H:%M:%S') if tender_draft.created_at else 'N/A'}
- Updated At: {tender_draft.updated_at.strftime('%Y-%m-%d %H:%M:%S') if tender_draft.updated_at else 'N/A'}

ELIGIBILITY CRITERIA:
{tender_draft.eligibility_criteria or 'N/A'}
"""
    else:
        context += """
SECTION 4: TENDER DRAFT
--------------------------------------------------------------------------------
No tender draft data available for this project.
"""

    # Publish RFP Section
    logger.info("  Section 5: Publish RFP")
    if publish_rfp:
        context += f"""
SECTION 5: PUBLISH RFP (from publish_rfps table)
--------------------------------------------------------------------------------
- Publication ID: {publish_rfp.id}
- Bank Website Published: {'Yes' if publish_rfp.bank_website == 1 else 'No'}
- CPPP Portal Published: {'Yes' if publish_rfp.cppp == 1 else 'No'}
- Newspaper Publication: {'Yes' if publish_rfp.newspaper_publication == 1 else 'No'}
- GeM Portal Published: {'Yes' if publish_rfp.gem_portal == 1 else 'No'}
- Publication Date: {publish_rfp.publication_date.strftime('%Y-%m-%d') if publish_rfp.publication_date else 'N/A'}
- Pre-Bid Meeting Date: {publish_rfp.pre_bid_meeting.strftime('%Y-%m-%d') if publish_rfp.pre_bid_meeting else 'N/A'}
- Query Last Date: {publish_rfp.query_last_date.strftime('%Y-%m-%d') if publish_rfp.query_last_date else 'N/A'}
- Bid Opening Date: {publish_rfp.bid_opening_date.strftime('%Y-%m-%d') if publish_rfp.bid_opening_date else 'N/A'}
- Created At: {publish_rfp.created_at.strftime('%Y-%m-%d %H:%M:%S') if publish_rfp.created_at else 'N/A'}
"""
    else:
        context += """
SECTION 5: PUBLISH RFP
--------------------------------------------------------------------------------
No publish RFP data available for this project.
"""

    # Vendor Bids Section
    logger.info("  Section 6: Vendor Bids")
    if all_vendor_bids:
        context += f"""
SECTION 6: VENDOR BIDS (from vendor_bids table)
--------------------------------------------------------------------------------
Total Vendors: {len(all_vendor_bids)}

"""
        for i, bid in enumerate(all_vendor_bids, 1):
            context += f"""Vendor {i} {'(WINNER)' if bid.rank == 1 else ''}:
- Vendor Name: {bid.vendor_name}
- Technical Score: {bid.tech_score or 'N/A'}
- Commercial Score: {bid.comm_score or 'N/A'}
- Total Score: {bid.total_score or 'N/A'}
- Commercial Bid: ₹{bid.commercial_bid:,.2f}
- Technical Score (Percentage): {bid.technical_score}%
- Rank: {bid.rank}
- Created At: {bid.created_at.strftime('%Y-%m-%d %H:%M:%S') if bid.created_at else 'N/A'}

"""
    else:
        context += """
SECTION 6: VENDOR BIDS
--------------------------------------------------------------------------------
No vendor bid data available for this project.
"""

    # Purchase Data Section
    logger.info("  Section 7: Purchase Data")
    if purchase_data:
        context += f"""
SECTION 7: PURCHASE DATA (from purchase_data table)
--------------------------------------------------------------------------------
- Purchase ID: {purchase_data.id}
- Purchase Order Number: {purchase_data.purchase_order_number}
- Vendor: {purchase_data.vendor or 'N/A'}
- PO Value: ₹{(purchase_data.po_value or 0):,.2f}
- Delivery Period: {purchase_data.delivery_period or 'N/A'}
- Payment Terms: {purchase_data.payment_terms or 'N/A'}
- Warranty Period: {purchase_data.warranty_period or 'N/A'}
- Penalty Clause: {purchase_data.penalty_clause or 'N/A'}
- PO Filename: {purchase_data.po_filename or 'N/A'}
- File Size (KB): {round(purchase_data.file_size_kb, 2) if purchase_data.file_size_kb else 'N/A'}
- Created At: {purchase_data.created_at.strftime('%Y-%m-%d %H:%M:%S') if purchase_data.created_at else 'N/A'}
- Updated At: {purchase_data.updated_at.strftime('%Y-%m-%d %H:%M:%S') if purchase_data.updated_at else 'N/A'}
"""
    else:
        context += """
SECTION 7: PURCHASE DATA
--------------------------------------------------------------------------------
No purchase data available for this project.
"""

    # Generated RFP Section
    logger.info("  Section 8: Generated RFP")
    if generated_rfp:
        context += f"""
SECTION 8: GENERATED RFP (from generated_rfps table)
--------------------------------------------------------------------------------
- RFP ID: {generated_rfp.id}
- Version: {generated_rfp.version}
- RFP Filename: {generated_rfp.rfp_filename}
- Generated By: {generated_rfp.generated_by or 'N/A'}
- File Size (KB): {round(generated_rfp.file_size_kb, 2) if generated_rfp.file_size_kb else 'N/A'}
- Created At: {generated_rfp.created_at.strftime('%Y-%m-%d %H:%M:%S') if generated_rfp.created_at else 'N/A'}
"""
    else:
        context += """
SECTION 8: GENERATED RFP
--------------------------------------------------------------------------------
No generated RFP data available for this project.
"""

    # RFP Content Section
    logger.info("  Section 9: RFP Document Content")
    if rfp_content:
        context += f"""
SECTION 9: RFP DOCUMENT CONTENT
--------------------------------------------------------------------------------
{rfp_content}
"""
    elif generated_rfp and generated_rfp.rfp_content:
        context += f"""
SECTION 9: RFP DOCUMENT CONTENT
--------------------------------------------------------------------------------
{generated_rfp.rfp_content}
"""
    else:
        context += """
SECTION 9: RFP DOCUMENT CONTENT
--------------------------------------------------------------------------------
No RFP content available for this project.
"""

    # Existing Agreement Documents Section
    logger.info("  Section 10: Existing Agreement Documents")
    if agreement_documents:
        context += f"""
SECTION 10: EXISTING AGREEMENT DOCUMENTS (from agreement_documents table)
--------------------------------------------------------------------------------
Total Existing Agreements: {len(agreement_documents)}

"""
        for doc in agreement_documents:
            context += f"""- {doc.agreement_type}: {doc.filename}
  Vendor: {doc.vendor_name or 'N/A'}
  PO Value: ₹{(doc.po_value or 0):,.2f}
  Created At: {doc.created_at.strftime('%Y-%m-%d %H:%M:%S') if doc.created_at else 'N/A'}

"""
    else:
        context += """
SECTION 10: EXISTING AGREEMENT DOCUMENTS
--------------------------------------------------------------------------------
No existing agreement documents for this project.
"""

    context += """
================================================================================
                            END OF PROJECT DATA
================================================================================
"""
    
    logger.info(f"Context built successfully, total length: {len(context)} chars")
    logger.info("-" * 40)
    logger.info("HELPER: build_comprehensive_context completed")
    logger.info("-" * 40)
    
    return context


def generate_agreement_content_from_project_data(
    agreement_type: str,
    comprehensive_context: str,
    project_data: Dict[str, Any]
) -> str:
    """Generate agreement content using Anthropic API with comprehensive project data"""
    logger.info("-" * 40)
    logger.info(f"HELPER: generate_agreement_content_from_project_data called")
    logger.info(f"Agreement type: {agreement_type}")
    logger.info("-" * 40)
    
    logger.info("Checking for ANTHROPIC_API_KEY...")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not found in environment variables"
        )
    logger.info("ANTHROPIC_API_KEY found")
    
    logger.info("Creating Anthropic client...")
    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Anthropic client created")
    
    project = project_data["project"]
    purchase_data = project_data.get("purchase_data")
    vendor_bid = project_data.get("vendor_bid")
    
    # Get vendor name and PO details
    vendor_name = "Vendor"
    po_value = 0
    po_number = "N/A"
    delivery_period = "As per contract"
    payment_terms = "As per contract"
    warranty_period = "As per contract"
    penalty_clause = "As per contract"
    
    if purchase_data:
        vendor_name = purchase_data.vendor or vendor_name
        po_value = purchase_data.po_value or po_value
        po_number = purchase_data.purchase_order_number or po_number
        delivery_period = purchase_data.delivery_period or delivery_period
        payment_terms = purchase_data.payment_terms or payment_terms
        warranty_period = purchase_data.warranty_period or warranty_period
        penalty_clause = purchase_data.penalty_clause or penalty_clause
        logger.info(f"Using purchase_data: vendor={vendor_name}, po_value={po_value}")
    elif vendor_bid:
        vendor_name = vendor_bid.vendor_name
        po_value = vendor_bid.commercial_bid
        logger.info(f"Using vendor_bid: vendor={vendor_name}, po_value={po_value}")
    
    # Agreement-specific prompts with comprehensive context
    logger.info(f"Building prompt for {agreement_type}...")
    
    prompts = {
 
        "MSA": f"""You are a legal document expert for Punjab & Sind Bank. 
        CRITICAL LENGTH CONSTRAINT (MANDATORY):
            - The final document MUST NOT exceed 3 A4 pages when rendered as a professional PDF.
            - Target length: 1,200–1,400 words TOTAL.
            - Be concise. Summarize clauses. Avoid repetition.
            - Use short paragraphs and bullet-like sentence structure.
            - If content exceeds the limit, PRIORITIZE legally essential clauses and OMIT minor details.
        
        Generate a concise but legally complete MASTER SERVICE AGREEMENT (MSA) using ALL the project data provided below.

{comprehensive_context}

Using ALL the above data from all tables, create a formal and legally binding MSA document that includes:

1. PREAMBLE
   - Parties: Punjab & Sind Bank (the "Bank") and {vendor_name} (the "Service Provider")
   - Effective Date: {datetime.now().strftime('%d-%m-%Y')}
   - Contract Value: ₹{po_value:,.2f}

2. DEFINITIONS AND INTERPRETATION
   - Define all key terms based on the project scope and technical specifications
   - Include banking-specific terminology

3. SCOPE OF SERVICES
   - Based on project title: {project.title}
   - Department: {project.department}
   - Category: {project.category}
   - Include all technical specifications from the RFP
   - Reference the functional assessment requirements

4. TERM AND TERMINATION
   - Delivery Period: {delivery_period}
   - Contract renewal terms
   - Termination conditions based on tender draft
   - Exit management provisions

5. SERVICE FEES AND PAYMENT
   - Total Contract Value: ₹{po_value:,.2f}
   - Payment Terms: {payment_terms}
   - Invoice procedures
   - EMD details from tender draft

6. INTELLECTUAL PROPERTY RIGHTS
   - Ownership of deliverables
   - License grants
   - Third-party IP considerations

7. CONFIDENTIALITY
   - Banking data protection requirements
   - Customer information security
   - RBI compliance from technical review

8. DATA PROTECTION AND SECURITY
   - Security measures from technical review
   - Data handling procedures
   - RBI data localization compliance

9. WARRANTIES AND REPRESENTATIONS
   - Based on eligibility criteria from tender draft
   - Technical warranties from RFP requirements
   - Performance guarantees

10. LIMITATION OF LIABILITY
    - Caps on liability
    - Exclusions
    - Insurance requirements

11. INDEMNIFICATION
    - Mutual indemnification clauses
    - IP indemnification

12. FORCE MAJEURE
    - Definition and procedures
    - Notification requirements

13. DISPUTE RESOLUTION
    - Escalation matrix
    - Arbitration in New Delhi
    - Governing jurisdiction

14. GOVERNING LAW
    - Indian law
    - RBI regulations compliance

15. GENERAL PROVISIONS
    - Notices
    - Amendment procedures
    - Entire agreement clause
    - Severability

16. SIGNATURES
    - For Punjab & Sind Bank
    - For {vendor_name}

Format professionally with numbered clauses and sub-clauses. Reference specific data from all tables wherever applicable. Use plain text without markdown formatting.""",

        "SLA": f"""You are a service level management expert for Punjab & Sind Bank.
        CRITICAL LENGTH CONSTRAINT (MANDATORY):
            - The final document MUST NOT exceed 3 A4 pages when rendered as a professional PDF.
            - Target length: 1,200–1,400 words TOTAL.
            - Be concise. Summarize clauses. Avoid repetition.
            - Use short paragraphs and bullet-like sentence structure.
            - If content exceeds the limit, PRIORITIZE legally essential clauses and OMIT minor details.
        
        Generate a concise but legally complete SERVICE LEVEL AGREEMENT (SLA) using ALL the project data provided below.

{comprehensive_context}

Using ALL the above data from all tables, create a formal SLA document that includes:

1. SERVICE DESCRIPTION
   - Project: {project.title}
   - Department: {project.department}
   - Scope based on RFP content and functional assessment

2. SERVICE AVAILABILITY
   - 99.9% uptime guarantee
   - Planned maintenance windows
   - Availability calculation method

3. PERFORMANCE METRICS
   - Response time KPIs based on technical specifications
   - Transaction processing times
   - System performance benchmarks from technical review

4. RESPONSE TIME REQUIREMENTS
   - Priority 1 (Critical): Response within 15 minutes, Resolution within 4 hours
   - Priority 2 (High): Response within 30 minutes, Resolution within 8 hours
   - Priority 3 (Medium): Response within 2 hours, Resolution within 24 hours
   - Priority 4 (Low): Response within 4 hours, Resolution within 48 hours

5. INCIDENT MANAGEMENT
   - Incident classification based on technical review
   - Reporting procedures
   - Root cause analysis requirements

6. ESCALATION PROCEDURES
   - Escalation matrix with timelines
   - Contact points
   - Management escalation

7. MAINTENANCE WINDOWS
   - Scheduled maintenance timing
   - Emergency maintenance procedures
   - Notification requirements (minimum 72 hours advance notice)

8. SERVICE CREDITS
   - Credit calculation formula
   - Based on penalty clause: {penalty_clause}
   - Maximum credits per month

9. REPORTING REQUIREMENTS
   - Daily, weekly, monthly reports
   - Dashboard requirements
   - Performance review meetings

10. REVIEW AND MONITORING
    - Quarterly SLA reviews
    - Performance assessment criteria
    - Continuous improvement process

11. PENALTY CALCULATIONS
    - Specific penalties: {penalty_clause}
    - Calculation examples
    - Payment/credit process

12. EXCLUSIONS
    - Force majeure
    - Planned maintenance
    - Bank-caused issues
    - Third-party dependencies

13. SERVICE HOURS
    - 24x7 for critical systems
    - Business hours definition
    - Holiday support

14. SIGNATURES
    - For Punjab & Sind Bank
    - For {vendor_name}

Include specific metrics, timelines, and penalty calculations. Use plain text without markdown formatting.""",

        "NDA": f"""You are a legal expert specializing in confidentiality agreements for banking sector.
        CRITICAL LENGTH CONSTRAINT (MANDATORY):
            - The final document MUST NOT exceed 3 A4 pages when rendered as a professional PDF.
            - Target length: 1,200–1,400 words TOTAL.
            - Be concise. Summarize clauses. Avoid repetition.
            - Use short paragraphs and bullet-like sentence structure.
            - If content exceeds the limit, PRIORITIZE legally essential clauses and OMIT minor details.
        
        Generate a concise but legally complete NON-DISCLOSURE AGREEMENT (NDA) for Punjab & Sind Bank using ALL the project data provided below.

{comprehensive_context}

Using ALL the above data from all tables, create a formal NDA document that includes:

1. PREAMBLE
   - Parties: Punjab & Sind Bank (Disclosing Party) and {vendor_name} (Receiving Party)
   - Purpose: {project.title}
   - Effective Date: {datetime.now().strftime('%d-%m-%Y')}

2. DEFINITIONS
   - Confidential Information
   - Banking Data
   - Customer Information
   - RBI Regulated Information
   - Technical Information (based on technical review)
   - Business Information

3. CONFIDENTIAL INFORMATION SCOPE
   - Project-specific information: {project.title}
   - Technical specifications from RFP
   - Customer data and banking records
   - Security architecture from technical review
   - Financial information
   - Business processes

4. OBLIGATIONS OF RECEIVING PARTY
   - Non-disclosure obligations
   - Use restrictions (only for project: {project.title})
   - Protection standards (encryption, access control)
   - Employee confidentiality binding
   - Subcontractor restrictions

5. EXCLUSIONS FROM CONFIDENTIALITY
   - Publicly available information
   - Prior knowledge
   - Independent development
   - Required disclosures (RBI, regulatory, legal)

6. TERM OF CONFIDENTIALITY
   - General information: 5 years post-termination
   - Customer data: Perpetual
   - RBI regulated information: Perpetual
   - Security information: Perpetual

7. RETURN OF CONFIDENTIAL INFORMATION
   - Return procedures upon project completion
   - Destruction certification requirements
   - Retention for legal/regulatory requirements

8. NO LICENSE GRANTED
   - No IP rights transfer
   - No implied licenses
   - Bank's ownership of all data

9. NO WARRANTY
   - Disclaimer of warranties
   - Accuracy disclaimer
   - No guarantee of business relationship

10. REMEDIES
    - Injunctive relief
    - Monetary damages
    - Specific performance
    - Legal costs recovery

11. RBI COMPLIANCE
    - Data localization requirements
    - Regulatory reporting obligations
    - Audit requirements from technical review

12. GOVERNING LAW
    - Indian law
    - Jurisdiction: Courts of New Delhi
    - RBI regulations

13. ENTIRE AGREEMENT
    - Integration clause
    - Amendment requirements (written only)
    - No oral modifications

14. SIGNATURES
    - For Punjab & Sind Bank
    - For {vendor_name}
    - Witness signatures

Emphasize banking data protection and RBI compliance. Use plain text without markdown formatting.""",

        "DPA": f"""You are a data protection expert for banking sector.
        CRITICAL LENGTH CONSTRAINT (MANDATORY):
            - The final document MUST NOT exceed 3 A4 pages when rendered as a professional PDF.
            - Target length: 1,200–1,400 words TOTAL.
            - Be concise. Summarize clauses. Avoid repetition.
            - Use short paragraphs and bullet-like sentence structure.
            - If content exceeds the limit, PRIORITIZE legally essential clauses and OMIT minor details.
        
        Generate a concise but legally complete DATA PROCESSING AGREEMENT (DPA) for Punjab & Sind Bank using ALL the project data provided below.

{comprehensive_context}

Using ALL the above data from all tables, create a formal DPA document compliant with Indian data protection laws and RBI guidelines:

1. PREAMBLE
   - Data Controller: Punjab & Sind Bank
   - Data Processor: {vendor_name}
   - Purpose: {project.title}
   - Contract Reference: {po_number}
   - Effective Date: {datetime.now().strftime('%d-%m-%Y')}

2. DEFINITIONS
   - Personal Data
   - Sensitive Personal Data (banking, financial)
   - Data Processing
   - Data Controller (Punjab & Sind Bank)
   - Data Processor ({vendor_name})
   - Sub-processor
   - Data Subject (bank customers)
   - Data Breach
   - RBI Regulated Data

3. SCOPE AND PURPOSE OF PROCESSING
   - Project scope: {project.title}
   - Department: {project.department}
   - Processing activities based on RFP
   - Lawful basis for processing

4. DATA CONTROLLER AND PROCESSOR ROLES
   - Bank as Data Controller responsibilities
   - {vendor_name} as Data Processor obligations
   - Clear demarcation of duties

5. TYPES OF PERSONAL DATA
   - Customer information
   - Transaction data
   - Account details
   - KYC information
   - Financial records
   - Categories based on project: {project.category}

6. PROCESSING INSTRUCTIONS
   - Written instructions requirement
   - Scope limitations based on contract
   - Purpose limitations
   - No processing beyond instructions

7. SECURITY MEASURES
   - Technical measures from technical review
   - Encryption standards
   - Access controls
   - Network security
   - Physical security
   - ISO 27001 compliance requirement

8. SUB-PROCESSORS
   - Prior written consent requirement
   - List of approved sub-processors
   - Sub-processor agreement requirements
   - Flow-down of obligations
   - Bank's right to object

9. DATA SUBJECT RIGHTS
   - Access requests handling
   - Rectification requests
   - Deletion/erasure requests
   - Portability requests
   - Objection handling
   - Response timelines

10. DATA BREACH NOTIFICATION
    - 72-hour notification to Bank
    - Notification contents required
    - RBI notification (6 hours for critical)
    - Remediation procedures
    - Post-incident review

11. DATA TRANSFER
    - Data localization (all data in India) - RBI mandate
    - Cross-border transfer prohibition
    - Exception handling
    - Transfer impact assessment

12. AUDIT RIGHTS
    - Bank's audit rights (annual minimum)
    - RBI audit compliance
    - Third-party audit reports (SOC 2)
    - On-site inspection rights
    - 30-day notice for audits

13. DELETION AND RETURN OF DATA
    - Procedures upon termination
    - Retention periods as per RBI
    - Secure destruction methods
    - Destruction certification
    - Archive requirements

14. RBI COMPLIANCE REQUIREMENTS
    - Data localization (all data stored in India)
    - Outsourcing guidelines compliance
    - IT outsourcing circular requirements
    - Reporting to RBI
    - Inspection facilitation

15. DPDP ACT COMPLIANCE
    - Digital Personal Data Protection Act requirements
    - Consent management
    - Data principal rights
    - Grievance redressal

16. LIABILITY AND INDEMNIFICATION
    - Processor liability for breaches
    - Indemnification for non-compliance
    - Caps based on contract value: ₹{po_value:,.2f}
    - Insurance requirements

17. SIGNATURES
    - For Punjab & Sind Bank (Data Controller)
    - For {vendor_name} (Data Processor)

Include RBI data localization and DPDP Act compliance throughout. Use plain text without markdown formatting.""",

        "ANNEXURES": f"""You are a contract documentation expert.
        CRITICAL LENGTH CONSTRAINT (MANDATORY):
            - The final document MUST NOT exceed 3 A4 pages when rendered as a professional PDF.
            - Target length: 1,200–1,400 words TOTAL.
            - Be concise. Summarize clauses. Avoid repetition.
            - Use short paragraphs and bullet-like sentence structure.
            - If content exceeds the limit, PRIORITIZE legally essential clauses and OMIT minor details.
        
        Generate a concise but legally complete ANNEXURES AND SCHEDULES for Punjab & Sind Bank service agreement using ALL the project data provided below.

{comprehensive_context}

Using ALL the above data from all tables, create detailed annexures:

SCHEDULE A - SCOPE OF WORK
===========================
Project: {project.title}
Department: {project.department}
Category: {project.category}

1. DETAILED DELIVERABLES
   - Based on RFP content and technical specifications
   - Milestone-wise deliverables
   - Quality standards

2. TECHNICAL SPECIFICATIONS
   - From technical review and RFP
   - System architecture requirements
   - Integration specifications
   - Security requirements

3. IMPLEMENTATION TIMELINE
   - Delivery Period: {delivery_period}
   - Phase-wise breakdown
   - Key milestones with dates
   - Dependencies

4. ASSUMPTIONS AND DEPENDENCIES
   - Bank responsibilities
   - Vendor dependencies
   - Third-party requirements

SCHEDULE B - PRICING AND PAYMENT
================================
1. PRICE BREAKDOWN
   - Total Contract Value: ₹{po_value:,.2f}
   - Component-wise pricing
   - Tax details (GST applicable)
   - Currency: Indian Rupees

2. PAYMENT MILESTONES
   - Payment Terms: {payment_terms}
   - Milestone-wise payments
   - Payment schedule with dates
   - Hold-back provisions

3. INVOICE FORMAT
   - Required invoice details
   - Supporting documents
   - Submission process
   - Payment timeline (within 30 days)

4. EMD AND PERFORMANCE GUARANTEE
   - EMD details from tender draft
   - Performance Bank Guarantee requirements
   - Validity period
   - Return conditions

SCHEDULE C - PROJECT TEAM AND GOVERNANCE
========================================
1. BANK PROJECT TEAM
   - Project Sponsor
   - Project Manager
   - Technical Lead
   - Business Analyst
   - Contact: {project.email or 'As per project'}

2. VENDOR PROJECT TEAM
   - Account Manager
   - Project Manager
   - Technical Architect
   - Development Lead
   - QA Lead
   - Support Manager

3. GOVERNANCE STRUCTURE
   - Steering Committee
   - Project Management Committee
   - Technical Committee
   - Meeting frequency

4. RACI MATRIX
   - Roles and responsibilities
   - Decision-making authority
   - Escalation paths

SCHEDULE D - TECHNICAL REQUIREMENTS
===================================
Based on Technical Committee Review:

1. SYSTEM REQUIREMENTS
   - Hardware specifications
   - Software requirements
   - Operating system
   - Database requirements

2. INTEGRATION SPECIFICATIONS
   - API requirements
   - Data exchange formats
   - Integration points with bank systems
   - Middleware requirements

3. SECURITY REQUIREMENTS
   - Based on security assessment
   - Encryption standards (AES-256)
   - Access control (RBAC)
   - Audit logging
   - Vulnerability management

4. PERFORMANCE REQUIREMENTS
   - Response time: <2 seconds
   - Throughput requirements
   - Concurrent user support
   - Availability: 99.9%

5. COMPLIANCE REQUIREMENTS
   - RBI compliance from technical review
   - ISO 27001
   - PCI-DSS if applicable

SCHEDULE E - ACCEPTANCE CRITERIA
================================
1. TESTING PROCEDURES
   - Unit testing requirements
   - Integration testing
   - System testing
   - UAT requirements
   - Performance testing
   - Security testing

2. ACCEPTANCE CRITERIA
   - Functional acceptance
   - Performance acceptance
   - Security acceptance
   - Documentation acceptance

3. SIGN-OFF PROCESS
   - Sign-off authorities
   - Sign-off timelines
   - Defect classification
   - Critical defect: 0 open
   - Major defect: <5 open
   - Conditional acceptance

SCHEDULE F - CHANGE MANAGEMENT
==============================
1. CHANGE REQUEST PROCESS
   - Change request form
   - Submission procedure
   - Impact assessment
   - Approval workflow

2. CHANGE CATEGORIES
   - Minor changes (within scope)
   - Major changes (scope change)
   - Critical changes (contract amendment)

3. APPROVAL AUTHORITY
   - Minor: Project Manager
   - Major: Steering Committee
   - Critical: Competent Authority

4. COST AND TIMELINE IMPACT
   - Cost calculation method
   - Timeline extension process
   - Documentation requirements

SCHEDULE G - EXIT MANAGEMENT
============================
1. TRANSITION PLANNING
   - 90-day transition period
   - Knowledge transfer activities
   - Documentation handover
   - Training requirements

2. DATA HANDOVER
   - Data migration plan
   - Data format specifications
   - Verification procedures
   - Certification of completeness

3. ASSET TRANSFER
   - Bank-owned assets
   - License transfers
   - Documentation
   - Source code (if applicable)

4. POST-EXIT SUPPORT
   - 30-day support period
   - Issue resolution
   - Query handling

SCHEDULE H - SLA AND PENALTY MATRIX
===================================
1. SERVICE LEVELS
   - Availability: 99.9%
   - Response times by priority
   - Resolution times by priority

2. PENALTY CLAUSE
   - {penalty_clause}
   - Calculation formula
   - Monthly cap: 10% of monthly fee
   - Annual cap: 20% of annual contract value

3. SERVICE CREDIT CALCULATION
   - Credit percentage per SLA breach
   - Cumulative calculation
   - Credit note process

SCHEDULE I - COMPLIANCE AND AUDIT
=================================
1. REGULATORY COMPLIANCE
   - RBI compliance requirements
   - Data protection laws
   - IT Act compliance
   - Banking regulations

2. AUDIT REQUIREMENTS
   - Internal audit: Quarterly
   - External audit: Annual
   - RBI inspection: As required
   - Audit report submission: Within 30 days

3. CERTIFICATION REQUIREMENTS
   - ISO 27001
   - SOC 2 Type II
   - Any other applicable

Use plain text without markdown formatting. Include specific details from all project data wherever applicable."""
    }
    
    prompt = prompts.get(agreement_type, "")
    logger.info(f"Prompt built for {agreement_type}, length: {len(prompt)} chars")
    
    logger.info(f"Calling Anthropic API for {agreement_type} generation...")
    logger.info("  Model: claude-sonnet-4-5-20250929")
    logger.info("  Max tokens: 2500")
    
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    content = message.content[0].text
    logger.info(f"Anthropic API response received for {agreement_type}")
    logger.info(f"  Response length: {len(content)} chars")
    
    logger.info("-" * 40)
    logger.info(f"HELPER: generate_agreement_content_from_project_data completed for {agreement_type}")
    logger.info("-" * 40)
    
    return content


def create_agreement_pdf(
    content: str,
    agreement_type: str,
    project_id: str,
    project_title: str,
    vendor_name: str,
    po_number: str
) -> tuple:
    """Create PDF for agreement document"""
    logger.info("-" * 40)
    logger.info(f"HELPER: create_agreement_pdf called")
    logger.info(f"  Agreement type: {agreement_type}")
    logger.info(f"  Project ID: {project_id}")
    logger.info(f"  Vendor: {vendor_name}")
    logger.info("-" * 40)
    
    agreement_info = AGREEMENT_TYPES[agreement_type]
    filename = f"{agreement_type}_{project_id}.pdf"
    filepath = os.path.join(agreement_info["dir"], filename)
    
    logger.info(f"Creating PDF: {filename}")
    logger.info(f"Output path: {filepath}")
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.darkblue
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    center_style = ParagraphStyle(
        'CenterStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    story = []
    
    # Bank Header
    story.append(Paragraph("PUNJAB & SIND BANK", title_style))
    story.append(Paragraph("Head Office: 21, Rajendra Place, New Delhi - 110008", center_style))
    story.append(Spacer(1, 20))
    
    # Agreement Title
    story.append(Paragraph(agreement_info["name"].upper(), title_style))
    story.append(Spacer(1, 10))
    
    # Document Info Table
    doc_info = [
        ["Document Type:", agreement_info["name"]],
        ["Project ID:", project_id],
        ["Project Title:", project_title],
        ["Vendor:", vendor_name],
        ["PO Number:", po_number],
        ["Date:", datetime.now().strftime('%d-%m-%Y')],
    ]
    
    info_table = Table(doc_info, colWidths=[120, 350])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Content
    logger.info("Processing content for PDF...")
    content_lines = content.split('\n')
    logger.info(f"  Total lines: {len(content_lines)}")
    for line in content_lines:
        if line.strip():
            # Check if it's a header (all caps or numbered section)
            if line.strip().isupper() or (len(line) < 100 and line.strip().endswith(':')):
                story.append(Paragraph(line.strip(), header_style))
            else:
                story.append(Paragraph(line.strip(), normal_style))
    
    story.append(Spacer(1, 40))
    
    # Signature Section
    story.append(Paragraph("SIGNATURES", header_style))
    story.append(Spacer(1, 20))
    
    sig_data = [
        ["FOR PUNJAB & SIND BANK", "", f"FOR {vendor_name.upper()}"],
        ["", "", ""],
        ["", "", ""],
        ["Signature: _________________", "", "Signature: _________________"],
        ["Name: _________________", "", "Name: _________________"],
        ["Designation: _________________", "", "Designation: _________________"],
        ["Date: _________________", "", "Date: _________________"],
    ]
    
    sig_table = Table(sig_data, colWidths=[180, 90, 180])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(sig_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 80, center_style))
    story.append(Paragraph(f"Punjab & Sind Bank - {agreement_info['name']}", center_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", center_style))
    
    logger.info("Building PDF document...")
    doc.build(story)
    
    file_size_kb = os.path.getsize(filepath) / 1024
    
    logger.info(f"PDF created successfully:")
    logger.info(f"  Filename: {filename}")
    logger.info(f"  Filepath: {filepath}")
    logger.info(f"  File size: {round(file_size_kb, 2)} KB")
    
    logger.info("-" * 40)
    logger.info("HELPER: create_agreement_pdf completed")
    logger.info("-" * 40)
    
    return filename, filepath, file_size_kb


# ==================== NEW POST API - Generate Agreements by Project ID ====================

@router.post("/generate-agreements/{project_id}")
def generate_agreements_by_project_id(project_id: str):
    """
    Generate all agreement documents (MSA, SLA, NDA, DPA, Annexures) using project_id.
    
    Fetches all data from:
    - project_credentials table
    - functional_assessments table
    - technical_committee_reviews table
    - tender_drafts table
    - publish_rfps table
    - purchase_data table
    - agreement_documents table
    - generated_rfps table (including RFP content)
    
    And passes all data to Claude AI to generate comprehensive agreement documents.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: POST /purchase/generate-agreements/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        # Get project
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        # Get all project data from ALL tables
        logger.info("Fetching all project data from all tables...")
        project_data = get_all_project_data(db, project_id)
        logger.info("All project data fetched successfully")
        
        # Get RFP content
        rfp_content = None
        generated_rfp = project_data.get("generated_rfp")
        if generated_rfp:
            logger.info(f"Attempting to fetch RFP content for rfp_id: {generated_rfp.id}")
            # Try to fetch from API first
            rfp_content = fetch_rfp_content(generated_rfp.id)
            # If API fails, use content from database
            if not rfp_content and generated_rfp.rfp_content:
                logger.info("Using RFP content from database")
                rfp_content = generated_rfp.rfp_content
        else:
            logger.info("No generated RFP found")
        
        # Build comprehensive context from ALL tables
        logger.info("Building comprehensive context from all tables...")
        comprehensive_context = build_comprehensive_context(project_data, rfp_content)
        logger.info(f"Comprehensive context built, length: {len(comprehensive_context)} chars")
        
        # Get vendor and PO details
        purchase_data = project_data.get("purchase_data")
        vendor_bid = project_data.get("vendor_bid")
        
        vendor_name = "Vendor"
        po_number = "N/A"
        po_value = 0
        
        if purchase_data:
            vendor_name = purchase_data.vendor or vendor_name
            po_number = purchase_data.purchase_order_number or po_number
            po_value = purchase_data.po_value or po_value
            logger.info(f"Using purchase_data: vendor={vendor_name}, po_number={po_number}, po_value={po_value}")
        elif vendor_bid:
            vendor_name = vendor_bid.vendor_name
            po_value = vendor_bid.commercial_bid
            logger.info(f"Using vendor_bid: vendor={vendor_name}, po_value={po_value}")
        
        # Check if agreements already exist and delete them
        logger.info("Checking for existing agreements...")
        existing_agreements = db.query(AgreementDocument).filter(
            AgreementDocument.project_pk_id == project.pk_id
        ).all()
        
        if existing_agreements:
            logger.info(f"Found {len(existing_agreements)} existing agreements - deleting...")
            for agreement in existing_agreements:
                if agreement.filepath and os.path.exists(agreement.filepath):
                    logger.debug(f"  Deleting file: {agreement.filepath}")
                    os.remove(agreement.filepath)
                db.delete(agreement)
            db.commit()
            logger.info("Existing agreements deleted")
        
        # Generate all agreements
        logger.info("Starting agreement generation for all types...")
        generated_docs = []
        
        for agreement_type in AGREEMENT_TYPES.keys():
            logger.info(f"Generating {agreement_type}...")
            
            # Generate content using AI with comprehensive context from all tables
            logger.info(f"  Calling AI to generate content for {agreement_type}...")
            content = generate_agreement_content_from_project_data(
                agreement_type=agreement_type,
                comprehensive_context=comprehensive_context,
                project_data=project_data
            )
            logger.info(f"  Content generated for {agreement_type}, length: {len(content)} chars")
            
            # Create PDF
            logger.info(f"  Creating PDF for {agreement_type}...")
            filename, filepath, file_size_kb = create_agreement_pdf(
                content=content,
                agreement_type=agreement_type,
                project_id=project_id,
                project_title=project.title,
                vendor_name=vendor_name,
                po_number=po_number
            )
            logger.info(f"  PDF created: {filename} ({round(file_size_kb, 2)} KB)")
            
            # Save to database
            logger.info(f"  Saving {agreement_type} to database...")
            agreement_doc = AgreementDocument(
                project_pk_id=project.pk_id,
                project_id=project.id,
                purchase_order_number=po_number,
                agreement_type=agreement_type,
                content=content,
                filename=filename,
                filepath=filepath,
                file_size_kb=file_size_kb,
                vendor_name=vendor_name,
                po_value=po_value
            )
            
            db.add(agreement_doc)
            
            generated_docs.append({
                "agreement_type": agreement_type,
                "name": AGREEMENT_TYPES[agreement_type]["name"],
                "filename": filename,
                "filepath": filepath,
                "file_size_kb": round(file_size_kb, 2),
                "download_url": f"/purchase/download/agreement/{project_id}/{agreement_type}"
            })
            
            logger.info(f"  {agreement_type} generation complete")
        
        logger.info("Committing all agreements to database...")
        db.commit()
        logger.info("All agreements committed successfully")
        
        # Prepare data source summary
        data_sources = {
            "project_credentials": True,
            "functional_assessments": project_data.get("functional_assessment") is not None,
            "technical_committee_reviews": project_data.get("technical_review") is not None,
            "tender_drafts": project_data.get("tender_draft") is not None,
            "publish_rfps": project_data.get("publish_rfp") is not None,
            "vendor_bids": project_data.get("vendor_bid") is not None,
            "all_vendor_bids_count": len(project_data.get("all_vendor_bids", [])),
            "generated_rfps": generated_rfp is not None,
            "rfp_content_available": rfp_content is not None,
            "purchase_data": purchase_data is not None,
            "existing_agreement_documents": len(project_data.get("agreement_documents", []))
        }
        
        logger.info("Data sources used:")
        for source, value in data_sources.items():
            logger.info(f"  - {source}: {value}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /purchase/generate-agreements/{project_id} - SUCCESS")
        logger.info(f"Generated {len(generated_docs)} agreement documents")
        logger.info("=" * 60)
        
        return {
            "message": "All agreements generated successfully using comprehensive project data",
            "project_id": project.id,
            "project_title": project.title,
            "vendor": vendor_name,
            "purchase_order_number": po_number,
            "po_value": po_value,
            "data_sources_used": data_sources,
            "agreements": generated_docs,
            "created_at": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_agreements_by_project_id: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")




# ==================== DOWNLOAD AGREEMENT APIs ====================

@router.get("/download/agreement/{project_id}/{agreement_type}")
def download_agreement(project_id: str, agreement_type: str):
    """Download a specific agreement document by project ID and type"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /purchase/download/agreement/{project_id}/{agreement_type}")
    logger.info(f"Parameters - project_id: {project_id}, agreement_type: {agreement_type}")
    logger.info("=" * 60)
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        if agreement_type not in AGREEMENT_TYPES:
            logger.warning(f"Invalid agreement type: {agreement_type}")
            logger.error(f"Valid types: {list(AGREEMENT_TYPES.keys())}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agreement type. Valid types: {', '.join(AGREEMENT_TYPES.keys())}"
            )
        
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title}")
        
        logger.info(f"Querying {agreement_type} agreement for project...")
        agreement = db.query(AgreementDocument).filter(
            AgreementDocument.project_pk_id == project.pk_id,
            AgreementDocument.agreement_type == agreement_type
        ).first()
        
        if not agreement:
            logger.warning(f"No {agreement_type} found for project: {project_id}")
            raise HTTPException(
                status_code=404,
                detail=f"No {AGREEMENT_TYPES[agreement_type]['name']} found for this project"
            )
        
        logger.info(f"Agreement found: {agreement.filename}")
        
        if not agreement.filepath or not os.path.exists(agreement.filepath):
            logger.error(f"Agreement PDF file not found: {agreement.filepath}")
            raise HTTPException(status_code=404, detail="Agreement PDF file not found")
        
        logger.info(f"Returning file: {agreement.filepath}")
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /purchase/download/agreement - SUCCESS")
        logger.info("=" * 60)
        
        return FileResponse(
            path=agreement.filepath,
            filename=agreement.filename,
            media_type="application/pdf"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_agreement: {str(e)}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/download/msa/{project_id}")
def download_msa(project_id: str):
    """Download Master Service Agreement by project ID"""
    logger.info("API CALLED: GET /purchase/download/msa/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("Redirecting to download_agreement with type=MSA")
    return download_agreement(project_id, "MSA")


@router.get("/download/sla/{project_id}")
def download_sla(project_id: str):
    """Download Service Level Agreement by project ID"""
    logger.info("API CALLED: GET /purchase/download/sla/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("Redirecting to download_agreement with type=SLA")
    return download_agreement(project_id, "SLA")


@router.get("/download/nda/{project_id}")
def download_nda(project_id: str):
    """Download Non Disclosure Agreement by project ID"""
    logger.info("API CALLED: GET /purchase/download/nda/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("Redirecting to download_agreement with type=NDA")
    return download_agreement(project_id, "NDA")


@router.get("/download/dpa/{project_id}")
def download_dpa(project_id: str):
    """Download Data Processing Agreement by project ID"""
    logger.info("API CALLED: GET /purchase/download/dpa/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("Redirecting to download_agreement with type=DPA")
    return download_agreement(project_id, "DPA")


@router.get("/download/annexures/{project_id}")
def download_annexures(project_id: str):
    """Download Annexures & Schedules by project ID"""
    logger.info("API CALLED: GET /purchase/download/annexures/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("Redirecting to download_agreement with type=ANNEXURES")
    return download_agreement(project_id, "ANNEXURES")
import zipfile
import io

@router.get("/agreements/{project_id}")
def download_all_agreements_zip(project_id: str):
    db = SessionLocal()
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        agreements = db.query(AgreementDocument).filter(
            AgreementDocument.project_pk_id == project.pk_id
        ).all()

        if not agreements:
            raise HTTPException(status_code=404, detail="No agreements found")

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for agreement in agreements:
                if agreement.filepath and os.path.exists(agreement.filepath):
                    zip_file.write(
                        agreement.filepath,
                        arcname=agreement.filename
                    )

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=agreements_{project_id}.zip"
            }
        )

    finally:
        db.close()


# ==================== ANTHROPIC API INTEGRATION FOR PO ====================

def generate_po_content_with_ai(
    project_id: str,
    project_title: str,
    purchase_order_number: str,
    vendor_name: str,
    commercial_bid: float,
    publication_date: Optional[str] = None
) -> str:
    """Generate purchase order content using Anthropic API"""
    logger.info("-" * 40)
    logger.info("HELPER: generate_po_content_with_ai called")
    logger.info(f"  Project ID: {project_id}")
    logger.info(f"  Project Title: {project_title}")
    logger.info(f"  PO Number: {purchase_order_number}")
    logger.info(f"  Vendor: {vendor_name}")
    logger.info(f"  Commercial Bid: {commercial_bid}")
    logger.info(f"  Publication Date: {publication_date}")
    logger.info("-" * 40)
    
    logger.info("Checking for ANTHROPIC_API_KEY...")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not found in environment variables"
        )
    logger.info("ANTHROPIC_API_KEY found")
    
    logger.info("Creating Anthropic client...")
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""Generate a professional Purchase Order document with the following details:

Project ID: {project_id}
Project Title: {project_title}
Purchase Order Number: {purchase_order_number}
Vendor Name: {vendor_name}
PO Value: ₹{commercial_bid:,.2f}
Publication Date: {publication_date or 'N/A'}
Order Date: {datetime.now().strftime('%Y-%m-%d')}

Please create a complete Purchase Order document including:
1. Header with company name "Punjab & Sind Bank" and address
2. PO Number, Date, and Vendor details section
3. Order details with itemized description
4. Terms and Conditions (Delivery, Payment, Warranty, Penalties)
5. Authorized signature section
6. Footer with bank contact information

Format it professionally with clear sections. Use plain text formatting that can be converted to PDF.
Do not use markdown formatting like ** or ##. Use UPPERCASE for headers instead."""

    logger.info("Calling Anthropic API for PO content generation...")
    logger.info("  Model: claude-sonnet-4-5-20250929")
    logger.info("  Max tokens: 2000")
    
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    content = message.content[0].text
    logger.info(f"Anthropic API response received, length: {len(content)} chars")
    
    logger.info("-" * 40)
    logger.info("HELPER: generate_po_content_with_ai completed")
    logger.info("-" * 40)
    
    return content


def create_po_pdf(
    po_content: str,
    purchase_order_number: str,
    project_id: str,
    project_title: str,
    vendor_name: str,
    po_value: float,
    publication_date: Optional[str] = None
) -> tuple:
    """Create PDF from purchase order content"""
    logger.info("-" * 40)
    logger.info("HELPER: create_po_pdf called")
    logger.info(f"  PO Number: {purchase_order_number}")
    logger.info(f"  Project ID: {project_id}")
    logger.info(f"  Vendor: {vendor_name}")
    logger.info(f"  PO Value: {po_value}")
    logger.info("-" * 40)
    
    filename = f"{purchase_order_number}.pdf"
    filepath = os.path.join(PO_STORAGE_DIR, filename)
    
    logger.info(f"Creating PDF: {filename}")
    logger.info(f"Output path: {filepath}")
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_LEFT,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.darkblue
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    center_style = ParagraphStyle(
        'CenterStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    story = []
    
    # Bank Header
    story.append(Paragraph("PUNJAB & SIND BANK", title_style))
    story.append(Paragraph("Head Office: 21, Rajendra Place, New Delhi - 110008", center_style))
    story.append(Paragraph("CIN: L65110PB1908GOI002217", center_style))
    story.append(Spacer(1, 20))
    
    # Purchase Order Title
    story.append(Paragraph("PURCHASE ORDER", title_style))
    story.append(Spacer(1, 10))
    
    # PO Details Table
    po_details = [
        ["PO Number:", purchase_order_number],
        ["PO Date:", datetime.now().strftime('%d-%m-%Y')],
        ["Project ID:", project_id],
        ["Project Title:", project_title],
    ]
    
    po_table = Table(po_details, colWidths=[150, 300])
    po_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(po_table)
    story.append(Spacer(1, 20))
    
    # Vendor Details
    story.append(Paragraph("VENDOR DETAILS", header_style))
    vendor_details = [
        ["Vendor Name:", vendor_name],
        ["Selection Date:", publication_date or "N/A"],
    ]
    vendor_table = Table(vendor_details, colWidths=[150, 300])
    vendor_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vendor_table)
    story.append(Spacer(1, 20))
    
    # Order Details
    story.append(Paragraph("ORDER DETAILS", header_style))
    order_data = [
        ["S.No", "Description", "Amount (₹)"],
        ["1", project_title, f"{po_value:,.2f}"],
        ["", "Total Amount", f"₹ {po_value:,.2f}"],
    ]
    order_table = Table(order_data, colWidths=[50, 300, 100])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))
    
    # AI Generated Content
    story.append(Paragraph("TERMS AND CONDITIONS", header_style))
    logger.info("Processing PO content for PDF...")
    content_lines = po_content.split('\n')
    logger.info(f"  Total lines: {len(content_lines)}")
    for line in content_lines:
        if line.strip():
            story.append(Paragraph(line.strip(), normal_style))
    
    story.append(Spacer(1, 40))
    
    # Signature Section
    sig_data = [
        ["Authorized Signatory", "", "Vendor Acceptance"],
        ["", "", ""],
        ["Name: _________________", "", "Name: _________________"],
        ["Designation: ___________", "", "Designation: ___________"],
        ["Date: _________________", "", "Date: _________________"],
    ]
    sig_table = Table(sig_data, colWidths=[180, 90, 180])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(sig_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 80, center_style))
    story.append(Paragraph("Punjab & Sind Bank - Generated Purchase Order", center_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", center_style))
    
    logger.info("Building PDF document...")
    doc.build(story)
    
    file_size_kb = os.path.getsize(filepath) / 1024
    
    logger.info(f"PDF created successfully:")
    logger.info(f"  Filename: {filename}")
    logger.info(f"  Filepath: {filepath}")
    logger.info(f"  File size: {round(file_size_kb, 2)} KB")
    
    logger.info("-" * 40)
    logger.info("HELPER: create_po_pdf completed")
    logger.info("-" * 40)
    
    return filename, filepath, file_size_kb


# ==================== POST API - Create PO from Vendor Evaluation ====================

@router.post("/create-from-evaluation")
def create_purchase_order_from_evaluation(request: VendorEvaluationRequest):
    """Create purchase order from vendor evaluation response."""
    logger.info("=" * 60)
    logger.info("API CALLED: POST /purchase/create-from-evaluation")
    logger.info("=" * 60)
    logger.info("Request Parameters:")
    logger.info(f"  - project_id: {request.project_id}")
    logger.info(f"  - project_title: {request.project_title}")
    logger.info(f"  - winner.vendor_name: {request.winner.vendor_name}")
    logger.info(f"  - winner.commercial_bid: {request.winner.commercial_bid}")
    logger.info(f"  - winner.publication_date: {request.winner.publication_date}")
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {request.project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {request.project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        logger.info("Checking for existing purchase data...")
        existing = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            logger.info(f"Purchase order already exists: {existing.purchase_order_number}")
            logger.info("=" * 60)
            logger.info("API RESPONSE: POST /purchase/create-from-evaluation - EXISTING PO RETURNED")
            logger.info("=" * 60)
            
            return {
                "message": "Purchase order already exists for this project",
                "purchase_order_number": existing.purchase_order_number,
                "project_id": project.id,
                "project_title": project.title,
                "winner": {
                    "vendor_name": request.winner.vendor_name,
                    "commercial_bid": request.winner.commercial_bid,
                    "publication_date": request.winner.publication_date
                },
                "po_filename": existing.po_filename,
                "po_filepath": existing.po_filepath,
                "created_at": existing.created_at.isoformat() if existing.created_at else None
            }
        
        logger.info("No existing PO found. Creating new purchase order...")
        
        purchase_order_number = generate_purchase_order_number(request.project_id)
        logger.info(f"Generated PO number: {purchase_order_number}")
        
        logger.info("Generating PO content with AI...")
        po_content = generate_po_content_with_ai(
            project_id=request.project_id,
            project_title=request.project_title or project.title,
            purchase_order_number=purchase_order_number,
            vendor_name=request.winner.vendor_name,
            commercial_bid=request.winner.commercial_bid,
            publication_date=request.winner.publication_date
        )
        logger.info(f"PO content generated, length: {len(po_content)} chars")
        
        logger.info("Creating PO PDF...")
        po_filename, po_filepath, file_size_kb = create_po_pdf(
            po_content=po_content,
            purchase_order_number=purchase_order_number,
            project_id=request.project_id,
            project_title=request.project_title or project.title,
            vendor_name=request.winner.vendor_name,
            po_value=request.winner.commercial_bid,
            publication_date=request.winner.publication_date
        )
        logger.info(f"PO PDF created: {po_filename} ({round(file_size_kb, 2)} KB)")
        
        logger.info("Saving purchase data to database...")
        purchase_data = PurchaseData(
            project_pk_id=project.pk_id,
            project_id=project.id,
            purchase_order_number=purchase_order_number,
            vendor=request.winner.vendor_name,
            po_value=request.winner.commercial_bid,
            po_content=po_content,
            po_filename=po_filename,
            po_filepath=po_filepath,
            file_size_kb=file_size_kb
        )
        
        db.add(purchase_data)
        
        logger.info("Committing transaction...")
        db.commit()
        logger.info("Transaction committed successfully")
        
        db.refresh(purchase_data)
        logger.info(f"Purchase data saved with id: {purchase_data.id}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /purchase/create-from-evaluation - SUCCESS")
        logger.info(f"Created PO: {purchase_order_number}")
        logger.info("=" * 60)
        
        return {
            "message": "Purchase order created successfully",
            "purchase_order_number": purchase_data.purchase_order_number,
            "project_id": project.id,
            "project_title": project.title,
            "winner": {
                "vendor_name": request.winner.vendor_name,
                "commercial_bid": request.winner.commercial_bid,
                "publication_date": request.winner.publication_date
            },
            "po_filename": purchase_data.po_filename,
            "po_filepath": purchase_data.po_filepath,
            "file_size_kb": round(purchase_data.file_size_kb, 2) if purchase_data.file_size_kb else None,
            "created_at": purchase_data.created_at.isoformat() if purchase_data.created_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_purchase_order_from_evaluation: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


# ==================== DOWNLOAD PO APIs ====================

@router.get("/download/{project_id}")
def download_purchase_order(project_id: str):
    """Download the generated purchase order PDF for a project"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /purchase/download/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title}")
        
        logger.info("Querying purchase data...")
        purchase_data = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if not purchase_data:
            logger.warning(f"No purchase order found for project: {project_id}")
            raise HTTPException(status_code=404, detail="No purchase order found for this project")
        
        logger.info(f"Purchase order found: {purchase_data.purchase_order_number}")
        
        if not purchase_data.po_filepath or not os.path.exists(purchase_data.po_filepath):
            logger.error(f"PO PDF file not found: {purchase_data.po_filepath}")
            raise HTTPException(status_code=404, detail="Purchase order PDF file not found")
        
        logger.info(f"Returning file: {purchase_data.po_filepath}")
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /purchase/download/{project_id} - SUCCESS")
        logger.info("=" * 60)
        
        return FileResponse(
            path=purchase_data.po_filepath,
            filename=purchase_data.po_filename,
            media_type="application/pdf"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_purchase_order: {str(e)}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/download/by-po-number/{po_number}")
def download_purchase_order_by_po_number(po_number: str):
    """Download the generated purchase order PDF by PO number"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /purchase/download/by-po-number/{po_number}")
    logger.info(f"Parameter - po_number: {po_number}")
    logger.info("=" * 60)
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying purchase data with po_number: {po_number}")
        purchase_data = db.query(PurchaseData).filter(
            PurchaseData.purchase_order_number == po_number
        ).first()
        
        if not purchase_data:
            logger.warning(f"Purchase order not found: {po_number}")
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        logger.info(f"Purchase order found for project: {purchase_data.project_id}")
        
        if not purchase_data.po_filepath or not os.path.exists(purchase_data.po_filepath):
            logger.error(f"PO PDF file not found: {purchase_data.po_filepath}")
            raise HTTPException(status_code=404, detail="Purchase order PDF file not found")
        
        logger.info(f"Returning file: {purchase_data.po_filepath}")
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /purchase/download/by-po-number/{po_number} - SUCCESS")
        logger.info("=" * 60)
        
        return FileResponse(
            path=purchase_data.po_filepath,
            filename=purchase_data.po_filename,
            media_type="application/pdf"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_purchase_order_by_po_number: {str(e)}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


# ==================== POST API - Full Submit ====================

@router.post("/submit")
def submit_purchase_data(request: PurchaseDataRequest):
    """Submit purchase order data for a project"""
    logger.info("=" * 60)
    logger.info("API CALLED: POST /purchase/submit")
    logger.info("=" * 60)
    logger.info("Request Parameters:")
    logger.info(f"  - project_id: {request.project_id}")
    logger.info(f"  - purchase_order_number: {request.purchase_order_number}")
    logger.info(f"  - vendor: {request.vendor}")
    logger.info(f"  - po_value: {request.po_value}")
    logger.info(f"  - delivery_period: {request.delivery_period}")
    logger.info(f"  - payment_terms: {request.payment_terms}")
    logger.info(f"  - warranty_period: {request.warranty_period}")
    logger.info(f"  - penalty_clause: {request.penalty_clause}")
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {request.project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {request.project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        logger.info("Validating payment terms and warranty period...")
        payment_terms = validate_payment_terms(request.payment_terms)
        warranty_period = validate_warranty_period(request.warranty_period)
        logger.info("Validation passed")
        
        logger.info("Checking for existing purchase data...")
        existing = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            logger.info(f"Existing purchase data found with id: {existing.id}")
            logger.info("Updating existing purchase data...")
            
            existing.purchase_order_number = request.purchase_order_number
            existing.vendor = request.vendor
            existing.po_value = request.po_value
            existing.delivery_period = request.delivery_period
            existing.payment_terms = payment_terms
            existing.warranty_period = warranty_period
            existing.penalty_clause = request.penalty_clause
            
            logger.info("Committing transaction...")
            db.commit()
            logger.info("Transaction committed successfully")
            
            db.refresh(existing)
            
            logger.info("=" * 60)
            logger.info("API RESPONSE: POST /purchase/submit - SUCCESS (UPDATE)")
            logger.info(f"Updated purchase_id: {existing.id}")
            logger.info("=" * 60)
            
            return {
                "message": "Purchase data updated successfully",
                "purchase_id": existing.id,
                "project_id": project.id,
                "project_title": project.title,
                "data": {
                    "purchase_order_number": existing.purchase_order_number,
                    "vendor": existing.vendor,
                    "po_value": existing.po_value,
                    "delivery_period": existing.delivery_period,
                    "payment_terms": existing.payment_terms,
                    "warranty_period": existing.warranty_period,
                    "penalty_clause": existing.penalty_clause
                },
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
                "updated_at": existing.updated_at.isoformat() if existing.updated_at else None
            }
        
        else:
            logger.info("No existing purchase data found. Creating new record...")
            
            # Check if PO number already exists
            logger.info(f"Checking if PO number already exists: {request.purchase_order_number}")
            existing_po = db.query(PurchaseData).filter(
                PurchaseData.purchase_order_number == request.purchase_order_number
            ).first()
            
            if existing_po:
                logger.warning(f"PO number already exists: {request.purchase_order_number}")
                logger.error("Raising HTTPException 400: PO number already exists")
                raise HTTPException(
                    status_code=400,
                    detail=f"Purchase order number '{request.purchase_order_number}' already exists"
                )
            
            logger.info("Creating new PurchaseData record...")
            purchase_data = PurchaseData(
                project_pk_id=project.pk_id,
                project_id=project.id,
                purchase_order_number=request.purchase_order_number,
                vendor=request.vendor,
                po_value=request.po_value,
                delivery_period=request.delivery_period,
                payment_terms=payment_terms,
                warranty_period=warranty_period,
                penalty_clause=request.penalty_clause
            )
            
            db.add(purchase_data)
            
            logger.info("Committing transaction...")
            db.commit()
            logger.info("Transaction committed successfully")
            
            db.refresh(purchase_data)
            logger.info(f"Purchase data created with id: {purchase_data.id}")
            
            logger.info("=" * 60)
            logger.info("API RESPONSE: POST /purchase/submit - SUCCESS (CREATE)")
            logger.info(f"Created purchase_id: {purchase_data.id}")
            logger.info("=" * 60)
            
            return {
                "message": "Purchase data submitted successfully",
                "purchase_id": purchase_data.id,
                "project_id": project.id,
                "project_title": project.title,
                "data": {
                    "purchase_order_number": purchase_data.purchase_order_number,
                    "vendor": purchase_data.vendor,
                    "po_value": purchase_data.po_value,
                    "delivery_period": purchase_data.delivery_period,
                    "payment_terms": purchase_data.payment_terms,
                    "warranty_period": purchase_data.warranty_period,
                    "penalty_clause": purchase_data.penalty_clause
                },
                "created_at": purchase_data.created_at.isoformat() if purchase_data.created_at else None
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_purchase_data: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


# ==================== GET APIs ====================

@router.get("/list")
def get_all_purchase_data():
    """Get all purchase data records"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /purchase/list")
    logger.info("=" * 60)
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info("Querying all purchase data records ordered by created_at DESC...")
        records = db.query(PurchaseData).order_by(PurchaseData.created_at.desc()).all()
        logger.info(f"Found {len(records)} purchase data records")
        
        result = []
        for idx, record in enumerate(records):
            logger.debug(f"Processing record {idx + 1}: {record.purchase_order_number}")
            
            project = db.query(ProjectCredential).filter(
                ProjectCredential.pk_id == record.project_pk_id
            ).first()
            
            result.append({
                "id": record.id,
                "project_id": record.project_id,
                "project_title": project.title if project else None,
                "purchase_order_number": record.purchase_order_number,
                "vendor": record.vendor,
                "po_value": record.po_value,
                "delivery_period": record.delivery_period,
                "payment_terms": record.payment_terms,
                "warranty_period": record.warranty_period,
                "penalty_clause": record.penalty_clause,
                "po_filename": record.po_filename,
                "file_size_kb": round(record.file_size_kb, 2) if record.file_size_kb else None,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None
            })
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /purchase/list - SUCCESS")
        logger.info(f"Returning {len(result)} records")
        logger.info("=" * 60)
        
        return {
            "total_records": len(result),
            "purchase_data": result
        }
    
    except Exception as e:
        logger.error(f"Error in get_all_purchase_data: {str(e)}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/{project_id}")
def get_purchase_data_by_project(project_id: str):
    """Get purchase data for a specific project"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /purchase/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title}")
        
        logger.info("Querying purchase data...")
        purchase_data = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if not purchase_data:
            logger.warning(f"No purchase data found for project: {project_id}")
            raise HTTPException(status_code=404, detail="No purchase data found for this project")
        
        logger.info(f"Purchase data found: {purchase_data.purchase_order_number}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /purchase/{project_id} - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "project_id": project.id,
            "project_title": project.title,
            "purchase_data": {
                "id": purchase_data.id,
                "purchase_order_number": purchase_data.purchase_order_number,
                "vendor": purchase_data.vendor,
                "po_value": purchase_data.po_value,
                "delivery_period": purchase_data.delivery_period,
                "payment_terms": purchase_data.payment_terms,
                "warranty_period": purchase_data.warranty_period,
                "penalty_clause": purchase_data.penalty_clause,
                "po_filename": purchase_data.po_filename,
                "po_filepath": purchase_data.po_filepath,
                "file_size_kb": round(purchase_data.file_size_kb, 2) if purchase_data.file_size_kb else None,
                "created_at": purchase_data.created_at.isoformat() if purchase_data.created_at else None,
                "updated_at": purchase_data.updated_at.isoformat() if purchase_data.updated_at else None
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_purchase_data_by_project: {str(e)}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/options/payment-terms")
def get_payment_terms_options():
    """Get valid payment terms options"""
    logger.info("API CALLED: GET /purchase/options/payment-terms")
    logger.info(f"Returning payment terms: {VALID_PAYMENT_TERMS}")
    return {
        "payment_terms": VALID_PAYMENT_TERMS
    }


@router.get("/options/warranty-periods")
def get_warranty_period_options():
    """Get valid warranty period options"""
    logger.info("API CALLED: GET /purchase/options/warranty-periods")
    logger.info(f"Returning warranty periods: {VALID_WARRANTY_PERIODS}")
    return {
        "warranty_periods": VALID_WARRANTY_PERIODS
    }


logger.info("=" * 60)
logger.info("PURCHASE MODULE LOADED SUCCESSFULLY")
logger.info("=" * 60)
