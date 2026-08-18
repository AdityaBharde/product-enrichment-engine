import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from app.services.profiler import profile_csv

app = FastAPI(title="ForgeIQ API")

UPLOAD_DIR = os.path.join("data", "uploads")
REPORTS_DIR = os.path.join("data", "reports")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"name": "ForgeIQ", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_csv(file: UploadFile = File(None)):
    # 16. Error Handling - Invalid input
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Save safely
    unique_filename = f"{uuid.uuid4().hex}.csv"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        size_bytes = 0
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
                size_bytes += len(chunk)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # 15. Integrate with Upload API
    try:
        profile_data, profile_path = profile_csv(file_path)
    except ValueError as e:
        # e.g., pandas couldn't parse it, or it was completely empty
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Unexpected error (do not leak stack trace)
        raise HTTPException(status_code=500, detail="An error occurred during profiling.")
    
    return {
        "status": "success",
        "filename": unique_filename,
        "original_filename": file.filename,
        "size_bytes": size_bytes,
        "profile": {
            "rows": profile_data["dataset"]["rows"],
            "column_count": profile_data["dataset"]["column_count"],
            "duplicate_rows": profile_data["dataset"]["duplicate_rows"],
            "profile_path": profile_path
        }
    }