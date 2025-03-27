import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from app.models import AuditRequest, AuditResponse
from app.audit import audit_logs

# Load environment variables
load_dotenv()

app = FastAPI(title="LLM Risk Auditor API")

@app.post("/audit", response_model=AuditResponse)
async def audit_endpoint(request: AuditRequest):
    try:
        result = audit_logs(request.logs)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
