import logging
from fastapi import APIRouter, HTTPException, Form
from database import SessionLocal, ProjectCredential, UploadedFile, FunctionalAssessment
from datetime import datetime
from typing import Optional

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("FUNCTIONAL MODULE INITIALIZATION STARTED")
logger.info("=" * 60)

router = APIRouter(prefix="/functional", tags=["Functional Assessment"])
logger.info("Router created with prefix: /functional")
logger.info("Tags: ['Functional Assessment']")

logger.info("=" * 60)
logger.info("FUNCTIONAL MODULE INITIALIZED SUCCESSFULLY")
logger.info("=" * 60)


@router.get("/get-projects")
def get_all_projects():
    logger.info("=" * 60)
    logger.info("API CALLED: GET /functional/get-projects")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info("Querying all projects from ProjectCredential table...")
        logger.info("Order by: created_at DESC")
        projects = db.query(ProjectCredential).order_by(ProjectCredential.created_at.desc()).all()
        logger.info(f"Total projects found: {len(projects)}")
        
        result = []
        for idx, project in enumerate(projects):
            logger.debug(f"Processing project {idx + 1}/{len(projects)}: {project.id}")
            
            logger.debug(f"  Counting files for project pk_id: {project.pk_id}")
            file_count = db.query(UploadedFile).filter(
                UploadedFile.project_pk_id == project.pk_id
            ).count()
            logger.debug(f"  File count: {file_count}")
            
            logger.debug(f"  Checking for existing assessment...")
            assessment = db.query(FunctionalAssessment).filter(
                FunctionalAssessment.project_pk_id == project.pk_id
            ).first()
            logger.debug(f"  Assessment exists: {assessment is not None}")
            if assessment:
                logger.debug(f"  Assessment status: {assessment.status}")
            
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
        
        logger.info(f"Successfully processed {len(result)} projects")
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /functional/get-projects - SUCCESS")
        logger.info(f"Returning {len(result)} projects")
        logger.info("=" * 60)
        
        return {
            "total_projects": len(result),
            "projects": result
        }
    
    except Exception as e:
        logger.error(f"Error in get_all_projects: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/projects/{project_id}")
def get_project_details(project_id: str):
    """
    Get detailed info for a specific project including files
    """
    logger.info("=" * 60)
    logger.info("API CALLED: GET /functional/projects/{project_id}")
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
        
        logger.info(f"Project found: {project.title}")
        logger.info(f"  - pk_id: {project.pk_id}")
        logger.info(f"  - department: {project.department}")
        logger.info(f"  - category: {project.category}")
        logger.info(f"  - priority: {project.priority}")
        
        logger.info(f"Querying uploaded files for project pk_id: {project.pk_id}")
        files = db.query(UploadedFile).filter(
            UploadedFile.project_pk_id == project.pk_id
        ).order_by(UploadedFile.label).all()
        logger.info(f"Files found: {len(files)}")
        for f in files:
            logger.debug(f"  - File: {f.original_filename} (label: {f.label}, size: {f.file_size_kb} KB)")
        
        logger.info(f"Querying functional assessment for project pk_id: {project.pk_id}")
        assessment = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
        if assessment:
            logger.info(f"Assessment found with id: {assessment.id}")
            logger.info(f"  - status: {assessment.status}")
            logger.info(f"  - created_at: {assessment.created_at}")
        else:
            logger.info("No assessment found for this project")
        
        response = {
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
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /functional/projects/{project_id} - SUCCESS")
        logger.info(f"Returning project details for: {project_id}")
        logger.info(f"  - Files count: {len(files)}")
        logger.info(f"  - Has assessment: {assessment is not None}")
        logger.info("=" * 60)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project_details: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.post("/assessment")
def create_assessment(
    project_id: str = Form(...),
    functional_fit_assessment: str = Form(...),
    technical_feasibility: str = Form(...),
    risk_assessment: str = Form(...),
    recommendations: str = Form(...)
):
    logger.info("=" * 60)
    logger.info("API CALLED: POST /functional/assessment")
    logger.info("=" * 60)
    logger.info("Request Parameters:")
    logger.info(f"  - project_id: {project_id}")
    logger.info(f"  - functional_fit_assessment length: {len(functional_fit_assessment)} chars")
    logger.info(f"  - technical_feasibility length: {len(technical_feasibility)} chars")
    logger.info(f"  - risk_assessment length: {len(risk_assessment)} chars")
    logger.info(f"  - recommendations length: {len(recommendations)} chars")

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
        
        logger.info(f"Checking for existing assessment for project pk_id: {project.pk_id}")
        existing = db.query(FunctionalAssessment).filter(
            FunctionalAssessment.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            logger.warning(f"Assessment already exists for project: {project_id}")
            logger.warning(f"Existing assessment id: {existing.id}")
            logger.error("Raising HTTPException 409: Assessment already exists")
            raise HTTPException(
                status_code=409, 
                detail="Assessment already exists for this project. Use PUT to update."
            )
        
        logger.info("No existing assessment found. Creating new assessment...")
        logger.info("Building FunctionalAssessment object...")
        assessment = FunctionalAssessment(
            project_pk_id=project.pk_id,
            project_id=project.id,
            functional_fit_assessment=functional_fit_assessment,
            technical_feasibility=technical_feasibility,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            status="submitted"
        )
        
        logger.info("Adding assessment to database session...")
        db.add(assessment)
        
        logger.info("Committing transaction...")
        db.commit()
        logger.info("Transaction committed successfully")
        
        logger.info("Refreshing assessment object...")
        db.refresh(assessment)
        logger.info(f"Assessment created with id: {assessment.id}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /functional/assessment - SUCCESS")
        logger.info(f"Assessment created successfully")
        logger.info(f"  - assessment_id: {assessment.id}")
        logger.info(f"  - project_id: {project.id}")
        logger.info(f"  - status: {assessment.status}")
        logger.info("=" * 60)
        
        return {
            "message": "Assessment submitted successfully",
            "assessment_id": assessment.id,
            "project_id": project.id,
            "status": assessment.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_assessment: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/assessments")
def get_all_assessments():
    logger.info("=" * 60)
    logger.info("API CALLED: GET /functional/assessments")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info("Querying all assessments from FunctionalAssessment table...")
        logger.info("Order by: created_at DESC")
        assessments = db.query(FunctionalAssessment).order_by(
            FunctionalAssessment.created_at.desc()
        ).all()
        logger.info(f"Total assessments found: {len(assessments)}")
        
        for idx, a in enumerate(assessments):
            logger.debug(f"Assessment {idx + 1}: id={a.id}, project_id={a.project_id}, status={a.status}")
        
        response = {
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
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /functional/assessments - SUCCESS")
        logger.info(f"Returning {len(assessments)} assessments")
        logger.info("=" * 60)
        
        return response
    
    except Exception as e:
        logger.error(f"Error in get_all_assessments: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")
