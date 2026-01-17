from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal, ProjectCredential, TechnicalCommitteeReview, FunctionalAssessment, UploadedFile, GeneratedRFP
from datetime import datetime
import anthropic
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import re
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/technical-review", tags=["Technical Committee Review"])

# ==================== CONFIG ====================
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")  
RFP_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_rfps")
os.makedirs(RFP_OUTPUT_DIR, exist_ok=True)


# ==================== PYDANTIC MODELS ====================

class TechnicalReviewRequest(BaseModel):
    project_id: str
    architecture_review: str
    security_assessment: str
    integration_complexity: str
    rbi_compliance_check: str
    technical_committee_recommendation: str


class TechnicalReviewUpdateRequest(BaseModel):
    architecture_review: Optional[str] = None
    security_assessment: Optional[str] = None
    integration_complexity: Optional[str] = None
    rbi_compliance_check: Optional[str] = None
    technical_committee_recommendation: Optional[str] = None


def generate_rfp_internal(db, project_id: str):
    from technical_committee_review import generate_rfp, GenerateRFPRequest
    req = GenerateRFPRequest(project_id=project_id)
    result = generate_rfp(req)
    return result




# ==================== PUT API ====================

@router.post("/submit")
def submit_technical_review(request: TechnicalReviewRequest):

    db = SessionLocal()

    try:
        # 1️⃣ Find the project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2️⃣ Check if review already exists
        existing = db.query(TechnicalCommitteeReview).filter(
            TechnicalCommitteeReview.project_pk_id == project.pk_id
        ).first()

        if existing:
            # 🔁 UPDATE existing review
            existing.architecture_review = request.architecture_review
            existing.security_assessment = request.security_assessment
            existing.integration_complexity = request.integration_complexity
            existing.rbi_compliance_check = request.rbi_compliance_check
            existing.technical_committee_recommendation = request.technical_committee_recommendation

            db.commit()
            db.refresh(existing)

            review = existing

        else:
            # ➕ CREATE new review
            review = TechnicalCommitteeReview(
                project_pk_id=project.pk_id,
                project_id=project.id,
                architecture_review=request.architecture_review,
                security_assessment=request.security_assessment,
                integration_complexity=request.integration_complexity,
                rbi_compliance_check=request.rbi_compliance_check,
                technical_committee_recommendation=request.technical_committee_recommendation
            )

            db.add(review)
            db.commit()
            db.refresh(review)

        # ============================
        # 🔥 AUTO GENERATE RFP HERE
        # ============================

        rfp_result = generate_rfp_internal(db, project.id)

        return {
            "message": "Technical review submitted and RFP generated successfully",
            "review_id": review.id,
            "rfp_id": rfp_result["rfp_id"],
            "project_id": project.id,
            "project_title": project.title,
            "download_url": rfp_result["download_url"],
            "created_at": review.created_at.isoformat() if review.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        db.close()



# ==================== GET APIs ====================

@router.get("/projects")
def get_projects_for_review():

    db = SessionLocal()
    
    try:
        # Get projects with functional assessments
        projects = db.query(ProjectCredential).join(
            FunctionalAssessment,
            ProjectCredential.pk_id == FunctionalAssessment.project_pk_id
        ).order_by(ProjectCredential.created_at.desc()).all()
        
        result = []
        for project in projects:
            # Get assessment
            assessment = db.query(FunctionalAssessment).filter(
                FunctionalAssessment.project_pk_id == project.pk_id
            ).first()
            
            # Check if technical review exists
            tech_review = db.query(TechnicalCommitteeReview).filter(
                TechnicalCommitteeReview.project_pk_id == project.pk_id
            ).first()
            
            # Get file count
            file_count = db.query(UploadedFile).filter(
                UploadedFile.project_pk_id == project.pk_id
            ).count()
            
            result.append({
                "pk_id": project.pk_id,
                "project_id": project.id,
                "title": project.title,
                "department": project.department,
                "category": project.category,
                "priority": project.priority,
                "estimated_amount": project.estimated_amount,
                "submitted_by": project.submitted_by,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "file_count": file_count,
                "functional_assessment_status": assessment.status if assessment else None,
            })
        
        return {
            "total_projects": len(result),
            "projects": result
        }
    
    finally:
        db.close()


@router.get("/reviews")
def get_all_reviews():
    """
    Get all technical committee reviews
    """
    db = SessionLocal()
    
    try:
        reviews = db.query(TechnicalCommitteeReview).order_by(
            TechnicalCommitteeReview.created_at.desc()
        ).all()
        
        result = []
        for review in reviews:
            # Get project info
            project = db.query(ProjectCredential).filter(
                ProjectCredential.pk_id == review.project_pk_id
            ).first()
            
            result.append({
                "review_id": review.id,
                "project_id": review.project_id,
                "project_title": project.title if project else None,
                "department": project.department if project else None,
                "architecture_review": review.architecture_review,
                "security_assessment": review.security_assessment,
                "integration_complexity": review.integration_complexity,
                "rbi_compliance_check": review.rbi_compliance_check,
                "technical_committee_recommendation": review.technical_committee_recommendation,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None
            })
        
        return {
            "total_reviews": len(result),
            "reviews": result
        }
    
    finally:
        db.close()


@router.get("/reviews/{project_id}")
def get_review_by_project(project_id: str):
    """
    Get technical committee review for a specific project
    """
    db = SessionLocal()
    
    try:
        # Find the project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get review
        review = db.query(TechnicalCommitteeReview).filter(
            TechnicalCommitteeReview.project_pk_id == project.pk_id
        ).first()
        
        if not review:
            raise HTTPException(status_code=404, detail="Technical review not found for this project")
        
        # Get functional assessment
        assessment = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
        # Get files
        files = db.query(UploadedFile).filter(
            UploadedFile.project_pk_id == project.pk_id
        ).order_by(UploadedFile.label).all()
        
        return {
            "project": {
                "pk_id": project.pk_id,
                "project_id": project.id,
                "title": project.title,
                "department": project.department,
                "category": project.category,
                "priority": project.priority,
                "estimated_amount": project.estimated_amount,
                "business_justification": project.business_justification,
                "submitted_by": project.submitted_by,
                "created_at": project.created_at.isoformat() if project.created_at else None
            },
            "functional_assessment": {
                "functional_fit_assessment": assessment.functional_fit_assessment,
                "technical_feasibility": assessment.technical_feasibility,
                "risk_assessment": assessment.risk_assessment,
                "recommendations": assessment.recommendations
            } if assessment else None,
            "technical_review": {
                "review_id": review.id,
                "architecture_review": review.architecture_review,
                "security_assessment": review.security_assessment,
                "integration_complexity": review.integration_complexity,
                "rbi_compliance_check": review.rbi_compliance_check,
                "technical_committee_recommendation": review.technical_committee_recommendation,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None
            },
            "files": [
                {
                    "label": f.label,
                    "original_filename": f.original_filename,
                    "file_size_kb": f.file_size_kb,
                    "download_url": f"/requirements/files/download/{f.saved_filename}"
                }
                for f in files
            ]
        }
    
    finally:
        db.close()


@router.get("/summary/{project_id}")
def get_project_summary(project_id: str):
    """
    Get complete summary of project with all stages
    """
    db = SessionLocal()
    
    try:
        # Find the project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all related data
        files = db.query(UploadedFile).filter(
            UploadedFile.project_pk_id == project.pk_id
        ).count()
        
        assessment = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
        tech_review = db.query(TechnicalCommitteeReview).filter(
            TechnicalCommitteeReview.project_pk_id == project.pk_id
        ).first()
        
        # Determine overall status
        if tech_review:
            overall_status = "Technical Review: Completed"
        elif assessment:
            overall_status = f"Functional Assessment: {assessment.status}"
        else:
            overall_status = "Pending Assessment"
        
        return {
            "project_id": project.id,
            "title": project.title,
            "department": project.department,
            "priority": project.priority,
            "estimated_amount": project.estimated_amount,
            "overall_status": overall_status,
            "stages": {
                "requirement_submitted": True,
                "files_uploaded": files > 0,
                "file_count": files,
                "functional_assessment_completed": assessment is not None,
                "functional_assessment_status": assessment.status if assessment else None,
                "technical_review_completed": tech_review is not None
            },
            "created_at": project.created_at.isoformat() if project.created_at else None
        }
    
    finally:
        db.close()


# ==================== RFP GENERATION ====================

class GenerateRFPRequest(BaseModel):
    project_id: str


def clean_text_for_pdf(text: str) -> str:
    """Remove markdown and clean text for PDF"""
    if not text:
        return text
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    return text


def generate_pdf(content: str, filepath: str, title: str):
    """Generate PDF from text content"""
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=14
    )
    
    story = []
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.5 * inch))
    
    # Process content - split by sections
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.2 * inch))
            continue
        
        # Check if it's a heading (starts with number or all caps)
        if re.match(r'^\d+\.', line) or (line.isupper() and len(line) < 100):
            story.append(Paragraph(line, heading_style))
        else:
            # Escape special characters for ReportLab
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(line, body_style))
    
    doc.build(story)


@router.post("/generate-rfp")
def generate_rfp(request: GenerateRFPRequest):
    """
    Generate RFP document using Claude AI
    
    Fetches all project data and creates a professional RFP document
    Saves as PDF for download
    """
    db = SessionLocal()
    
    try:
        # ==================== 1. FETCH ALL PROJECT DATA ====================
        
        # Get project
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get uploaded files and their extracted text
        files = db.query(UploadedFile).filter(
            UploadedFile.project_pk_id == project.pk_id
        ).order_by(UploadedFile.label).all()
        
        # Get functional assessment
        assessment = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
        # Get technical review
        tech_review = db.query(TechnicalCommitteeReview).filter(
            TechnicalCommitteeReview.project_pk_id == project.pk_id
        ).first()
        
        # ==================== 2. BUILD CONTEXT FOR CLAUDE ====================
        
        # Compile all extracted text from files
        documents_text = ""
        if files:
            for f in files:
                if f.text_extracted:
                    documents_text += f"\n\n--- Document: {f.original_filename} ---\n"
                    documents_text += f.text_extracted[:5000]  # Limit per document
        
        # Build comprehensive context
        context = f"""
PROJECT INFORMATION:
- Project ID: {project.id}
- Title: {project.title}
- Department: {project.department}
- Category: {project.category}
- Priority: {project.priority}
- Estimated Amount: {project.estimated_amount}
- Business Justification: {project.business_justification}
- Submitted By: {project.submitted_by}
- Technical Specification: {project.technical_specification or 'Not provided'}
- Expected Timeline: {project.expected_timeline or 'Not specified'}
"""
        
        if assessment:
            context += f"""
FUNCTIONAL ASSESSMENT:
- Functional Fit Assessment: {assessment.functional_fit_assessment}
- Technical Feasibility: {assessment.technical_feasibility}
- Risk Assessment: {assessment.risk_assessment}
- Recommendations: {assessment.recommendations}
"""
        
        if tech_review:
            context += f"""
TECHNICAL COMMITTEE REVIEW:
- Architecture Review: {tech_review.architecture_review}
- Security Assessment: {tech_review.security_assessment}
- Integration Complexity: {tech_review.integration_complexity}
- RBI/Compliance Check: {tech_review.rbi_compliance_check}
- Technical Committee Recommendation: {tech_review.technical_committee_recommendation}
"""
        
        if documents_text:
            context += f"""
EXTRACTED DOCUMENT CONTENT:
{documents_text[:15000]}
"""
        
        # ==================== 3. CALL CLAUDE API ====================
        
        prompt = f"""You are an expert RFP (Request for Proposal) writer. Based on the following project information, create a comprehensive and professional RFP document.

{context}

Create a complete RFP document with the following sections:
1. EXECUTIVE SUMMARY
2. INTRODUCTION AND BACKGROUND
3. SCOPE OF WORK
4. TECHNICAL REQUIREMENTS
5. FUNCTIONAL REQUIREMENTS
6. COMPLIANCE AND REGULATORY REQUIREMENTS
7. VENDOR QUALIFICATIONS
8. EVALUATION CRITERIA
9. TIMELINE AND MILESTONES
10. BUDGET AND PRICING STRUCTURE
11. TERMS AND CONDITIONS
12. SUBMISSION REQUIREMENTS
13. CONTACT INFORMATION

Write in a professional, formal tone. Be specific and detailed based on the provided information.
Do NOT use markdown formatting (no #, *, _, etc.). Write in plain text only.
Each section should be clearly labeled with the section number and title.
"""

        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        rfp_content = response.content[0].text
        rfp_content = clean_text_for_pdf(rfp_content)
        
        # ==================== 4. GENERATE PDF ====================
        
        # Get version number
        existing_rfps = db.query(GeneratedRFP).filter(
            GeneratedRFP.project_pk_id == project.pk_id
        ).count()
        version = existing_rfps + 1
        
        # Generate filename
        rfp_filename = f"RFP_{project.id}_v{version}.pdf"
        rfp_filepath = os.path.join(RFP_OUTPUT_DIR, rfp_filename)
        
        # Create PDF
        generate_pdf(
            content=rfp_content,
            filepath=rfp_filepath,
            title=f"Request for Proposal: {project.title}"
        )
        
        # Get file size
        file_size_kb = round(os.path.getsize(rfp_filepath) / 1024, 2)
        
        # ==================== 5. SAVE TO DATABASE ====================
        
        generated_rfp = GeneratedRFP(
            project_pk_id=project.pk_id,
            project_id=project.id,
            rfp_content=rfp_content,
            rfp_filename=rfp_filename,
            rfp_filepath=rfp_filepath,
            version=version,
            file_size_kb=file_size_kb
        )
        
        db.add(generated_rfp)
        db.commit()
        db.refresh(generated_rfp)
        
        return {
            "message": "RFP generated successfully",
            "rfp_id": generated_rfp.id,
            "project_id": project.id,
            "project_title": project.title,
            "version": version,
            "filename": rfp_filename,
            "file_size_kb": file_size_kb,
            "download_url": f"/technical-review/rfp/download/{generated_rfp.id}",
            "created_at": generated_rfp.created_at.isoformat() if generated_rfp.created_at else None,
            "data_sources": {
                "project_info": True,
                "functional_assessment": assessment is not None,
                "technical_review": tech_review is not None,
                "documents_used": len(files),
                "documents_with_text": len([f for f in files if f.text_extracted])
            }
        }
    
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating RFP: {str(e)}")
    
    finally:
        db.close()


# ==================== RFP DOWNLOAD APIs ====================

@router.get("/rfp/download/{rfp_id}")
def download_rfp(rfp_id: int):
    db = SessionLocal()
 
    try:
        rfp = db.query(GeneratedRFP).filter(GeneratedRFP.id == rfp_id).first()
 
        if not rfp:
            raise HTTPException(status_code=404, detail="RFP not found")
 
        if not os.path.exists(rfp.rfp_filepath):
            raise HTTPException(status_code=404, detail="RFP file not found on server")
 
        return FileResponse(
            path=rfp.rfp_filepath,
            media_type="application/pdf",
            filename=rfp.rfp_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{rfp.rfp_filename}"'
            }
        )
 
    finally:
        db.close()


@router.get("/rfp/list")
def list_all_rfps():
    """List all generated RFPs"""
    db = SessionLocal()
    
    try:
        rfps = db.query(GeneratedRFP).order_by(GeneratedRFP.created_at.desc()).all()
        
        result = []
        for rfp in rfps:
            project = db.query(ProjectCredential).filter(
                ProjectCredential.pk_id == rfp.project_pk_id
            ).first()
            
            result.append({
                "rfp_id": rfp.id,
                "project_id": rfp.project_id,
                "project_title": project.title if project else None,
                "version": rfp.version,
                "filename": rfp.rfp_filename,
                "file_size_kb": rfp.file_size_kb,
                "download_url": f"/technical-review/rfp/download/{rfp.id}",
                "created_at": rfp.created_at.isoformat() if rfp.created_at else None
            })
        
        return {
            "total_rfps": len(result),
            "rfps": result
        }
    
    finally:
        db.close()


@router.get("/rfp/project/{project_id}")
def get_rfps_by_project(project_id: str):
    """Get all RFP versions for a project"""
    db = SessionLocal()
    
    try:
        rfps = db.query(GeneratedRFP).filter(
            GeneratedRFP.project_id == project_id
        ).order_by(GeneratedRFP.version.desc()).all()
        
        if not rfps:
            raise HTTPException(status_code=404, detail="No RFPs found for this project")
        
        return {
            "project_id": project_id,
            "total_versions": len(rfps),
            "rfps": [
                {
                    "rfp_id": rfp.id,
                    "version": rfp.version,
                    "filename": rfp.rfp_filename,
                    "file_size_kb": rfp.file_size_kb,
                    "download_url": f"/technical-review/rfp/download/{rfp.id}",
                    "created_at": rfp.created_at.isoformat() if rfp.created_at else None
                }
                for rfp in rfps
            ]
        }
    
    finally:
        db.close()


@router.get("/rfp/content/{rfp_id}")
def get_rfp_content(rfp_id: int):
    """Get RFP text content (for editing/viewing)"""
    db = SessionLocal()
    
    try:
        rfp = db.query(GeneratedRFP).filter(GeneratedRFP.id == rfp_id).first()
        
        if not rfp:
            raise HTTPException(status_code=404, detail="RFP not found")
        
        project = db.query(ProjectCredential).filter(
            ProjectCredential.pk_id == rfp.project_pk_id
        ).first()
        
        return {
            "rfp_id": rfp.id,
            "project_id": rfp.project_id,
            "project_title": project.title if project else None,
            "version": rfp.version,
            "content": rfp.rfp_content,
            "filename": rfp.rfp_filename,
            "download_url": f"/technical-review/rfp/download/{rfp.id}",
            "created_at": rfp.created_at.isoformat() if rfp.created_at else None
        }
    
    finally:
        db.close()
