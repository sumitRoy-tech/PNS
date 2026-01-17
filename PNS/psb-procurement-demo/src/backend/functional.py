from fastapi import APIRouter, HTTPException, Form
from database import SessionLocal, ProjectCredential, UploadedFile, FunctionalAssessment
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/functional", tags=["Functional Assessment"])


@router.get("/get-projects")
def get_all_projects():

    db = SessionLocal()
    
    try:
        projects = db.query(ProjectCredential).order_by(ProjectCredential.created_at.desc()).all()
        
        result = []
        for project in projects:
            file_count = db.query(UploadedFile).filter(
                UploadedFile.project_pk_id == project.pk_id
            ).count()
            
            assessment = db.query(FunctionalAssessment).filter(
                FunctionalAssessment.project_pk_id == project.pk_id
            ).first()
            
            result.append({
                "pk_id": project.pk_id,
                "project_id": project.id,
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
                "file_count": file_count,
                "has_assessment": assessment is not None,
                "assessment_status": assessment.status if assessment else None
            })
        
        return {
            "total_projects": len(result),
            "projects": result
        }
    
    finally:
        db.close()


@router.get("/projects/{project_id}")
def get_project_details(project_id: str):
    """
    Get detailed info for a specific project including files
    """
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        files = db.query(UploadedFile).filter(
            UploadedFile.project_pk_id == project.pk_id
        ).order_by(UploadedFile.label).all()
        
        assessment = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
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
                "technical_specification": project.technical_specification,
                "expected_timeline": project.expected_timeline,
                "email": project.email,
                "phone_number": project.phone_number,
                "created_at": project.created_at.isoformat() if project.created_at else None
            },
            "files": [
                {
                    "id": f.id,
                    "label": f.label,
                    "original_filename": f.original_filename,
                    "saved_filename": f.saved_filename,
                    "file_extension": f.file_extension,
                    "file_size_kb": f.file_size_kb,
                    "download_url": f"/requirements/files/download/{f.saved_filename}"
                }
                for f in files
            ],
            "assessment": {
                "id": assessment.id,
                "functional_fit_assessment": assessment.functional_fit_assessment,
                "technical_feasibility": assessment.technical_feasibility,
                "risk_assessment": assessment.risk_assessment,
                "recommendations": assessment.recommendations,
                "status": assessment.status,
                "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                "updated_at": assessment.updated_at.isoformat() if assessment.updated_at else None
            } if assessment else None
        }
    
    finally:
        db.close()


@router.post("/assessment")
def create_assessment(
    project_id: str = Form(...),
    functional_fit_assessment: str = Form(...),
    technical_feasibility: str = Form(...),
    risk_assessment: str = Form(...),
    recommendations: str = Form(...)
):

    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        existing = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=409, 
                detail="Assessment already exists for this project. Use PUT to update."
            )
        
        assessment = FunctionalAssessment(
            project_pk_id=project.pk_id,
            project_id=project.id,
            functional_fit_assessment=functional_fit_assessment,
            technical_feasibility=technical_feasibility,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            status="submitted"
        )
        
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        
        return {
            "message": "Assessment submitted successfully",
            "assessment_id": assessment.id,
            "project_id": project.id,
            "status": assessment.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.get("/assessments")
def get_all_assessments():

    db = SessionLocal()
    
    try:
        assessments = db.query(FunctionalAssessment).order_by(
            FunctionalAssessment.created_at.desc()
        ).all()
        
        return {
            "total_assessments": len(assessments),
            "assessments": [
                {
                    "id": a.id,
                    "project_id": a.project_id,
                    "functional_fit_assessment": a.functional_fit_assessment,
                    "technical_feasibility": a.technical_feasibility,
                    "risk_assessment": a.risk_assessment,
                    "recommendations": a.recommendations,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "updated_at": a.updated_at.isoformat() if a.updated_at else None
                }
                for a in assessments
            ]
        }
    
    finally:
        db.close()
