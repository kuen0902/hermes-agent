#!/Users/bookid/.hermes/.venv/bin/python
import os
import sys

# Ensure scripts directory is in path for imports
sys.path.append(os.path.expanduser("~/.hermes/scripts"))

import fastapi
import uvicorn
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import logging

# Pre-load heavy libraries
import pandas as pd
import duckdb
import sqlite3
import numpy as np

# Import actual pipelines
try:
    from ml.intraday_ml_pipeline import run_intraday_pipeline
    from intraday_risk_monitor import run_risk_monitor
except ImportError as e:
    logging.error(f"Failed to import pipelines: {e}")

app = fastapi.FastAPI(title="Hermes ML Daemon", version="1.0.0")

class PipelineRequest(BaseModel):
    silent: bool = True
    target_date: str = None

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Hermes ML Daemon is running"}

@app.post("/intraday_pipeline")
def trigger_intraday_pipeline(req: PipelineRequest):
    """
    Triggers the intraday ML pipeline.
    Because this is a synchronous `def` (not `async def`), FastAPI runs it in an external threadpool.
    """
    try:
        run_intraday_pipeline(silent=req.silent, target_date=req.target_date)
        return {"status": "success"}
    except Exception as e:
        logging.exception("Error in intraday_pipeline")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/risk_monitor")
def trigger_risk_monitor():
    """
    Triggers the intraday risk monitor.
    """
    try:
        run_risk_monitor()
        return {"status": "success"}
    except Exception as e:
        logging.exception("Error in risk_monitor")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=28888, log_level="info")
