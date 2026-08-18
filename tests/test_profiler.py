import io
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_profiler_logic_success():
    # Synthetic CSV with duplicates, missing values, and placeholders
    csv_content = (
        "id,brand,desc\n"
        "1,Bosch,Drill\n"
        "2,-- Unbranded --,Saw\n"
        "3,,Hammer\n"
        "1,Bosch,Drill\n" # Duplicate row
    ).encode("utf-8")
    
    response = client.post(
        "/upload",
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify summary returned in API
    profile_summary = data["profile"]
    assert profile_summary["rows"] == 4
    assert profile_summary["column_count"] == 3
    assert profile_summary["duplicate_rows"] == 1
    
    # Verify the JSON file was actually created on disk
    assert os.path.exists(profile_summary["profile_path"])

def test_profiler_empty_csv():
    # Headers only, no data
    csv_content = b"id,brand,desc\n"
    
    response = client.post(
        "/upload",
        files={"file": ("empty.csv", io.BytesIO(csv_content), "text/csv")}
    )
    
    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()

def test_profiler_invalid_csv():
    csv_content = b"This is just a random text file string without columns."
    
    response = client.post(
        "/upload",
        files={"file": ("invalid.csv", io.BytesIO(csv_content), "text/csv")}
    )
    
    assert response.status_code in [200, 422]