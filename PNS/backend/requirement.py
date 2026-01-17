from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional
from database import (
    SessionLocal, ProjectCredential, UploadedFile, TrackProgress, 
    RejectedProject, ProjectNavigation, WORKFLOW_PAGES, 
    STAGE_COMPONENT_MAP, COMPONENT_STAGE_MAP
)
from datetime import datetime
import os
import re
import faiss
import numpy as np
import string
from sentence_transformers import SentenceTransformer
import PyPDF2
from docx import Document
import openpyxl
from io import BytesIO
import logging

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("REQUIREMENT MODULE INITIALIZATION STARTED")
logger.info("=" * 60)

router = APIRouter(prefix="/requirements", tags=["Requirements"])
logger.info("Router created with prefix: /requirements")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info(f"Upload directory: {UPLOAD_DIR}")

FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss.index")
logger.info(f"FAISS index path: {FAISS_INDEX_PATH}")

logger.info("Loading SentenceTransformer model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
dimension = 384 
logger.info(f"Embedding model loaded, dimension: {dimension}")

if os.path.exists(FAISS_INDEX_PATH):
    logger.info("Loading existing FAISS index...")
    faiss_index = faiss.read_index(FAISS_INDEX_PATH)
    logger.info(f"FAISS index loaded with {faiss_index.ntotal} vectors")
else:
    logger.info("Creating new FAISS index...")
    faiss_index = faiss.IndexFlatL2(dimension)
    logger.info("New FAISS index created")

FAISS_METADATA_PATH = os.path.join(BASE_DIR, "faiss_metadata.npy")
if os.path.exists(FAISS_METADATA_PATH):
    logger.info("Loading FAISS metadata...")
    faiss_metadata = list(np.load(FAISS_METADATA_PATH, allow_pickle=True))
    logger.info(f"FAISS metadata loaded with {len(faiss_metadata)} entries")
else:
    logger.info("Creating new FAISS metadata list")
    faiss_metadata = []

logger.info("=" * 60)
logger.info("REQUIREMENT MODULE INITIALIZED SUCCESSFULLY")
logger.info("=" * 60)


# ==================== PYDANTIC MODELS FOR PROGRESS ====================

class UpdateProgressRequest(BaseModel):
    project_id: str
    page_number: int
    is_completed: bool


class ProgressResponse(BaseModel):
    project_id: str
    current_page: int
    overall_progress: float
    status: str


# ==================== PAGE FIELD MAPPING ====================
# Maps frontend page numbers to database column names
# Frontend has 10 pages, DB has columns with different naming
# Page 3 (TechnicalReview) includes RFP generation, so we mark page_4_rfp_generation too

PAGE_FIELD_MAPPING = {
    1: "page_1_requirement",        # RequirementForm
    2: "page_2_functional",         # FunctionalAnalysis
    3: "page_3_technical",          # TechnicalReview (also marks page_4_rfp_generation)
    4: "page_5_tender_draft",       # TenderDrafting
    5: "page_6_authority_approval", # ApprovalGate
    6: "page_7_publish_rfp",        # PublishRFP
    7: "page_8_vendor_bidding",     # ReceiveBids
    8: "page_9_vendor_evaluation",  # VendorEvaluation
    9: "page_10_purchase_order",    # PurchaseOrder
    10: "page_10_contract_signing"  # ContractSigning (NEW - for 100% completion)
}

PAGE_NAME_MAPPING = {
    1: "Requirement Submission",
    2: "Functional Analysis",
    3: "Technical Review",
    4: "Tender Drafting",
    5: "Authority Approval",
    6: "Publish RFP",
    7: "Receive Bids",
    8: "Vendor Evaluation",
    9: "Purchase Order",
    10: "Contract Signing"
}


# ==================== HELPER FUNCTIONS ====================

def build_project_id(pk_id: int) -> str:
    """Generate collision-proof business ID (file-safe format)"""
    today = datetime.now()
    return f"PSB-PROC-{today.year}-{today.month}-{today.day}-{pk_id}"


def parse_estimated_amount(value: str) -> float:
    """
    Accepts:
    - 2.5
    - 2.5 CR
    - 3.8 caror
    Converts to RUPEES
    """

    value = value.lower().strip()

    match = re.search(r"(\d+(\.\d+)?)", value)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid estimated amount format"
        )

    number = float(match.group(1))

    # if any(k in value for k in ["cr", "crore", "caror"]):
    #     return number * 10_000_000

    return number


def save_faiss():
    """Persist FAISS index and metadata"""
    logger.info("Saving FAISS index and metadata...")
    faiss.write_index(faiss_index, FAISS_INDEX_PATH)
    np.save(FAISS_METADATA_PATH, np.array(faiss_metadata, dtype=object))
    logger.info("FAISS index and metadata saved")


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc = Document(BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""


def extract_text_from_xlsx(content: bytes) -> str:
    """Extract text from XLSX file"""
    try:
        wb = openpyxl.load_workbook(BytesIO(content), read_only=True)
        text = ""
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = " ".join([str(cell) for cell in row if cell is not None])
                text += row_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"XLSX extraction error: {e}")
        return ""


def extract_text(content: bytes, file_extension: str) -> str:
    """Extract text based on file type"""
    if file_extension == ".pdf":
        return extract_text_from_pdf(content)
    elif file_extension in [".docx", ".doc"]:
        return extract_text_from_docx(content)
    elif file_extension in [".xlsx", ".xls"]:
        return extract_text_from_xlsx(content)
    return ""


def get_embedding(text: str) -> np.ndarray:
    """Generate embedding for text"""
    if not text:
        return np.zeros((1, dimension), dtype="float32")
    
    # Truncate text if too long (model has max token limit)
    text = text[:10000]
    embedding = embedding_model.encode([text])
    return embedding.astype("float32")


def get_file_label(index: int) -> str:
    """Convert index to letter: 0->a, 1->b, 25->z, 26->aa, 27->ab..."""
    result = ""
    while index >= 0:
        result = string.ascii_lowercase[index % 26] + result
        index = index // 26 - 1
    return result


def get_file_extension(filename: str) -> str:
    """Extract file extension"""
    return os.path.splitext(filename)[1].lower()


def calculate_overall_progress(progress: TrackProgress) -> float:
    """Calculate overall progress percentage based on completed pages"""
    # Use getattr for page_10_contract_signing in case column doesn't exist yet
    contract_signing = getattr(progress, 'page_10_contract_signing', False) or False
    
    completed_count = sum([
        progress.page_1_requirement,
        progress.page_2_functional,
        progress.page_3_technical,
        progress.page_4_rfp_generation,
        progress.page_5_tender_draft,
        progress.page_6_authority_approval,
        progress.page_7_publish_rfp,
        progress.page_8_vendor_bidding,
        progress.page_9_vendor_evaluation,
        progress.page_10_purchase_order,
        contract_signing  # New column for ContractSigning
    ])
    return (completed_count / 11) * 100


def get_current_page(progress: TrackProgress) -> int:
    """Determine the current active page based on completion status"""
    # Use getattr for page_10_contract_signing in case column doesn't exist yet
    contract_signing = getattr(progress, 'page_10_contract_signing', False) or False
    
    pages = [
        progress.page_1_requirement,
        progress.page_2_functional,
        progress.page_3_technical,
        progress.page_4_rfp_generation,
        progress.page_5_tender_draft,
        progress.page_6_authority_approval,
        progress.page_7_publish_rfp,
        progress.page_8_vendor_bidding,
        progress.page_9_vendor_evaluation,
        progress.page_10_purchase_order,
        contract_signing  # New column for ContractSigning
    ]
    
    # Find the first incomplete page
    for i, completed in enumerate(pages):
        if not completed:
            return i + 1
    
    return 11  # All completed


# ==================== PROGRESS TRACKING APIs ====================

@router.post("/progress/update")
def update_progress(request: UpdateProgressRequest):
    """
    Update the progress for a specific page/stage of a project.
    
    - page_number: 1-10 (corresponding to workflow stages)
    - is_completed: True/False
    
    Page Mapping (Frontend → DB Column):
    1: RequirementForm      → page_1_requirement
    2: FunctionalAnalysis   → page_2_functional
    3: TechnicalReview      → page_3_technical + page_4_rfp_generation
    4: TenderDrafting       → page_5_tender_draft
    5: ApprovalGate         → page_6_authority_approval
    6: PublishRFP           → page_7_publish_rfp
    7: ReceiveBids          → page_8_vendor_bidding
    8: VendorEvaluation     → page_9_vendor_evaluation
    9: PurchaseOrder        → page_10_purchase_order
    10: ContractSigning     → (marks workflow complete)
    """
    logger.info("=" * 60)
    logger.info("API CALLED: POST /requirements/progress/update")
    logger.info(f"Request - project_id: {request.project_id}, page: {request.page_number}, completed: {request.is_completed}")
    logger.info("=" * 60)
    
    if request.page_number < 1 or request.page_number > 10:
        logger.error(f"Invalid page number: {request.page_number}")
        raise HTTPException(status_code=400, detail="Page number must be between 1 and 10")
    
    db = SessionLocal()
    
    try:
        # Get project
        logger.info(f"Querying project with id: {request.project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found: {request.project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title}")
        
        # Get or create progress record
        logger.info("Querying progress record...")
        progress = db.query(TrackProgress).filter(
            TrackProgress.project_id == request.project_id
        ).first()
        
        if not progress:
            logger.info("Creating new progress record...")
            progress = TrackProgress(
                project_pk_id=project.pk_id,
                project_id=project.id
            )
            db.add(progress)
            db.flush()
            logger.info(f"Progress record created with id: {progress.id}")
        
        # FIXED MAPPING: Frontend page number → DB column name
        # This corrects the off-by-one issue where DB has page_4_rfp_generation
        page_field_mapping = {
            1: "page_1_requirement",        # RequirementForm
            2: "page_2_functional",         # FunctionalAnalysis
            3: "page_3_technical",          # TechnicalReview
            4: "page_5_tender_draft",       # TenderDrafting (skip page_4_rfp_generation)
            5: "page_6_authority_approval", # ApprovalGate
            6: "page_7_publish_rfp",        # PublishRFP
            7: "page_8_vendor_bidding",     # ReceiveBids
            8: "page_9_vendor_evaluation",  # VendorEvaluation
            9: "page_10_purchase_order",    # PurchaseOrder
            10: "page_10_contract_signing"  # ContractSigning (separate column for 100%)
        }
        
        page_field = page_field_mapping.get(request.page_number)
        
        if not page_field:
            logger.error(f"Invalid page number mapping: {request.page_number}")
            raise HTTPException(status_code=400, detail="Invalid page number")
        
        # Page name for logging
        page_name = PAGE_NAME_MAPPING.get(request.page_number, f"Page {request.page_number}")
        
        logger.info(f"Frontend Page {request.page_number} ({page_name}) → DB Column: {page_field}")
        logger.info(f"Updating field: {page_field} = {request.is_completed}")
        
        setattr(progress, page_field, request.is_completed)
        
        # Special case: Page 3 (TechnicalReview) also marks page_4_rfp_generation
        # because RFP generation happens as part of Technical Review in the frontend
        if request.page_number == 3 and request.is_completed:
            logger.info("Also marking page_4_rfp_generation = True (RFP generation is part of Technical Review)")
            setattr(progress, "page_4_rfp_generation", True)
        
        # Set completion timestamp (use the mapped column number, not frontend page number)
        # Extract the column number from the field name
        import re
        col_match = re.search(r'page_(\d+)_', page_field)
        if col_match:
            col_number = int(col_match.group(1))
            page_timestamp_field = f"page_{col_number}_completed_at"
            
            if request.is_completed:
                setattr(progress, page_timestamp_field, datetime.utcnow())
                logger.info(f"Setting completion timestamp: {page_timestamp_field}")
            else:
                setattr(progress, page_timestamp_field, None)
        
        # Recalculate overall progress
        progress.overall_progress = calculate_overall_progress(progress)
        progress.current_page = get_current_page(progress)
        
        # Update status
        if progress.overall_progress == 100:
            progress.status = "completed"
        elif progress.overall_progress > 0:
            progress.status = "in_progress"
        else:
            progress.status = "in_progress"
        
        logger.info(f"Overall progress: {progress.overall_progress}%")
        logger.info(f"Current page: {progress.current_page}")
        logger.info(f"Status: {progress.status}")
        
        db.commit()
        db.refresh(progress)
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /requirements/progress/update - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "message": "Progress updated successfully",
            "project_id": request.project_id,
            "page_updated": request.page_number,
            "page_name": page_name,
            "db_column_updated": page_field,
            "is_completed": request.is_completed,
            "current_page": progress.current_page,
            "overall_progress": progress.overall_progress,
            "status": progress.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()



@router.get("/progress/{project_id}")
def get_progress(project_id: str):
    """
    Get the progress details for a specific project.
    Returns completion status for all 10 pages/stages.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/progress/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get progress record
        progress = db.query(TrackProgress).filter(
            TrackProgress.project_id == project_id
        ).first()
        
        if not progress:
            logger.info("No progress record found, returning default values")
            return {
                "project_id": project_id,
                "project_title": project.title,
                "current_page": 1,
                "overall_progress": 0.0,
                "status": "not_started",
                "pages": [
                    {"page": i, "name": WORKFLOW_PAGES[i]["label"], "completed": False, "completed_at": None}
                    for i in range(1, 11)
                ]
            }
        
        # Build detailed response
        pages_detail = []
        for i in range(1, 11):
            page_info = WORKFLOW_PAGES[i]
            field_name = page_info["field"]
            completed = getattr(progress, field_name)
            completed_at = getattr(progress, f"page_{i}_completed_at")
            
            pages_detail.append({
                "page": i,
                "name": page_info["label"],
                "completed": completed,
                "completed_at": completed_at.isoformat() if completed_at else None
            })
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /requirements/progress/{project_id} - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "project_id": project_id,
            "project_title": project.title,
            "current_page": progress.current_page,
            "overall_progress": progress.overall_progress,
            "status": progress.status,
            "pages": pages_detail,
            "created_at": progress.created_at.isoformat() if progress.created_at else None,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.get("/progress/list/all")
def get_all_progress():
    """
    Get progress for all projects.
    Returns a summary of progress for each project.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/progress/list/all")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get all projects with their progress
        projects = db.query(ProjectCredential).order_by(ProjectCredential.created_at.desc()).all()
        
        logger.info(f"Found {len(projects)} projects")
        
        result = []
        for project in projects:
            progress = db.query(TrackProgress).filter(
                TrackProgress.project_id == project.id
            ).first()
            
            if progress:
                # Handle current_page > 10 (completed workflows)
                current_page = progress.current_page
                if current_page > 10:
                    current_page_name = "Completed"
                else:
                    current_page_name = WORKFLOW_PAGES.get(current_page, {}).get("label", f"Page {current_page}")
                
                result.append({
                    "project_id": project.id,
                    "project_title": project.title,
                    "department": project.department,
                    "priority": project.priority,
                    "current_page": progress.current_page,
                    "current_page_name": current_page_name,
                    "overall_progress": progress.overall_progress,
                    "status": progress.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
                })
            else:
                result.append({
                    "project_id": project.id,
                    "project_title": project.title,
                    "department": project.department,
                    "priority": project.priority,
                    "current_page": 1,
                    "current_page_name": WORKFLOW_PAGES[1]["label"],
                    "overall_progress": 0.0,
                    "status": "not_started",
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": None
                })
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /requirements/progress/list/all - SUCCESS")
        logger.info(f"Returning {len(result)} progress records")
        logger.info("=" * 60)
        
        return {
            "total_projects": len(result),
            "projects": result
        }
    
    except Exception as e:
        logger.error(f"Error getting all progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.post("/progress/init/{project_id}")
def initialize_progress(project_id: str):
    """
    Initialize progress tracking for a project.
    Creates a new progress record with page 1 marked as completed.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: POST /requirements/progress/init/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if progress already exists
        existing = db.query(TrackProgress).filter(
            TrackProgress.project_id == project_id
        ).first()
        
        if existing:
            logger.info("Progress record already exists")
            return {
                "message": "Progress record already exists",
                "project_id": project_id,
                "current_page": existing.current_page,
                "overall_progress": existing.overall_progress
            }
        
        # Create new progress record with page 1 completed
        progress = TrackProgress(
            project_pk_id=project.pk_id,
            project_id=project.id,
            page_1_requirement=True,
            page_1_completed_at=datetime.utcnow(),
            current_page=2,
            overall_progress=10.0,
            status="in_progress"
        )
        
        db.add(progress)
        db.commit()
        db.refresh(progress)
        
        logger.info(f"Progress initialized for project: {project_id}")
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /requirements/progress/init - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "message": "Progress initialized successfully",
            "project_id": project_id,
            "current_page": progress.current_page,
            "overall_progress": progress.overall_progress,
            "status": progress.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing progress: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.get("/progress/summary")
def get_progress_summary():
    """
    Get a summary of all projects' progress.
    Returns counts by status and overall statistics.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/progress/summary")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get all progress records
        all_progress = db.query(TrackProgress).all()
        total_projects = db.query(ProjectCredential).count()
        
        # Calculate statistics
        completed = sum(1 for p in all_progress if p.status == "completed")
        in_progress = sum(1 for p in all_progress if p.status == "in_progress")
        on_hold = sum(1 for p in all_progress if p.status == "on_hold")
        not_started = total_projects - len(all_progress)
        
        # Average progress
        avg_progress = sum(p.overall_progress for p in all_progress) / len(all_progress) if all_progress else 0
        
        # Projects by current page
        by_page = {}
        for i in range(1, 11):
            count = sum(1 for p in all_progress if p.current_page == i)
            by_page[WORKFLOW_PAGES[i]["label"]] = count
        
        # Add count for completed projects (page 11)
        completed_count = sum(1 for p in all_progress if p.current_page > 10)
        if completed_count > 0:
            by_page["Completed"] = completed_count
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /requirements/progress/summary - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "total_projects": total_projects,
            "with_progress_tracking": len(all_progress),
            "status_counts": {
                "completed": completed,
                "in_progress": in_progress,
                "on_hold": on_hold,
                "not_started": not_started
            },
            "average_progress": round(avg_progress, 2),
            "projects_by_stage": by_page
        }
    
    except Exception as e:
        logger.error(f"Error getting progress summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== PROJECT DETAILS API ====================

@router.get("/project/{project_id}")
def get_project_details(project_id: str):
    """
    Get full project details by project_id.
    Returns project credentials and progress information.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/project/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get progress record
        progress = db.query(TrackProgress).filter(
            TrackProgress.project_id == project_id
        ).first()
        
        # Build response
        response_data = {
            "project_id": project.id,
            "pk_id": project.pk_id,
            "title": project.title,
            "department": project.department,
            "category": project.category,
            "priority": project.priority,
            "estimated_amount": project.estimated_amount,
            "business_justification": project.business_justification,
            "submitted_by": project.submitted_by,
            "technical_specification": project.technical_specification,
            "expected_timeline": project.expected_timeline,
            "email": project.email,
            "phone_number": project.phone_number,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            # Progress info
            "current_page": progress.current_page if progress else 1,
            "overall_progress": progress.overall_progress if progress else 0.0,
            "status": progress.status if progress else "not_started"
        }
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /requirements/project/{project_id} - SUCCESS")
        logger.info("=" * 60)
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== ORIGINAL REQUIREMENT APIs ====================

@router.post("/")
async def create_requirement(
    title: str = Form(...),
    department: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    expected_timeline: str = Form(None),
    estimated_amount: str = Form(...),
    business_justification: str = Form(...),
    submitted_by: str = Form(...),

    technical_specification: str = Form(None),
    email: str = Form(None),
    phone_number: str = Form(None),

    files: list[UploadFile] = File(None)
):
    logger.info("=" * 60)
    logger.info("API CALLED: POST /requirements/")
    logger.info(f"Creating new requirement: {title}")
    logger.info("=" * 60)
    
    db = SessionLocal()

    try:
        # ==================== AMOUNT PARSING ====================
        parsed_amount = parse_estimated_amount(estimated_amount)
        logger.info(f"Parsed amount: {parsed_amount}")

        # ==================== DB INSERT (STEP 1) ====================
        project = ProjectCredential(
            title=title,
            department=department,
            category=category,
            priority=priority,
            estimated_amount=parsed_amount,
            expected_timeline=expected_timeline,
            business_justification=business_justification,
            submitted_by=submitted_by,
            technical_specification=technical_specification,
            email=email,
            phone_number=phone_number
        )

        db.add(project)
        db.flush()  # pk_id generated here
        logger.info(f"Project created with pk_id: {project.pk_id}")

        # ==================== BUSINESS ID ====================
        project.id = build_project_id(project.pk_id)
        logger.info(f"Generated project id: {project.id}")

        # ==================== FILE HANDLING ====================
        saved_files = []
        
        if files:
            logger.info(f"Processing {len(files)} files...")
            for idx, file in enumerate(files):
                if file.filename == "" or file.filename is None:
                    continue
                    
                if file.content_type not in [
                    "application/pdf",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ]:
                    raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")

                content = await file.read()

                if len(content) > 10 * 1024 * 1024:
                    raise HTTPException(status_code=400, detail=f"File size exceeds 10MB: {file.filename}")

                # Generate file name: ProjectID_a.pdf, ProjectID_b.docx, etc.
                file_label = get_file_label(idx)
                file_ext = get_file_extension(file.filename)
                new_filename = f"{project.id}_{file_label}{file_ext}"
                
                file_path = os.path.join(UPLOAD_DIR, new_filename)

                with open(file_path, "wb") as f:
                    f.write(content)

                saved_files.append({
                    "original_name": file.filename,
                    "saved_as": new_filename,
                    "label": file_label,
                    "size_kb": round(len(content) / 1024, 2)
                })
                logger.info(f"  File saved: {new_filename}")

                # ==================== FAISS VECTOR ====================
                # Extract text and create embedding
                extracted_text = extract_text(content, file_ext)
                vector = get_embedding(extracted_text)
                faiss_index.add(vector)
                
                # Get FAISS index position
                faiss_idx = faiss_index.ntotal - 1
                
                # Store metadata for this vector
                faiss_metadata.append({
                    "project_id": project.id,
                    "filename": new_filename,
                    "label": file_label,
                    "original_name": file.filename,
                    "text_preview": extracted_text[:500] if extracted_text else ""
                })
                
                # ==================== SAVE TO DATABASE ====================
                uploaded_file = UploadedFile(
                    project_pk_id=project.pk_id,
                    project_id=project.id,
                    label=file_label,
                    original_filename=file.filename,
                    saved_filename=new_filename,
                    file_extension=file_ext,
                    file_size_kb=round(len(content) / 1024, 2),
                    content_type=file.content_type,
                    faiss_index_id=faiss_idx,
                    text_extracted=extracted_text[:5000] if extracted_text else None  # Store first 5000 chars
                )
                db.add(uploaded_file)

        save_faiss()

        # ==================== INITIALIZE PROGRESS ====================
        logger.info("Initializing progress tracking...")
        progress = TrackProgress(
            project_pk_id=project.pk_id,
            project_id=project.id,
            page_1_requirement=True,
            page_1_completed_at=datetime.utcnow(),
            current_page=2,
            overall_progress=10.0,
            status="in_progress"
        )
        db.add(progress)
        logger.info("Progress tracking initialized with page 1 completed")

        # ==================== FINAL COMMIT ====================
        db.commit()
        logger.info("Transaction committed successfully")

        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /requirements/ - SUCCESS")
        logger.info("=" * 60)

        return {
            "message": "Requirement created successfully",
            "project_id": project.id,
            "estimated_amount_rupees": parsed_amount,
            "files_uploaded": len(saved_files),
            "files": saved_files,
            "progress": {
                "current_page": 2,
                "overall_progress": 10.0,
                "status": "in_progress"
            }
        }

    except IntegrityError:
        db.rollback()
        logger.error("Duplicate requirement detected")
        raise HTTPException(
            status_code=409,
            detail="Duplicate requirement detected"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating requirement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

    finally:
        db.close()


@router.get("/files")
def list_uploaded_files(project_id: str | None = None):
    """
    List uploaded files.
    - If project_id is provided -> only files for that project
    - Else -> all uploaded files
    """
    logger.info(f"API CALLED: GET /requirements/files (project_id: {project_id})")

    if not os.path.exists(UPLOAD_DIR):
        return {"files": []}

    files_info = []

    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.isfile(file_path):
            continue

        # Extract project_id from filename (format: ProjectID_label.ext)
        parts = filename.rsplit("_", 1)
        if len(parts) != 2:
            continue
            
        file_project_id = parts[0]
        label_with_ext = parts[1]
        label = os.path.splitext(label_with_ext)[0]

        # Filter by project_id if provided
        if project_id and file_project_id != project_id:
            continue

        stat = os.stat(file_path)

        files_info.append({
            "file_name": filename,
            "project_id": file_project_id,
            "label": label,
            "size_kb": round(stat.st_size / 1024, 2),
            "uploaded_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "download_url": f"/requirements/files/download/{filename}"
        })

    # Sort by label (a, b, c...)
    files_info.sort(key=lambda x: (x["project_id"], x["label"]))

    return {
        "total_files": len(files_info),
        "files": files_info
    }


@router.get("/files/download/{filename}")
def download_file(filename: str):
    """
    Download a specific uploaded file
    """
    logger.info(f"API CALLED: GET /requirements/files/download/{filename}")

    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@router.get("/search")
def search_documents(query: str, top_k: int = 5):
    """
    Search documents using semantic similarity
    
    Args:
        query: Search query text
        top_k: Number of results to return (default 5)
    """
    logger.info(f"API CALLED: GET /requirements/search (query: {query})")
    
    if faiss_index.ntotal == 0:
        return {"message": "No documents indexed yet", "results": []}
    
    # Generate embedding for query
    query_vector = get_embedding(query)
    
    # Search FAISS
    k = min(top_k, faiss_index.ntotal)
    distances, indices = faiss_index.search(query_vector, k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(faiss_metadata):
            meta = faiss_metadata[idx]
            results.append({
                "rank": i + 1,
                "project_id": meta["project_id"],
                "filename": meta["filename"],
                "original_name": meta["original_name"],
                "label": meta["label"],
                "text_preview": meta["text_preview"],
                "similarity_score": round(float(1 / (1 + distances[0][i])), 4),
                "download_url": f"/requirements/files/download/{meta['filename']}"
            })
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }


@router.get("/extract/{project_id}")
def extract_document_text(project_id: str, label: str = None):
    """
    Extract text from uploaded documents for a project
    
    Args:
        project_id: Project ID
        label: Optional file label (a, b, c...). If not provided, extracts from all files.
    """
    logger.info(f"API CALLED: GET /requirements/extract/{project_id} (label: {label})")
    
    if not os.path.exists(UPLOAD_DIR):
        raise HTTPException(status_code=404, detail="No files found")
    
    extracted_data = []
    
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.isfile(file_path):
            continue
        
        # Parse filename
        parts = filename.rsplit("_", 1)
        if len(parts) != 2:
            continue
            
        file_project_id = parts[0]
        label_with_ext = parts[1]
        file_label = os.path.splitext(label_with_ext)[0]
        file_ext = os.path.splitext(label_with_ext)[1].lower()
        
        # Filter by project_id
        if file_project_id != project_id:
            continue
            
        # Filter by label if provided
        if label and file_label != label:
            continue
        
        # Read and extract text
        with open(file_path, "rb") as f:
            content = f.read()
        
        text = extract_text(content, file_ext)
        
        extracted_data.append({
            "filename": filename,
            "label": file_label,
            "text": text,
            "word_count": len(text.split()) if text else 0
        })
    
    if not extracted_data:
        raise HTTPException(status_code=404, detail="No files found for this project")
    
    # Sort by label
    extracted_data.sort(key=lambda x: x["label"])
    
    return {
        "project_id": project_id,
        "total_files": len(extracted_data),
        "extracted": extracted_data
    }


@router.get("/db/files")
def get_files_from_db(project_id: str = None):
    """
    Get uploaded files info from database
    
    Args:
        project_id: Optional project ID to filter
    """
    logger.info(f"API CALLED: GET /requirements/db/files (project_id: {project_id})")
    db = SessionLocal()
    
    try:
        query = db.query(UploadedFile)
        
        if project_id:
            query = query.filter(UploadedFile.project_id == project_id)
        
        files = query.order_by(UploadedFile.project_id, UploadedFile.label).all()
        
        return {
            "total_files": len(files),
            "files": [
                {
                    "id": f.id,
                    "project_id": f.project_id,
                    "label": f.label,
                    "original_filename": f.original_filename,
                    "saved_filename": f.saved_filename,
                    "file_extension": f.file_extension,
                    "file_size_kb": f.file_size_kb,
                    "faiss_index_id": f.faiss_index_id,
                    "has_text": bool(f.text_extracted),
                    "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
                    "download_url": f"/requirements/files/download/{f.saved_filename}"
                }
                for f in files
            ]
        }
    finally:
        db.close()


@router.get("/db/files/{file_id}")
def get_file_details(file_id: int):
    """
    Get detailed info for a specific file including extracted text
    """
    logger.info(f"API CALLED: GET /requirements/db/files/{file_id}")
    db = SessionLocal()
    
    try:
        file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "id": file.id,
            "project_id": file.project_id,
            "project_pk_id": file.project_pk_id,
            "label": file.label,
            "original_filename": file.original_filename,
            "saved_filename": file.saved_filename,
            "file_extension": file.file_extension,
            "file_size_kb": file.file_size_kb,
            "content_type": file.content_type,
            "faiss_index_id": file.faiss_index_id,
            "text_extracted": file.text_extracted,
            "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else None,
            "download_url": f"/requirements/files/download/{file.saved_filename}"
        }
    finally:
        db.close()


# ==================== REJECTED PROJECTS APIs ====================

@router.post("/rejected/{project_id}")
def add_rejected_project(project_id: str):
    """
    Add a project_id to the rejected_projects table.
    Called when a project is rejected at ApprovalGate (Page 5).
    """
    logger.info("=" * 60)
    logger.info("API CALLED: POST /requirements/rejected/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Check if already rejected
        existing = db.query(RejectedProject).filter(
            RejectedProject.project_id == project_id
        ).first()
        
        if existing:
            logger.info(f"Project {project_id} is already in rejected list")
            return {
                "message": "Project already marked as rejected",
                "project_id": project_id,
                "rejected_at": existing.rejected_at.isoformat()
            }
        
        # Add to rejected table
        rejected = RejectedProject(project_id=project_id)
        db.add(rejected)
        db.commit()
        db.refresh(rejected)
        
        logger.info(f"Project {project_id} added to rejected list")
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /requirements/rejected/{project_id} - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "message": "Project marked as rejected",
            "project_id": project_id,
            "rejected_at": rejected.rejected_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error adding rejected project: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.get("/rejected/list")
def get_rejected_projects():
    """
    Get all rejected project IDs.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/rejected/list")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        rejected = db.query(RejectedProject).order_by(RejectedProject.rejected_at.desc()).all()
        
        logger.info(f"Found {len(rejected)} rejected projects")
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /requirements/rejected/list - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "total_rejected": len(rejected),
            "projects": [
                {
                    "project_id": r.project_id,
                    "rejected_at": r.rejected_at.isoformat()
                }
                for r in rejected
            ]
        }
    
    finally:
        db.close()
@router.post("/progress/remove/{project_id}")
def remove_progress(project_id: str):
    """
    Remove a project's progress record from track_progress table AND project_navigation table.
    Called when a project is rejected to clean up progress tracking.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: POST /requirements/progress/remove/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        deleted_progress = False
        deleted_navigation = False
        
        # 1. Find and delete the progress record from track_progress
        progress = db.query(TrackProgress).filter(
            TrackProgress.project_id == project_id
        ).first()
        
        if progress:
            db.delete(progress)
            deleted_progress = True
            logger.info(f"Progress record deleted from track_progress for project: {project_id}")
        else:
            logger.info(f"No progress record found in track_progress for project: {project_id}")
        
        # 2. Find and delete the navigation record from project_navigation
        navigation = db.query(ProjectNavigation).filter(
            ProjectNavigation.project_id == project_id
        ).first()
        
        if navigation:
            db.delete(navigation)
            deleted_navigation = True
            logger.info(f"Navigation record deleted from project_navigation for project: {project_id}")
        else:
            logger.info(f"No navigation record found in project_navigation for project: {project_id}")
        
        # Commit all deletions
        db.commit()
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /requirements/progress/remove/{project_id} - SUCCESS")
        logger.info("=" * 60)
        
        return {
            "message": "Records removed successfully",
            "project_id": project_id,
            "progress_deleted": deleted_progress,
            "navigation_deleted": deleted_navigation,
            "deleted": deleted_progress or deleted_navigation
        }
    
    except Exception as e:
        logger.error(f"Error removing progress: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== PROJECT NAVIGATION APIs ====================

class NavigationUpdate(BaseModel):
    """Request body for updating navigation"""
    current_stage: int
    current_page_component: str
    current_page_name: Optional[str] = None


@router.post("/navigation/{project_id}")
def update_navigation(project_id: str, nav_data: NavigationUpdate):
    """
    Update or create navigation state for a project.
    Called by each page component when completing a stage.
    
    Parameters:
    - project_id: The project ID (from URL path)
    - current_stage: The App.js case number (0-9)
    - current_page_component: Component name (e.g., "FunctionalAnalysis")
    - current_page_name: Human-readable name (optional)
    """
    logger.info("=" * 60)
    logger.info("API CALLED: POST /requirements/navigation/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info(f"Body - current_stage: {nav_data.current_stage}")
    logger.info(f"Body - current_page_component: {nav_data.current_page_component}")
    logger.info(f"Body - current_page_name: {nav_data.current_page_name}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Check if navigation record exists
        existing = db.query(ProjectNavigation).filter(
            ProjectNavigation.project_id == project_id
        ).first()
        
        # Get page name from mapping if not provided
        page_name = nav_data.current_page_name
        if not page_name and nav_data.current_stage in STAGE_COMPONENT_MAP:
            page_name = STAGE_COMPONENT_MAP[nav_data.current_stage]["name"]
        
        if existing:
            # Update existing record
            existing.current_stage = nav_data.current_stage
            existing.current_page_component = nav_data.current_page_component
            existing.current_page_name = page_name
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            
            logger.info(f"Navigation UPDATED for project {project_id}")
            logger.info(f"  → Stage: {nav_data.current_stage}")
            logger.info(f"  → Component: {nav_data.current_page_component}")
            
            return {
                "message": "Navigation updated",
                "project_id": project_id,
                "current_stage": existing.current_stage,
                "current_page_component": existing.current_page_component,
                "current_page_name": existing.current_page_name,
                "updated_at": existing.updated_at.isoformat()
            }
        else:
            # Create new record
            new_nav = ProjectNavigation(
                project_id=project_id,
                current_stage=nav_data.current_stage,
                current_page_component=nav_data.current_page_component,
                current_page_name=page_name
            )
            db.add(new_nav)
            db.commit()
            db.refresh(new_nav)
            
            logger.info(f"Navigation CREATED for project {project_id}")
            logger.info(f"  → Stage: {nav_data.current_stage}")
            logger.info(f"  → Component: {nav_data.current_page_component}")
            
            return {
                "message": "Navigation created",
                "project_id": project_id,
                "current_stage": new_nav.current_stage,
                "current_page_component": new_nav.current_page_component,
                "current_page_name": new_nav.current_page_name,
                "created_at": new_nav.created_at.isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error updating navigation: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.get("/navigation/{project_id}")
def get_navigation(project_id: str):
    """
    Get the current navigation state for a project.
    Used by Dashboard to navigate to the correct page.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/navigation/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        nav = db.query(ProjectNavigation).filter(
            ProjectNavigation.project_id == project_id
        ).first()
        
        if not nav:
            logger.info(f"No navigation found for project {project_id}, returning default (stage 1)")
            return {
                "project_id": project_id,
                "current_stage": 1,
                "current_page_component": "FunctionalAnalysis",
                "current_page_name": "Functional Analysis",
                "found": False
            }
        
        logger.info(f"Navigation found: Stage {nav.current_stage} - {nav.current_page_component}")
        
        return {
            "project_id": project_id,
            "current_stage": nav.current_stage,
            "current_page_component": nav.current_page_component,
            "current_page_name": nav.current_page_name,
            "updated_at": nav.updated_at.isoformat() if nav.updated_at else None,
            "found": True
        }
    
    finally:
        db.close()


@router.get("/navigation/list/all")
def get_all_navigation():
    """
    Get navigation state for all projects.
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /requirements/navigation/list/all")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        navigations = db.query(ProjectNavigation).order_by(
            ProjectNavigation.updated_at.desc()
        ).all()
        
        logger.info(f"Found {len(navigations)} navigation records")
        
        return {
            "total": len(navigations),
            "projects": [
                {
                    "project_id": nav.project_id,
                    "current_stage": nav.current_stage,
                    "current_page_component": nav.current_page_component,
                    "current_page_name": nav.current_page_name,
                    "updated_at": nav.updated_at.isoformat() if nav.updated_at else None
                }
                for nav in navigations
            ]
        }
    
    finally:
        db.close()


@router.delete("/navigation/{project_id}")
def delete_navigation(project_id: str):
    """
    Delete navigation record for a project (used when project is rejected/deleted).
    """
    logger.info("=" * 60)
    logger.info("API CALLED: DELETE /requirements/navigation/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        nav = db.query(ProjectNavigation).filter(
            ProjectNavigation.project_id == project_id
        ).first()
        
        if not nav:
            return {
                "message": "No navigation record found",
                "project_id": project_id,
                "deleted": False
            }
        
        db.delete(nav)
        db.commit()
        
        logger.info(f"Navigation deleted for project {project_id}")
        
        return {
            "message": "Navigation deleted",
            "project_id": project_id,
            "deleted": True
        }
    
    except Exception as e:
        logger.error(f"Error deleting navigation: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


logger.info("=" * 60)
logger.info("REQUIREMENT MODULE LOADED SUCCESSFULLY")
logger.info("=" * 60)
