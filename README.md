KidsLearnPython Backend

Overview
KidsLearnPython is a simple, safe API that powers a friendly website for teaching Python to kids ages 8–14. It provides:
- Safe code execution with a strict sandbox and a 2-second timeout
- Quiz score storage and retrieval using SQLite
- CORS enabled for easy local development

Tech
- FastAPI + Uvicorn
- SQLite (file: kidslearn.db)

Run locally
1) Create and activate a virtual environment (recommended)
2) Install dependencies:
   pip install -r requirements.txt
3) Start the API server:
   python main.py
4) The API will be available at:
   http://localhost:8000

Environment
- PORT: optional (defaults to 8000). Example:
  PORT=8001 python main.py

API Endpoints
- POST /run-code
  Body: { "code": "print('Hello')" }
  Runs code in a limited sandbox. Imports and special names are blocked. Timeout: 2s.

- POST /submit-score
  Body: { "name": "Mia", "score": 75 }
  Saves a score to SQLite.

- GET /get-scores?limit=10
  Returns the top scores.

Notes on safety
- The runner disallows imports and access to special names ("__").
- Only a small set of safe built-ins is exposed (print, range, len, int, float, str, bool, list, dict, set, tuple, enumerate, abs, min, max, sum).
- Execution is isolated in a separate process with a 2-second timeout.

Project files
- main.py: FastAPI app with endpoints and sandboxed execution
- requirements.txt: Python dependencies
- kidslearn.db: Created automatically on first write
