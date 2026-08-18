# ForgeIQ

AI-powered product intelligence system.

## Setup Instructions

1. **Create the virtual environment**:
   ```bash
   python -m venv .venv
   ```

2. **Activate the virtual environment**:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the FastAPI server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing Endpoints

**Test GET /**:
```bash
curl http://127.0.0.1:8000/
```

**Test GET /health**:
```bash
curl http://127.0.0.1:8000/health
```

**Test CSV Upload**:
```bash
curl -X POST -F "file=@path/to/your/file.csv" http://127.0.0.1:8000/upload
```