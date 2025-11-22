import os
import io
import sys
import sqlite3
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeout
import builtins

app = FastAPI(title="KidsLearnPython API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.getcwd(), "kidslearn.db")

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn

class RunCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=4000)

class RunCodeResponse(BaseModel):
    output: str
    error: Optional[str] = None
    timed_out: bool = False

class SubmitScoreRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    score: int = Field(..., ge=0, le=100)

class Score(BaseModel):
    name: str
    score: int
    created_at: str

class ScoresResponse(BaseModel):
    scores: List[Score]

# ---------------------
# Safe code execution
# ---------------------

def _run_user_code(code: str) -> tuple[str, Optional[str]]:
    # Hard sandbox: remove dangerous builtins
    safe_builtins = {
        "print": builtins.print,
        "range": builtins.range,
        "len": builtins.len,
        "int": builtins.int,
        "float": builtins.float,
        "str": builtins.str,
        "bool": builtins.bool,
        "list": builtins.list,
        "dict": builtins.dict,
        "set": builtins.set,
        "tuple": builtins.tuple,
        "enumerate": builtins.enumerate,
        "abs": builtins.abs,
        "min": builtins.min,
        "max": builtins.max,
        "sum": builtins.sum,
    }

    # Disallow dunder access and imports in a naive way
    if "__" in code or "import" in code:
        return ("", "Sorry, importing modules or using special names isn't allowed.")

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        # Redirect stdout/stderr
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout, stderr
        # Restricted globals/locals
        sandbox_globals = {"__builtins__": safe_builtins}
        sandbox_locals = {}
        exec(code, sandbox_globals, sandbox_locals)
        out = stdout.getvalue()
        err = stderr.getvalue()
        return (out, err if err else None)
    except Exception as e:
        return (stdout.getvalue(), str(e))
    finally:
        sys.stdout, sys.stderr = old_out, old_err

_executor = ProcessPoolExecutor(max_workers=1)

@app.post("/run-code", response_model=RunCodeResponse)
def run_code(req: RunCodeRequest):
    try:
        future = _executor.submit(_run_user_code, req.code)
        out, err = future.result(timeout=2)  # 2-second timeout
        return RunCodeResponse(output=out or ("No output" if not err else ""), error=err, timed_out=False)
    except FuturesTimeout:
        return RunCodeResponse(output="", error="Your code took too long to finish.", timed_out=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit-score")
def submit_score(req: SubmitScoreRequest):
    try:
        conn = get_db_conn()
        with conn:
            conn.execute("INSERT INTO scores(name, score) VALUES(?, ?)", (req.name.strip(), int(req.score)))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.get("/get-scores", response_model=ScoresResponse)
def get_scores(limit: int = 10):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT name, score, created_at FROM scores ORDER BY score DESC, created_at ASC LIMIT ?", (limit,))
        rows = cur.fetchall()
        scores = [Score(name=r[0], score=r[1], created_at=str(r[2])) for r in rows]
        return ScoresResponse(scores=scores)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.get("/")
def root():
    return {"message": "KidsLearnPython API is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
