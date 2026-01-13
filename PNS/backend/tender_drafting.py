from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal, ProjectCredential, TenderDraft
from datetime import datetime
import re

router = APIRouter(prefix="/tender", tags=["Tender Drafting"])


# ==================== PYDANTIC MODELS ====================

class TenderDraftRequest(BaseModel):
    project_id: str
    select_rfp_template: str
    bid_validity_period: str  # e.g., "60 days", "90 days"
    submission_deadline: str  # e.g., "01/15/2025" (mm/dd/yyyy)
    emd_amount: str  # e.g., "5 Lakhs", "50000", "2.5 CR"
    eligibility_criteria: str


# ==================== HELPER FUNCTIONS ====================

def parse_bid_validity(value: str) -> int:
    """
    Extract number from bid validity period
    Examples: "60 days" -> 60, "90 days" -> 90, "120" -> 120
    """
    if not value:
        raise HTTPException(status_code=400, detail="Bid validity period is required")
    
    # Find all numbers in the string
    match = re.search(r'(\d+)', value)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid bid validity period format. Expected format: '60 days' or '90'")
    
    return int(match.group(1))


def parse_submission_deadline(value: str) -> datetime:
    """
    Parse date from mm/dd/yyyy format
    Examples: "01/15/2025" -> datetime(2025, 1, 15)
    """
    if not value:
        raise HTTPException(status_code=400, detail="Submission deadline is required")
    
    try:
        # Try mm/dd/yyyy format
        return datetime.strptime(value.strip(), "%m/%d/%Y")
    except ValueError:
        pass
    
    try:
        # Try dd/mm/yyyy format as fallback
        return datetime.strptime(value.strip(), "%d/%m/%Y")
    except ValueError:
        pass
    
    try:
        # Try yyyy-mm-dd format as fallback
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Expected format: mm/dd/yyyy (e.g., 01/15/2025)"
        )


def parse_emd_amount(value: str) -> float:
    """
    Extract number from EMD amount
    Examples: 
    - "5 Lakhs" -> 500000
    - "50000" -> 50000
    - "2.5 CR" -> 25000000
    - "1,00,000" -> 100000
    - "₹ 5,00,000" -> 500000
    """
    if not value:
        raise HTTPException(status_code=400, detail="EMD amount is required")
    
    value = value.lower().strip()
    
    # Remove currency symbols and commas
    value_clean = re.sub(r'[₹$,\s]', '', value)
    
    # Find the number (including decimals)
    match = re.search(r'(\d+\.?\d*)', value_clean)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid EMD amount format")
    
    number = float(match.group(1))
    
    # Check for multipliers
    if any(k in value for k in ["cr", "crore", "caror"]):
        return number * 10000000  # 1 crore = 10 million
    elif any(k in value for k in ["lakh", "lac", "lacs", "lakhs"]):
        return number * 100000  # 1 lakh = 100,000
    elif any(k in value for k in ["k", "thousand"]):
        return number * 1000
    
    return number


# ==================== POST API ====================

@router.post("/submit")
def submit_tender_draft(request: TenderDraftRequest):
    """
    Submit tender draft details
    
    Accepts JSON body:
    {
        "project_id": "PSB-PROC-2025-1-12-1",
        "select_rfp_template": "Standard IT Procurement",
        "bid_validity_period": "90 days",
        "submission_deadline": "01/15/2025",
        "emd_amount": "5 Lakhs",
        "eligibility_criteria": "Minimum 3 years experience..."
    }
    """
    db = SessionLocal()
    
    try:
        # Find the project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Parse fields
        bid_validity_days = parse_bid_validity(request.bid_validity_period)
        submission_date = parse_submission_deadline(request.submission_deadline)
        emd_number = parse_emd_amount(request.emd_amount)
        
        # Check if tender draft already exists
        existing = db.query(TenderDraft).filter(
            TenderDraft.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            # Update existing
            existing.rfp_template = request.select_rfp_template
            existing.bid_validity_period = bid_validity_days
            existing.submission_deadline = submission_date
            existing.emd_amount = emd_number
            existing.eligibility_criteria = request.eligibility_criteria
            
            db.commit()
            db.refresh(existing)
            
            return {
                "message": "Tender draft updated successfully",
                "tender_id": existing.id,
                "project_id": project.id,
                "project_title": project.title,
                "parsed_values": {
                    "rfp_template": existing.rfp_template,
                    "bid_validity_period_days": existing.bid_validity_period,
                    "submission_deadline": existing.submission_deadline.strftime("%Y-%m-%d"),
                    "emd_amount": existing.emd_amount
                },
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
                "updated_at": existing.updated_at.isoformat() if existing.updated_at else None
            }
        
        else:
            # Create new
            tender_draft = TenderDraft(
                project_pk_id=project.pk_id,
                project_id=project.id,
                rfp_template=request.select_rfp_template,
                bid_validity_period=bid_validity_days,
                submission_deadline=submission_date,
                emd_amount=emd_number,
                eligibility_criteria=request.eligibility_criteria
            )
            
            db.add(tender_draft)
            db.commit()
            db.refresh(tender_draft)
            
            return {
                "message": "Tender draft submitted successfully",
                "tender_id": tender_draft.id,
                "project_id": project.id,
                "project_title": project.title,
                "parsed_values": {
                    "rfp_template": tender_draft.rfp_template,
                    "bid_validity_period_days": tender_draft.bid_validity_period,
                    "submission_deadline": tender_draft.submission_deadline.strftime("%Y-%m-%d"),
                    "emd_amount": tender_draft.emd_amount
                },
                "created_at": tender_draft.created_at.isoformat() if tender_draft.created_at else None
            }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== GET APIs ====================

@router.get("/list")
def get_all_tender_drafts():
    """Get all tender drafts"""
    db = SessionLocal()
    
    try:
        drafts = db.query(TenderDraft).order_by(TenderDraft.created_at.desc()).all()
        
        result = []
        for draft in drafts:
            project = db.query(ProjectCredential).filter(
                ProjectCredential.pk_id == draft.project_pk_id
            ).first()
            
            result.append({
                "tender_id": draft.id,
                "project_id": draft.project_id,
                "project_title": project.title if project else None,
                "department": project.department if project else None,
                "rfp_template": draft.rfp_template,
                "bid_validity_period_days": draft.bid_validity_period,
                "submission_deadline": draft.submission_deadline.strftime("%Y-%m-%d") if draft.submission_deadline else None,
                "emd_amount": draft.emd_amount,
                "eligibility_criteria": draft.eligibility_criteria[:100] + "..." if len(draft.eligibility_criteria) > 100 else draft.eligibility_criteria,
                "authority_decision": draft.authority_decision,
                "created_at": draft.created_at.isoformat() if draft.created_at else None
            })
        
        return {
            "total_drafts": len(result),
            "drafts": result
        }
    
    finally:
        db.close()


@router.get("/{project_id}")
def get_tender_draft(project_id: str):
    """Get tender draft for a specific project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        draft = db.query(TenderDraft).filter(
            TenderDraft.project_pk_id == project.pk_id
        ).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Tender draft not found for this project")
        
        return {
            "tender_id": draft.id,
            "project_id": draft.project_id,
            "project_title": project.title,
            "department": project.department,
            "rfp_template": draft.rfp_template,
            "bid_validity_period_days": draft.bid_validity_period,
            "submission_deadline": draft.submission_deadline.strftime("%Y-%m-%d") if draft.submission_deadline else None,
            "emd_amount": draft.emd_amount,
            "eligibility_criteria": draft.eligibility_criteria,
            "authority_decision": draft.authority_decision,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
            "updated_at": draft.updated_at.isoformat() if draft.updated_at else None
        }
    
    finally:
        db.close()


# ==================== AUTHORITY DECISION ====================

class AuthorityDecisionRequest(BaseModel):
    project_id: str
    truth_value: int  # 0 or 1


@router.post("/authority-decision")
def submit_authority_decision(request: AuthorityDecisionRequest):
    """
    Submit authority decision for a tender
    
    Accepts JSON body:
    {
        "project_id": "PSB-PROC-2025-1-12-1",
        "truth_value": 1
    }
    
    truth_value: 0 = Rejected, 1 = Approved
    """
    db = SessionLocal()
    
    try:
        # Validate truth_value
        if request.truth_value not in [0, 1]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid truth_value. Must be 0 (Rejected) or 1 (Approved)"
            )
        
        # Find the project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Find the tender draft
        draft = db.query(TenderDraft).filter(
            TenderDraft.project_pk_id == project.pk_id
        ).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Tender draft not found for this project")
        
        # Update authority_decision
        draft.authority_decision = request.truth_value
        
        db.commit()
        db.refresh(draft)
        
        decision_text = "Approved" if request.truth_value == 1 else "Rejected"
        
        return {
            "message": f"Authority decision updated successfully",
            "tender_id": draft.id,
            "project_id": project.id,
            "project_title": project.title,
            "authority_decision": draft.authority_decision,
            "decision_status": decision_text,
            "updated_at": draft.updated_at.isoformat() if draft.updated_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()
