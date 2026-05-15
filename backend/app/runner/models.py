from enum import Enum
from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class PluginResult(BaseModel):
    command: list[str]
    exit_code: int
    status: CheckStatus
    output: str
    perfdata: str | None = None
    stderr: str | None = None
    duration_seconds: float = Field(ge=0)
    timed_out: bool = False
