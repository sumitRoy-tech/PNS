from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal, ProjectCredential, TechnicalCommitteeReview, FunctionalAssessment, UploadedFile
from datetime import datetime

router = APIRouter(prefix="/technical-review", tags=["Technical Committee Review"])


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

            return {
                "message": "Technical review updated successfully",
                "review_id": existing.id,
                "project_id": project.id,
                "project_title": project.title,
                "department": project.department,
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
                "updated_at": existing.updated_at.isoformat() if existing.updated_at else None
            }

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

            return {
                "message": "Technical review submitted successfully",
                "review_id": review.id,
                "project_id": project.id,
                "project_title": project.title,
                "department": project.department,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None
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
                "reviewed_by": review.reviewed_by,
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
            overall_status = f"Technical Review: {tech_review.status}"
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
