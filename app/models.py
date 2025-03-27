from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class PromptLogEntry(BaseModel):
    user: str
    prompt: str
    tokens: int
    model: str = "gpt-3.5-turbo"
    timestamp: Optional[str] = None

class LogRiskAssessment(BaseModel):
    risk_level: str  # "High", "Medium", or "Low"
    reason: str

class AuditRequest(BaseModel):
    logs: List[PromptLogEntry]

class AuditResponse(BaseModel):
    summary: str
    risk_status: str = "Safe"  # "Safe", "Moderate", "High-Risk"
    flags: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    log_assessments: Dict[int, LogRiskAssessment] = Field(default_factory=dict)
