"""Shared utilities for transport integration tests."""

import asyncio
import socket
import subprocess
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from fabric_mcp.core import DEFAULT_MCP_HTTP_PATH, DEFAULT_MCP_SSE_PATH

# Type aliases for better readability
ServerConfig = dict[str, Any]


def find_free_port() -> int:
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _build_server_command(config: ServerConfig, transport_type: str) -> list[str]:
    """Build the command to start the server."""
    cmd_args = [
        sys.executable,
        "-m",
        "fabric_mcp.cli",
        "--transport",
        transport_type,
        "--host",
        config["host"],
        "--port",
        str(config["port"]),
        "--log-level",
        "info",
    ]

    # Add transport-specific arguments
    if transport_type == "http":
        cmd_args.extend(["--mcp-path", config.get("mcp_path", DEFAULT_MCP_HTTP_PATH)])
    elif transport_type == "sse":
        cmd_args.extend(["--sse-path", config.get("sse_path", DEFAULT_MCP_SSE_PATH)])

    return cmd_args


def _get_health_url(config: ServerConfig, transport_type: str) -> str:
    """Get the health check URL for the given transport type."""
    server_url = f"http://{config['host']}:{config['port']}"

    if transport_type == "http":
        return f"{server_url}{config.get('mcp_path', '/mcp')}"
    if transport_type == "sse":
        return f"{server_url}{config.get('sse_path', '/sse')}"
    return server_url


async def _check_sse_endpoint(client: httpx.AsyncClient, health_url: str) -> bool:
    """Check if SSE endpoint is ready."""
    try:
        response = await client.get(
            health_url,
            timeout=0.5,
            headers={"Accept": "text/event-stream"},
        )
        return response.status_code == 200
    except httpx.ReadTimeout:
        # For SSE, a read timeout after connection is success
        return True
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def _check_http_endpoint(client: httpx.AsyncClient, health_url: str) -> bool:
    """Check if HTTP endpoint is ready."""
    try:
        response = await client.get(health_url, timeout=1.0)
        return response.status_code in [200, 307, 404, 405, 406]
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def _wait_for_server_ready(
    config: ServerConfig, transport_type: str, server_process: subprocess.Popen[str]
) -> None:
    """Wait for the server to be ready."""
    health_url = _get_health_url(config, transport_type)

    for _ in range(50):  # 5 second timeout
        # Check if server process died
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate(timeout=5)
            raise RuntimeError(f"Server process died: stdout={stdout}, stderr={stderr}")

        # Try to connect to server
        async with httpx.AsyncClient() as client:
            if transport_type == "sse":
                is_ready = await _check_sse_endpoint(client, health_url)
            else:
                is_ready = await _check_http_endpoint(client, health_url)

            if is_ready:
                return

        await asyncio.sleep(0.1)

    # Server failed to start
    server_process.terminate()
    stdout, stderr = server_process.communicate(timeout=5)
    raise RuntimeError(
        f"Server failed to start on {config['host']}:{config['port']}\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )


@asynccontextmanager
async def run_server(
    config: ServerConfig, transport_type: str
) -> AsyncGenerator[ServerConfig, None]:
    """Context manager to run a server during tests."""
    cmd_args = _build_server_command(config, transport_type)

    # Start server as subprocess for proper isolation
    with subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as server_process:
        try:
            # Wait for server to start
            await _wait_for_server_ready(config, transport_type, server_process)

            yield config
        finally:
            # Clean up server process
            if server_process.poll() is None:
                # Try graceful shutdown first
                server_process.terminate()
                try:
                    server_process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    server_process.kill()
                    server_process.wait(timeout=1.0)


def get_expected_tools() -> list[str]:
    """Get the list of expected Fabric tools."""
    return [
        "fabric_list_patterns",
        "fabric_get_pattern_details",
        "fabric_run_pattern",
        "fabric_list_models",
        "fabric_list_strategies",
        "fabric_get_configuration",
    ]
