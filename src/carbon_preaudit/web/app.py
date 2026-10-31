"""FastAPI application entry point."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="carbon-preaudit")


class HealthResponse(BaseModel):
    """Response body of the health endpoint."""

    status: str


@app.get("/health")
def health() -> HealthResponse:
    """Report that the service is up."""
    return HealthResponse(status="ok")
