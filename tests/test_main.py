import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"name": "ForgeIQ", "status": "running"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_upload_csv_success():
    # Simulate a CSV file
    file_content = b"col1,col2\nval1,val2"
    file_name = "test_data.csv"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, io.BytesIO(file_content), "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["original_filename"] == "test_data.csv"
    assert data["size_bytes"] == len(file_content)
    assert data["filename"].endswith(".csv")

def test_upload_non_csv():
    # Simulate a TXT file
    file_content = b"just some text"
    file_name = "test_data.txt"
    
    response = client.post(
        "/upload",
        files={"file": (file_name, io.BytesIO(file_content), "text/plain")}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are allowed"

def test_upload_no_file():
    response = client.post("/upload")
    
    assert response.status_code == 400
    assert response.json()["detail"] == "No file provided"
