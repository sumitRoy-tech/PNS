from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from database import SessionLocal, ProjectCredential, PurchaseData
from datetime import datetime
import random
import os
import anthropic
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/purchase", tags=["Purchase Order"])

# Directory for storing generated PO PDFs
PO_STORAGE_DIR = "generated_purchase_orders"
os.makedirs(PO_STORAGE_DIR, exist_ok=True)


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
    """Generate purchase order number based on project_id"""
    random_suffix = random.randint(1000, 9999)
    return f"PO-{project_id}-{random_suffix}"


# ==================== ANTHROPIC API INTEGRATION ====================

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
    
    # Custom styles
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
    
    # Terms and Conditions
    story.append(Paragraph("TERMS AND CONDITIONS", header_style))
    terms = [
        "1. Delivery Period: As per agreed timeline in the RFP document.",
        "2. Payment Terms: As per the contract agreement.",
        "3. Warranty: Standard warranty as per vendor's policy.",
        "4. Penalty Clause: Delay penalties as per RFP terms.",
        "5. Quality: All deliverables must meet the specifications mentioned in the RFP.",
        "6. Compliance: Vendor must comply with all applicable laws and regulations.",
        "7. Confidentiality: All project information must be kept confidential.",
        "8. Dispute Resolution: Any disputes shall be resolved through arbitration.",
    ]
    for term in terms:
        story.append(Paragraph(term, normal_style))
    
    story.append(Spacer(1, 30))
    
    # AI Generated Content Section
    story.append(Paragraph("ADDITIONAL DETAILS", header_style))
    # Split AI content into paragraphs
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
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
    ]))
    story.append(sig_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 80, center_style))
    story.append(Paragraph("Punjab & Sind Bank - Generated Purchase Order", center_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", center_style))
    
    # Build PDF
    doc.build(story)
    
    # Get file size
    file_size_kb = os.path.getsize(filepath) / 1024
    
    return filename, filepath, file_size_kb


# ==================== POST API - Create PO from Vendor Evaluation ====================

@router.post("/create-from-evaluation")
def create_purchase_order_from_evaluation(request: VendorEvaluationRequest):
    """
    Create purchase order from vendor evaluation response.
    Generates PO using Anthropic API, creates PDF, and saves to database.
    """
    db = SessionLocal()
    
    try:
        # Find project by ID
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if purchase order already exists for this project
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
        
        # Generate purchase order number
        purchase_order_number = generate_purchase_order_number(request.project_id)
        
        # Generate PO content using Anthropic API
        po_content = generate_po_content_with_ai(
            project_id=request.project_id,
            project_title=request.project_title or project.title,
            purchase_order_number=purchase_order_number,
            vendor_name=request.winner.vendor_name,
            commercial_bid=request.winner.commercial_bid,
            publication_date=request.winner.publication_date
        )
        
        # Create PDF
        po_filename, po_filepath, file_size_kb = create_po_pdf(
            po_content=po_content,
            purchase_order_number=purchase_order_number,
            project_id=request.project_id,
            project_title=request.project_title or project.title,
            vendor_name=request.winner.vendor_name,
            po_value=request.winner.commercial_bid,
            publication_date=request.winner.publication_date
        )
        
        # Create new purchase data record
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


# ==================== DOWNLOAD API ====================

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
