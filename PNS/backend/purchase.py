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

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/purchase", tags=["Purchase Order"])

# Directories for storing generated documents
PO_STORAGE_DIR = "generated_purchase_orders"
MSA_STORAGE_DIR = "generated_agreements/master_service_agreement"
SLA_STORAGE_DIR = "generated_agreements/service_level_agreement"
NDA_STORAGE_DIR = "generated_agreements/non_disclosure_agreement"
DPA_STORAGE_DIR = "generated_agreements/data_processing_agreement"
ANNEXURES_STORAGE_DIR = "generated_agreements/annexures_schedules"

# Create directories
for directory in [PO_STORAGE_DIR, MSA_STORAGE_DIR, SLA_STORAGE_DIR, NDA_STORAGE_DIR, DPA_STORAGE_DIR, ANNEXURES_STORAGE_DIR]:
    os.makedirs(directory, exist_ok=True)

# Agreement types
AGREEMENT_TYPES = {
    "MSA": {"name": "Master Service Agreement", "dir": MSA_STORAGE_DIR},
    "SLA": {"name": "Service Level Agreement", "dir": SLA_STORAGE_DIR},
    "NDA": {"name": "Non Disclosure Agreement", "dir": NDA_STORAGE_DIR},
    "DPA": {"name": "Data Processing Agreement", "dir": DPA_STORAGE_DIR},
    "ANNEXURES": {"name": "Annexures & Schedules", "dir": ANNEXURES_STORAGE_DIR}
}


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

VALID_WARRANTY_PERIODS = ["1 year", "2 year"]


def validate_payment_terms(value: str) -> str:
    if value not in VALID_PAYMENT_TERMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment terms: {value}. Valid options: {', '.join(VALID_PAYMENT_TERMS)}"
        )
    return value


def validate_warranty_period(value: str) -> str:
    if value not in VALID_WARRANTY_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid warranty period: {value}. Valid options: {', '.join(VALID_WARRANTY_PERIODS)}"
        )
    return value


def generate_purchase_order_number(project_id: str) -> str:
    random_suffix = random.randint(1000, 9999)
    return f"PO-{project_id}-{random_suffix}"


# ==================== GET RFP ID API ====================

@router.get("/rfp/{project_id}")
def get_rfp_by_project_id(project_id: str):
    """Get RFP ID from generated_rfps table using project_id"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get the latest RFP for the project
        rfp = db.query(GeneratedRFP).filter(
            GeneratedRFP.project_pk_id == project.pk_id
        ).order_by(GeneratedRFP.version.desc()).first()
        
        if not rfp:
            raise HTTPException(status_code=404, detail="No RFP found for this project")
        
        return {
            "rfp_id": rfp.id,
            "project_id": project.id,
            "project_title": project.title,
            "version": rfp.version,
            "filename": rfp.rfp_filename,
            "filepath": rfp.rfp_filepath,
            "created_at": rfp.created_at.isoformat() if rfp.created_at else None
        }
    
    finally:
        db.close()


# ==================== HELPER FUNCTIONS ====================

def get_all_project_data(db, project_id: str) -> Dict[str, Any]:
    """Gather all project data from all tables"""
    
    project = db.query(ProjectCredential).filter(
        ProjectCredential.id == project_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all related data
    functional_assessment = db.query(FunctionalAssessment).filter(
        FunctionalAssessment.project_pk_id == project.pk_id
    ).first()
    
    technical_review = db.query(TechnicalCommitteeReview).filter(
        TechnicalCommitteeReview.project_pk_id == project.pk_id
    ).first()
    
    tender_draft = db.query(TenderDraft).filter(
        TenderDraft.project_pk_id == project.pk_id
    ).first()
    
    publish_rfp = db.query(PublishRFP).filter(
        PublishRFP.project_pk_id == project.pk_id
    ).first()
    
    vendor_bid = db.query(VendorBid).filter(
        VendorBid.project_pk_id == project.pk_id,
        VendorBid.rank == 1
    ).first()
    
    generated_rfp = db.query(GeneratedRFP).filter(
        GeneratedRFP.project_pk_id == project.pk_id
    ).order_by(GeneratedRFP.version.desc()).first()
    
    purchase_data = db.query(PurchaseData).filter(
        PurchaseData.project_pk_id == project.pk_id
    ).first()
    
    return {
        "project": project,
        "functional_assessment": functional_assessment,
        "technical_review": technical_review,
        "tender_draft": tender_draft,
        "publish_rfp": publish_rfp,
        "vendor_bid": vendor_bid,
        "generated_rfp": generated_rfp,
        "purchase_data": purchase_data
    }


def fetch_rfp_content(rfp_id: int) -> Optional[str]:
    """Fetch RFP content from the technical-review API"""
    try:
        response = requests.get(
            f"http://localhost:8003/technical-review/rfp/content/{rfp_id}",
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "")
    except Exception as e:
        print(f"Error fetching RFP content: {e}")
    return None


def generate_agreement_content(
    agreement_type: str,
    project_data: Dict[str, Any],
    purchase_info: PurchaseDataInfo,
    rfp_content: Optional[str] = None
) -> str:
    """Generate agreement content using Anthropic API"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not found in environment variables"
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    
    project = project_data["project"]
    vendor_bid = project_data.get("vendor_bid")
    technical_review = project_data.get("technical_review")
    functional_assessment = project_data.get("functional_assessment")
    tender_draft = project_data.get("tender_draft")
    
    # Build context
    context = f"""
PROJECT DETAILS:
- Project ID: {project.id}
- Project Title: {project.title}
- Department: {project.department}
- Category: {project.category}
- Estimated Amount: ₹{project.estimated_amount:,.2f}
- Business Justification: {project.business_justification}

PURCHASE ORDER DETAILS:
- PO Number: {purchase_info.purchase_order_number}
- Vendor: {purchase_info.vendor}
- PO Value: ₹{purchase_info.po_value:,.2f}
- Delivery Period: {purchase_info.delivery_period}
- Payment Terms: {purchase_info.payment_terms}
- Warranty Period: {purchase_info.warranty_period}
- Penalty Clause: {purchase_info.penalty_clause}

BANK DETAILS:
- Bank Name: Punjab & Sind Bank
- Head Office: 21, Rajendra Place, New Delhi - 110008
- CIN: L65110PB1908GOI002217
"""
    
    if technical_review:
        context += f"""
TECHNICAL REVIEW:
- Architecture Review: {technical_review.architecture_review[:500] if technical_review.architecture_review else 'N/A'}
- Security Assessment: {technical_review.security_assessment[:500] if technical_review.security_assessment else 'N/A'}
"""
    
    if rfp_content:
        context += f"""
RFP CONTENT SUMMARY:
{rfp_content[:2000]}
"""
    
    # Agreement-specific prompts
    prompts = {
        "MSA": f"""Generate a comprehensive MASTER SERVICE AGREEMENT (MSA) for Punjab & Sind Bank.

{context}

Create a formal MSA document including:
1. DEFINITIONS AND INTERPRETATION
2. SCOPE OF SERVICES
3. TERM AND TERMINATION
4. SERVICE FEES AND PAYMENT
5. INTELLECTUAL PROPERTY RIGHTS
6. CONFIDENTIALITY
7. DATA PROTECTION AND SECURITY
8. WARRANTIES AND REPRESENTATIONS
9. LIMITATION OF LIABILITY
10. INDEMNIFICATION
11. FORCE MAJEURE
12. DISPUTE RESOLUTION
13. GOVERNING LAW
14. GENERAL PROVISIONS
15. SIGNATURES

Format professionally with numbered clauses and sub-clauses. Use plain text without markdown.""",

        "SLA": f"""Generate a comprehensive SERVICE LEVEL AGREEMENT (SLA) for Punjab & Sind Bank.

{context}

Create a formal SLA document including:
1. SERVICE DESCRIPTION
2. SERVICE AVAILABILITY (99.9% uptime)
3. PERFORMANCE METRICS
4. RESPONSE TIME REQUIREMENTS
5. INCIDENT MANAGEMENT
6. ESCALATION PROCEDURES
7. MAINTENANCE WINDOWS
8. SERVICE CREDITS
9. REPORTING REQUIREMENTS
10. REVIEW AND MONITORING
11. PENALTY CALCULATIONS
12. EXCLUSIONS
13. SIGNATURES

Include specific metrics, timelines, and penalty calculations. Use plain text without markdown.""",

        "NDA": f"""Generate a comprehensive NON-DISCLOSURE AGREEMENT (NDA) for Punjab & Sind Bank.

{context}

Create a formal NDA document including:
1. DEFINITIONS
2. CONFIDENTIAL INFORMATION
3. OBLIGATIONS OF RECEIVING PARTY
4. EXCLUSIONS FROM CONFIDENTIALITY
5. TERM OF CONFIDENTIALITY (5 years)
6. RETURN OF CONFIDENTIAL INFORMATION
7. NO LICENSE GRANTED
8. NO WARRANTY
9. REMEDIES
10. GOVERNING LAW
11. ENTIRE AGREEMENT
12. SIGNATURES

Emphasize banking data protection requirements. Use plain text without markdown.""",

        "DPA": f"""Generate a comprehensive DATA PROCESSING AGREEMENT (DPA) for Punjab & Sind Bank.

{context}

Create a formal DPA document including:
1. DEFINITIONS
2. SCOPE AND PURPOSE OF PROCESSING
3. DATA CONTROLLER AND PROCESSOR ROLES
4. TYPES OF PERSONAL DATA
5. PROCESSING INSTRUCTIONS
6. SECURITY MEASURES
7. SUB-PROCESSORS
8. DATA SUBJECT RIGHTS
9. DATA BREACH NOTIFICATION
10. DATA TRANSFER
11. AUDIT RIGHTS
12. DELETION AND RETURN OF DATA
13. RBI COMPLIANCE REQUIREMENTS
14. LIABILITY
15. SIGNATURES

Include RBI data localization and DPDP Act compliance. Use plain text without markdown.""",

        "ANNEXURES": f"""Generate ANNEXURES AND SCHEDULES for Punjab & Sind Bank service agreement.

{context}

Create comprehensive annexures including:

SCHEDULE A - SCOPE OF WORK
- Detailed deliverables
- Technical specifications
- Implementation timeline

SCHEDULE B - PRICING AND PAYMENT
- Price breakdown
- Payment milestones
- Invoice format

SCHEDULE C - PROJECT TEAM
- Key personnel
- Roles and responsibilities
- Contact information

SCHEDULE D - TECHNICAL REQUIREMENTS
- System requirements
- Integration specifications
- Security requirements

SCHEDULE E - ACCEPTANCE CRITERIA
- Testing procedures
- Acceptance criteria
- Sign-off process

SCHEDULE F - CHANGE MANAGEMENT
- Change request process
- Impact assessment
- Approval workflow

SCHEDULE G - EXIT MANAGEMENT
- Transition plan
- Knowledge transfer
- Data handover

Use plain text without markdown. Include specific details from the project."""
    }
    
    prompt = prompts.get(agreement_type, "")
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text


def create_agreement_pdf(
    content: str,
    agreement_type: str,
    project_id: str,
    project_title: str,
    vendor_name: str,
    po_number: str
) -> tuple:
    """Create PDF for agreement document"""
    
    agreement_info = AGREEMENT_TYPES[agreement_type]
    filename = f"{agreement_type}_{project_id}.pdf"
    filepath = os.path.join(agreement_info["dir"], filename)
    
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
    content_lines = content.split('\n')
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
    
    doc.build(story)
    
    file_size_kb = os.path.getsize(filepath) / 1024
    
    return filename, filepath, file_size_kb


# ==================== POST API - Generate All Agreements ====================

@router.post("/generate-agreements")
def generate_all_agreements(request: GenerateAgreementsRequest):
    """
    Generate all agreement documents (MSA, SLA, NDA, DPA, Annexures) based on purchase data.
    """
    db = SessionLocal()
    
    try:
        # Get project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all project data
        project_data = get_all_project_data(db, request.project_id)
        
        # Get RFP content if available
        rfp_content = None
        generated_rfp = project_data.get("generated_rfp")
        if generated_rfp:
            rfp_content = fetch_rfp_content(generated_rfp.id)
            if not rfp_content and generated_rfp.rfp_content:
                rfp_content = generated_rfp.rfp_content
        
        # Check if agreements already exist
        existing_agreements = db.query(AgreementDocument).filter(
            AgreementDocument.project_pk_id == project.pk_id
        ).all()
        
        if existing_agreements:
            # Delete existing agreements
            for agreement in existing_agreements:
                if agreement.filepath and os.path.exists(agreement.filepath):
                    os.remove(agreement.filepath)
                db.delete(agreement)
            db.commit()
        
        # Generate all agreements
        generated_docs = []
        
        for agreement_type in AGREEMENT_TYPES.keys():
            # Generate content using AI
            content = generate_agreement_content(
                agreement_type=agreement_type,
                project_data=project_data,
                purchase_info=request.data,
                rfp_content=rfp_content
            )
            
            # Create PDF
            filename, filepath, file_size_kb = create_agreement_pdf(
                content=content,
                agreement_type=agreement_type,
                project_id=request.project_id,
                project_title=request.project_title or project.title,
                vendor_name=request.data.vendor,
                po_number=request.data.purchase_order_number
            )
            
            # Save to database
            agreement_doc = AgreementDocument(
                project_pk_id=project.pk_id,
                project_id=project.id,
                purchase_order_number=request.data.purchase_order_number,
                agreement_type=agreement_type,
                content=content,
                filename=filename,
                filepath=filepath,
                file_size_kb=file_size_kb,
                vendor_name=request.data.vendor,
                po_value=request.data.po_value
            )
            
            db.add(agreement_doc)
            
            generated_docs.append({
                "agreement_type": agreement_type,
                "name": AGREEMENT_TYPES[agreement_type]["name"],
                "filename": filename,
                "filepath": filepath,
                "file_size_kb": round(file_size_kb, 2),
                "download_url": f"/purchase/download/agreement/{request.project_id}/{agreement_type}"
            })
        
        db.commit()
        
        return {
            "message": "All agreements generated successfully",
            "project_id": project.id,
            "project_title": project.title,
            "vendor": request.data.vendor,
            "purchase_order_number": request.data.purchase_order_number,
            "agreements": generated_docs,
            "created_at": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== DOWNLOAD AGREEMENT APIs ====================

@router.get("/download/agreement/{project_id}/{agreement_type}")
def download_agreement(project_id: str, agreement_type: str):
    """Download a specific agreement document by project ID and type"""
    db = SessionLocal()
    
    try:
        if agreement_type not in AGREEMENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agreement type. Valid types: {', '.join(AGREEMENT_TYPES.keys())}"
            )
        
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        agreement = db.query(AgreementDocument).filter(
            AgreementDocument.project_pk_id == project.pk_id,
            AgreementDocument.agreement_type == agreement_type
        ).first()
        
        if not agreement:
            raise HTTPException(
                status_code=404,
                detail=f"No {AGREEMENT_TYPES[agreement_type]['name']} found for this project"
            )
        
        if not agreement.filepath or not os.path.exists(agreement.filepath):
            raise HTTPException(status_code=404, detail="Agreement PDF file not found")
        
        return FileResponse(
            path=agreement.filepath,
            filename=agreement.filename,
            media_type="application/pdf"
        )
    
    finally:
        db.close()


@router.get("/download/msa/{project_id}")
def download_msa(project_id: str):
    """Download Master Service Agreement by project ID"""
    return download_agreement(project_id, "MSA")


@router.get("/download/sla/{project_id}")
def download_sla(project_id: str):
    """Download Service Level Agreement by project ID"""
    return download_agreement(project_id, "SLA")


@router.get("/download/nda/{project_id}")
def download_nda(project_id: str):
    """Download Non Disclosure Agreement by project ID"""
    return download_agreement(project_id, "NDA")


@router.get("/download/dpa/{project_id}")
def download_dpa(project_id: str):
    """Download Data Processing Agreement by project ID"""
    return download_agreement(project_id, "DPA")


@router.get("/download/annexures/{project_id}")
def download_annexures(project_id: str):
    """Download Annexures & Schedules by project ID"""
    return download_agreement(project_id, "ANNEXURES")


@router.get("/agreements/{project_id}")
def get_all_agreements_by_project(project_id: str):
    """Get all agreement documents for a project"""
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
            raise HTTPException(status_code=404, detail="No agreements found for this project")
        
        result = []
        for agreement in agreements:
            result.append({
                "id": agreement.id,
                "agreement_type": agreement.agreement_type,
                "name": AGREEMENT_TYPES.get(agreement.agreement_type, {}).get("name", agreement.agreement_type),
                "filename": agreement.filename,
                "file_size_kb": round(agreement.file_size_kb, 2) if agreement.file_size_kb else None,
                "download_url": f"/purchase/download/agreement/{project_id}/{agreement.agreement_type}",
                "created_at": agreement.created_at.isoformat() if agreement.created_at else None
            })
        
        return {
            "project_id": project.id,
            "project_title": project.title,
            "total_agreements": len(result),
            "agreements": result
        }
    
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
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not found in environment variables"
        )
    
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

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text


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
    
    filename = f"{purchase_order_number}.pdf"
    filepath = os.path.join(PO_STORAGE_DIR, filename)
    
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
    content_lines = po_content.split('\n')
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
    
    doc.build(story)
    
    file_size_kb = os.path.getsize(filepath) / 1024
    
    return filename, filepath, file_size_kb


# ==================== POST API - Create PO from Vendor Evaluation ====================

@router.post("/create-from-evaluation")
def create_purchase_order_from_evaluation(request: VendorEvaluationRequest):
    """Create purchase order from vendor evaluation response."""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        existing = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if existing:
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
        
        purchase_order_number = generate_purchase_order_number(request.project_id)
        
        po_content = generate_po_content_with_ai(
            project_id=request.project_id,
            project_title=request.project_title or project.title,
            purchase_order_number=purchase_order_number,
            vendor_name=request.winner.vendor_name,
            commercial_bid=request.winner.commercial_bid,
            publication_date=request.winner.publication_date
        )
        
        po_filename, po_filepath, file_size_kb = create_po_pdf(
            po_content=po_content,
            purchase_order_number=purchase_order_number,
            project_id=request.project_id,
            project_title=request.project_title or project.title,
            vendor_name=request.winner.vendor_name,
            po_value=request.winner.commercial_bid,
            publication_date=request.winner.publication_date
        )
        
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
        db.commit()
        db.refresh(purchase_data)
        
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
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== DOWNLOAD PO APIs ====================

@router.get("/download/{project_id}")
def download_purchase_order(project_id: str):
    """Download the generated purchase order PDF for a project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        purchase_data = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if not purchase_data:
            raise HTTPException(status_code=404, detail="No purchase order found for this project")
        
        if not purchase_data.po_filepath or not os.path.exists(purchase_data.po_filepath):
            raise HTTPException(status_code=404, detail="Purchase order PDF file not found")
        
        return FileResponse(
            path=purchase_data.po_filepath,
            filename=purchase_data.po_filename,
            media_type="application/pdf"
        )
    
    finally:
        db.close()


@router.get("/download/by-po-number/{po_number}")
def download_purchase_order_by_po_number(po_number: str):
    """Download the generated purchase order PDF by PO number"""
    db = SessionLocal()
    
    try:
        purchase_data = db.query(PurchaseData).filter(
            PurchaseData.purchase_order_number == po_number
        ).first()
        
        if not purchase_data:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        if not purchase_data.po_filepath or not os.path.exists(purchase_data.po_filepath):
            raise HTTPException(status_code=404, detail="Purchase order PDF file not found")
        
        return FileResponse(
            path=purchase_data.po_filepath,
            filename=purchase_data.po_filename,
            media_type="application/pdf"
        )
    
    finally:
        db.close()


# ==================== POST API - Full Submit ====================

@router.post("/submit")
def submit_purchase_data(request: PurchaseDataRequest):
    """Submit purchase order data for a project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        payment_terms = validate_payment_terms(request.payment_terms)
        warranty_period = validate_warranty_period(request.warranty_period)
        
        existing = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            existing.purchase_order_number = request.purchase_order_number
            existing.vendor = request.vendor
            existing.po_value = request.po_value
            existing.delivery_period = request.delivery_period
            existing.payment_terms = payment_terms
            existing.warranty_period = warranty_period
            existing.penalty_clause = request.penalty_clause
            
            db.commit()
            db.refresh(existing)
            
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
            existing_po = db.query(PurchaseData).filter(
                PurchaseData.purchase_order_number == request.purchase_order_number
            ).first()
            
            if existing_po:
                raise HTTPException(
                    status_code=400,
                    detail=f"Purchase order number '{request.purchase_order_number}' already exists"
                )
            
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
            db.commit()
            db.refresh(purchase_data)
            
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
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== GET APIs ====================

@router.get("/list")
def get_all_purchase_data():
    """Get all purchase data records"""
    db = SessionLocal()
    
    try:
        records = db.query(PurchaseData).order_by(PurchaseData.created_at.desc()).all()
        
        result = []
        for record in records:
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
        
        return {
            "total_records": len(result),
            "purchase_data": result
        }
    
    finally:
        db.close()


@router.get("/{project_id}")
def get_purchase_data_by_project(project_id: str):
    """Get purchase data for a specific project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        purchase_data = db.query(PurchaseData).filter(
            PurchaseData.project_pk_id == project.pk_id
        ).first()
        
        if not purchase_data:
            raise HTTPException(status_code=404, detail="No purchase data found for this project")
        
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
    
    finally:
        db.close()


@router.get("/options/payment-terms")
def get_payment_terms_options():
    """Get valid payment terms options"""
    return {
        "payment_terms": VALID_PAYMENT_TERMS
    }


@router.get("/options/warranty-periods")
def get_warranty_period_options():
    """Get valid warranty period options"""
    return {
        "warranty_periods": VALID_WARRANTY_PERIODS
    }
