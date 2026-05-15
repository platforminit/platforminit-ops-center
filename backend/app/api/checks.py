from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.runner.nagios import run_nagios_plugin
from app.runner.models import PluginResult

ALLOWED_PREFIX = "/usr/lib/nagios/plugins/"


class RunCheckRequest(BaseModel):
    command: list[str]
    timeout_seconds: int = Field(default=10, ge=1, le=30)

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("command must contain at least 1 element")

        if len(v) > 20:
            raise ValueError("command must contain at most 20 elements")

        for i, element in enumerate(v):
            if not element:
                raise ValueError(f"command[{i}] must be non-empty")
            if len(element) > 512:
                raise ValueError(f"command[{i}] exceeds maximum length of 512")

        executable = v[0]
        if not executable.startswith(ALLOWED_PREFIX):
            raise ValueError(
                f"command[0] must be an absolute path under {ALLOWED_PREFIX}"
            )

        return v


class RunCheckResponse(BaseModel):
    result: PluginResult


def run_check(payload: RunCheckRequest) -> RunCheckResponse:
    result = run_nagios_plugin(
        command=payload.command,
        timeout_seconds=payload.timeout_seconds,
    )
    return RunCheckResponse(result=result)
