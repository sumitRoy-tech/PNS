from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, ProjectCredential, UploadedFile
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

router = APIRouter(prefix="/requirements", tags=["Requirements"])

# ==================== PATH SETUP ====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss.index")

# ==================== FAISS SETUP ====================

# Load embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
dimension = 384  # all-MiniLM-L6-v2 produces 384-dim vectors

if os.path.exists(FAISS_INDEX_PATH):
    faiss_index = faiss.read_index(FAISS_INDEX_PATH)
else:
    faiss_index = faiss.IndexFlatL2(dimension)

# Store file metadata for FAISS index mapping
FAISS_METADATA_PATH = os.path.join(BASE_DIR, "faiss_metadata.npy")
if os.path.exists(FAISS_METADATA_PATH):
    faiss_metadata = list(np.load(FAISS_METADATA_PATH, allow_pickle=True))
else:
    faiss_metadata = []

# ==================== HELPERS ====================

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
    faiss.write_index(faiss_index, FAISS_INDEX_PATH)
    np.save(FAISS_METADATA_PATH, np.array(faiss_metadata, dtype=object))


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc = Document(BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        print(f"DOCX extraction error: {e}")
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
        print(f"XLSX extraction error: {e}")
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

# ==================== API ====================

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
    db = SessionLocal()

    try:
        # ==================== AMOUNT PARSING ====================
        parsed_amount = parse_estimated_amount(estimated_amount)

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

        # ==================== BUSINESS ID ====================
        project.id = build_project_id(project.pk_id)

        # ==================== FILE HANDLING ====================
        saved_files = []
        
        if files:
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

        # ==================== FINAL COMMIT ====================
        db.commit()

        return {
            "message": "Requirement created successfully",
            "project_id": project.id,
            "estimated_amount_rupees": parsed_amount,
            "files_uploaded": len(saved_files),
            "files": saved_files
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate requirement detected"
        )

    finally:
        db.close()

@router.get("/files")
def list_uploaded_files(project_id: str | None = None):
    """
    List uploaded files.
    - If project_id is provided -> only files for that project
    - Else -> all uploaded files
    """

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


