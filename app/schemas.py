from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class RedFlag(BaseModel):
    category: str = Field(description="e.g. Visual artifact, Emotional manipulation, Urgency, Unverifiable claim, Suspicious link")
    detail: str = Field(description="Plain-language explanation a non-technical person understands")
    severity: Literal["low", "medium", "high"]


class Analysis(BaseModel):
    trust_score: int = Field(ge=0, le=100, description="0 = almost certainly fake/scam, 100 = looks authentic")
    verdict: Literal["Likely Authentic", "Needs Verification", "Suspicious", "Likely Fake/Scam"]
    confidence: Literal["low", "medium", "high"]
    summary: str
    red_flags: List[RedFlag]
    legit_signals: List[str] = Field(description="Reasons the content looks genuine")
    verify_yourself: List[str] = Field(description="Up to 3 concrete checks the user should do, e.g. sender domain, link target")
    claims_to_verify: List[str] = Field(description="Up to 3 short, checkable factual claims found in the content")


class Source(BaseModel):
    title: str
    url: str


class Provenance(BaseModel):
    summary: str
    sources: List[Source] = []
    search_queries: List[str] = []


class ScanResponse(BaseModel):
    analysis: Analysis
    provenance: Optional[Provenance] = None


class ChatTurn(BaseModel):
    role: Literal["user", "model"]
    text: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    scan: ScanResponse
    history: List[ChatTurn] = []


class ChatResponse(BaseModel):
    answer: str
