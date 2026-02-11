from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class FactState(str, Enum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"

class FactSource(str, Enum):
    USER = "user"
    DOCUMENT = "document"
    INFERENCE = "inference"

class Fact(BaseModel):
    name: str
    value: str  # Changed from FactState to str to allow descriptive values (e.g., "3 months")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: FactSource = FactSource.USER
    reason: Optional[str] = None

class FactUpdate(BaseModel):
    name: str
    value: str # Relaxed constraint
    confidence: float = 1.0
    source: FactSource = FactSource.USER
    reason: Optional[str] = None
