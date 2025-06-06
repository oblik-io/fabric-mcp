"""Mock Fabric API Server for Integration Testing.

This module provides a minimal FastAPI-based server that mimics the Fabric REST API
for integration testing purposes. It serves the same endpoints that the real Fabric
API would serve, but with predictable mock data.
"""

import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock data that mimics real Fabric API responses
MOCK_PATTERNS = [
    "analyze_claims",
    "create_story",
    "summarize",
    "extract_insights",
    "check_grammar",
    "create_outline",
]

MOCK_PATTERN_DETAILS = {
    "analyze_claims": {
        "name": "analyze_claims",
        "content": "# IDENTITY\nYou are an expert fact checker and truth evaluator...",
        "metadata": {
            "author": "daniel",
            "version": "1.0",
            "tags": ["analysis", "claims", "facts"],
        },
    },
    "create_story": {
        "name": "create_story",
        "content": "# IDENTITY\nYou are an expert storyteller...",
        "metadata": {
            "author": "fabric",
            "version": "1.2",
            "tags": ["creative", "writing", "story"],
        },
    },
    "summarize": {
        "name": "summarize",
        "content": "# IDENTITY\nYou are an expert content summarizer...",
        "metadata": {
            "author": "daniel",
            "version": "2.1",
            "tags": ["summary", "analysis"],
        },
    },
}


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[misc]
    """Application lifespan manager."""
    logger.info("Mock Fabric API server starting up...")
    yield
    logger.info("Mock Fabric API server shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Mock Fabric API",
    description="Mock Fabric REST API server for integration testing",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {"message": "Mock Fabric API Server", "status": "running"}


@app.get("/patterns/names")
async def list_pattern_names():
    """Return list of available pattern names.

    This mimics the real Fabric API endpoint GET /patterns/names
    """
    logger.info("Serving pattern names: %s", MOCK_PATTERNS)
    return MOCK_PATTERNS


@app.get("/patterns/{pattern_name}")
async def get_pattern_details(pattern_name: str):
    """Get details for a specific pattern.

    This mimics the real Fabric API endpoint GET /patterns/{name}
    """
    if pattern_name not in MOCK_PATTERN_DETAILS:
        raise HTTPException(
            status_code=404, detail=f"Pattern '{pattern_name}' not found"
        )

    logger.info("Serving pattern details for: %s", pattern_name)
    return MOCK_PATTERN_DETAILS[pattern_name]


@app.post("/patterns/{pattern_name}/run")
async def run_pattern(pattern_name: str, request_data: dict[str, Any]):
    """Execute a pattern with input text.

    This mimics the real Fabric API endpoint POST /patterns/{name}/run
    """
    if pattern_name not in MOCK_PATTERN_DETAILS:
        raise HTTPException(
            status_code=404, detail=f"Pattern '{pattern_name}' not found"
        )

    input_text = request_data.get("input", "")
    logger.info(
        "Running pattern '%s' with input length: %d", pattern_name, len(input_text)
    )

    # Generate mock response based on pattern
    mock_response = {
        "output_format": "text",
        "output_text": f"Mock {pattern_name} output for input: {input_text[:50]}...",
        "model_used": "gpt-4",
        "tokens_used": len(input_text) + 100,
        "execution_time_ms": 1250,
    }

    return mock_response


@app.exception_handler(Exception)
async def global_exception_handler(_request: Any, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def run_server(host: str = "127.0.0.1", port: int = 8080):
    """Run the mock Fabric API server."""
    logger.info("Starting Mock Fabric API server on %s:%s", host, port)

    # Handle shutdown signals gracefully
    def signal_handler(signum: int, _frame: Any) -> None:  # type: ignore[misc]
        logger.info("Received signal %s, shutting down...", signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Configure uvicorn
    config = uvicorn.Config(
        app=app, host=host, port=port, log_level="info", access_log=True, loop="asyncio"
    )

    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock Fabric API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")

    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
