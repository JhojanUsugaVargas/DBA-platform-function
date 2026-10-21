"""DBA Operation Schemas."""
from typing import List
from pydantic import BaseModel


class CancelSessionRequest(BaseModel):
    spid: str = ""
    reason: str = ""


class HistoricalCpuResponse(BaseModel):
    labels: List[str]
    data: List[int]
    simulated: bool = True
