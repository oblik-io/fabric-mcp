"""Shared utilities for transport integration tests."""

import asyncio
import socket
import subprocess
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx

# Type aliases for better readability
ServerConfig = dict[str, Any]


def find_free_port() -> int:
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@asynccontextmanager
async def run_server(
    config: ServerConfig, transport_type: str
) -> AsyncGenerator[ServerConfig, None]:
    """Context manager to run a server during tests."""
    # Prepare command args based on transport type
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
        cmd_args.extend(["--mcp-path", config.get("mcp_path", "/mcp")])
    elif transport_type == "sse":
        cmd_args.extend(["--sse-path", config.get("sse_path", "/sse")])

    # Start server as subprocess for proper isolation
    with subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as server_process:
        try:
            # Wait for server to start with timeout
            server_url = f"http://{config['host']}:{config['port']}"

            # For transport-specific health checks, use appropriate endpoints
            if transport_type == "http":
                health_url = f"{server_url}{config.get('mcp_path', '/mcp')}"
            elif transport_type == "sse":
                health_url = f"{server_url}{config.get('sse_path', '/sse')}"
            else:
                health_url = server_url

            # Wait for server to be ready
            for _ in range(50):  # 5 second timeout
                # Check if server process died
                if server_process.poll() is not None:
                    stdout, stderr = server_process.communicate(timeout=5)
                    raise RuntimeError(
                        f"Server process died: stdout={stdout}, stderr={stderr}"
                    )

                # Try to connect to server
                try:
                    async with httpx.AsyncClient() as client:
                        if transport_type == "sse":
                            # For SSE endpoints, we just need to check if connection
                            # succeeds. SSE endpoints stream indefinitely, so we use a
                            # very short timeout and expect the connection to succeed
                            # even if we don't read the response
                            try:
                                response = await client.get(
                                    health_url,
                                    timeout=0.5,
                                    headers={"Accept": "text/event-stream"},
                                )
                                # For SSE, 200 with text/event-stream means success
                                if response.status_code == 200:
                                    break
                            except httpx.ReadTimeout:
                                # For SSE, a read timeout after connection is
                                # actually success because SSE endpoints are supposed
                                # to stream indefinitely
                                break
                        else:
                            # For HTTP endpoints, normal response handling
                            response = await client.get(health_url, timeout=1.0)
                            # Any response (even error) means server is up
                            if response.status_code in [200, 307, 404, 405, 406]:
                                break
                except (httpx.ConnectError, httpx.TimeoutException):
                    # Server not ready yet, wait a bit more
                    await asyncio.sleep(0.1)
            else:
                # Server failed to start, get logs
                server_process.terminate()
                stdout, stderr = server_process.communicate(timeout=5)
                raise RuntimeError(
                    f"Server failed to start on {config['host']}:{config['port']}\n"
                    f"stdout: {stdout}\nstderr: {stderr}"
                )

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
