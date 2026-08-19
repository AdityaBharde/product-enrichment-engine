import os
import uuid
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from app.services.profiler import profile_csv
from app.services.schema_mapper import generate_mapping_report

app = FastAPI(title="ForgeIQ API")

UPLOAD_DIR = os.path.join("data", "uploads")
REPORTS_DIR = os.path.join("data", "reports")

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
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

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
    
    try:
        # Feature 2: Run Profiler
        profile_data, profile_path = profile_csv(file_path)
        
        # Feature 4: Intelligent Input Schema Mapping
        df_columns = pd.read_csv(file_path, nrows=0).columns.tolist()
        mapping_data, mapping_path = generate_mapping_report(df_columns, file_path)
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred during profiling and mapping.")
    
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
        },
        "schema_mapping": {
            "mapping_path": mapping_path,
            "canonical_fields_found": mapping_data["canonical_fields_found"],
            "brand_fields_found": mapping_data["brand_fields_found"],
            "unmapped_fields": mapping_data["unmapped_fields"]
        }
    }