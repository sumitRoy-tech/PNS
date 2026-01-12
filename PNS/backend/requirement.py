from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import SessionLocal, ProjectCredential
from datetime import datetime
import os
import faiss
import numpy as np

router = APIRouter(prefix="/requirements", tags=["Requirements"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# FAISS index
dimension = 384
faiss_index = faiss.IndexFlatL2(dimension)

serial_counter = 1


def generate_project_id():
    global serial_counter
    today = datetime.now()
    pid = f"PSB/PROC/{today.year}/{today.month}/{today.day}/{serial_counter}"
    serial_counter += 1
    return pid


@router.post("/")
async def create_requirement(
    title: str = Form(...),
    department: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    estimated_amount: float = Form(...),
    business_justification: str = Form(...),
    submitted_by: str = Form(...),

    technical_specification: str = Form(None),
    email: str = Form(None),
    phone_number: str = Form(None),

    files: list[UploadFile] = File(None)
):
    db = SessionLocal()
    project_id = generate_project_id()

    if files:
        for file in files:
            if file.content_type not in [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ]:
                raise HTTPException(status_code=400, detail="Invalid file type")

            content = await file.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File size exceeds 10MB")

            file_path = f"{UPLOAD_DIR}/{project_id}_{file.filename}"
            with open(file_path, "wb") as f:
                f.write(content)

            vector = np.random.rand(1, dimension).astype("float32")
            faiss_index.add(vector)

    project = ProjectCredential(
        id=project_id,
        title=title,
        department=department,
        category=category,
        priority=priority,
        estimated_amount=estimated_amount,
        business_justification=business_justification,
        submitted_by=submitted_by,
        technical_specification=technical_specification,
        email=email,
        phone_number=phone_number
    )

    db.add(project)
    db.commit()
    db.close()

    return {
        "message": "Requirement created successfully",
        "project_id": project_id
    }
