"""Integration tests for the Fabric MCP Server SSE Transport.

These tests verify the SSE transport functionality,
including all MCP tools over SSE and configuration options.
"""

import asyncio
import subprocess
import sys

import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import SSETransport

from tests.shared.transport_test_utils import (
    ServerConfig,
    find_free_port,
    get_expected_tools,
    run_server,
)


@pytest.mark.integration
class TestSSETransport:
    """Integration tests for SSE Transport."""

    @pytest.fixture
    def sse_server_config(self) -> ServerConfig:
        """Configuration for the SSE server."""
        return {
            "host": "127.0.0.1",
            "port": find_free_port(),
            "sse_path": "/sse",
        }

    @pytest.mark.asyncio
    async def test_sse_server_starts_and_responds(
        self, sse_server_config: ServerConfig
    ) -> None:
        """Test that SSE server starts and responds to basic requests."""
        async with run_server(sse_server_config, "sse") as config:
            # Test basic connectivity
            url = f"http://{config['host']}:{config['port']}{config['sse_path']}"

            async with httpx.AsyncClient() as client:
                # For SSE endpoints, we just check connection with streaming
                # Don't wait for response completion as SSE connections are persistent
                async with client.stream("GET", url, timeout=2.0) as response:
                    # SSE endpoint should respond with some status
                    # (could be 200 for valid SSE, 400/406/422 for invalid headers)
                    assert response.status_code in [200, 400, 406, 422]

    @pytest.mark.asyncio
    async def test_mcp_client_connection(self, sse_server_config: ServerConfig) -> None:
        """Test MCP client can connect and list tools."""
        async with run_server(sse_server_config, "sse") as config:
            url = f"http://{config['host']}:{config['port']}{config['sse_path']}"

            # Create MCP client with SSE transport
            transport = SSETransport(url=url)
            client = Client(transport)

            async with client:
                # Test list_tools
                tools = await client.list_tools()
                assert tools is not None
                assert isinstance(tools, list)

                # Verify expected tools are present
                tool_names: list[str] = [
                    tool.name
                    for tool in tools  # type: ignore[misc]
                ]

                expected_tools = get_expected_tools()
                for expected_tool in expected_tools:
                    assert expected_tool in tool_names, (
                        f"Expected tool '{expected_tool}' not found in {tool_names}"
                    )

    @pytest.mark.asyncio
    async def test_fabric_list_patterns_tool(
        self, sse_server_config: ServerConfig
    ) -> None:
        """Test fabric_list_patterns tool over SSE transport."""
        async with run_server(sse_server_config, "sse") as config:
            url = f"http://{config['host']}:{config['port']}{config['sse_path']}"

            transport = SSETransport(url=url)
            client = Client(transport)

            async with client:
                # Call fabric_list_patterns tool
                result = await client.call_tool("fabric_list_patterns", {})

                assert result is not None
                assert isinstance(result, list)

                # Extract text content from MCP response
                assert len(result) > 0
                text_content = result[0].text  # type: ignore[misc]
                assert isinstance(text_content, str)

                # Should return the mock patterns as JSON string
                assert "pattern1" in text_content
                assert "pattern2" in text_content
                assert "pattern3" in text_content

    @pytest.mark.asyncio
    async def test_fabric_get_configuration_tool(
        self, sse_server_config: ServerConfig
    ) -> None:
        """Test fabric_get_configuration tool over SSE transport."""
        async with run_server(sse_server_config, "sse") as config:
            url = f"http://{config['host']}:{config['port']}{config['sse_path']}"

            transport = SSETransport(url=url)
            client = Client(transport)

            async with client:
                # Call fabric_get_configuration tool
                result = await client.call_tool("fabric_get_configuration", {})

                assert result is not None
                assert isinstance(result, list)

                config_text = result[0].text  # type: ignore[misc]
                assert isinstance(config_text, str)
                # Should have redacted sensitive values
                assert "[REDACTED_BY_MCP_SERVER]" in config_text

    @pytest.mark.asyncio
    async def test_custom_sse_endpoint_path(
        self, sse_server_config: ServerConfig
    ) -> None:
        """Test SSE server with custom endpoint path."""
        # Override config with custom path
        config = sse_server_config.copy()
        config["sse_path"] = "/custom-sse"

        async with run_server(config, "sse") as running_config:
            url = (
                f"http://{running_config['host']}:{running_config['port']}"
                f"{running_config['sse_path']}"
            )

            transport = SSETransport(url=url)
            client = Client(transport)

            async with client:
                # Should be able to connect and list tools
                tools = await client.list_tools()
                assert tools is not None
                assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_sse_server_graceful_shutdown(
        self, sse_server_config: ServerConfig
    ) -> None:
        """Test that SSE server shuts down gracefully."""
        server_process = None

        try:
            # Start server manually to test shutdown
            server_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "fabric_mcp.cli",
                    "--transport",
                    "sse",
                    "--host",
                    sse_server_config["host"],
                    "--port",
                    str(sse_server_config["port"]),
                    "--sse-path",
                    sse_server_config["sse_path"],
                    "--log-level",
                    "info",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for server to start
            await asyncio.sleep(0.5)

            # Verify server is running
            assert server_process.poll() is None

            # Send SIGTERM for graceful shutdown
            server_process.terminate()

            # Server should exit gracefully within reasonable time
            try:
                return_code = server_process.wait(timeout=3.0)
                # Return code should be negative (terminated by signal) or 0 (graceful)
                assert return_code in [0, -15], f"Unexpected return code: {return_code}"
            except subprocess.TimeoutExpired:
                pytest.fail("Server did not shut down gracefully within timeout")

        finally:
            if server_process and server_process.poll() is None:
                server_process.kill()
                server_process.wait(timeout=1.0)

    @pytest.mark.asyncio
    async def test_sse_transport_validation_with_invalid_options(
        self,
        sse_server_config: ServerConfig,  # pylint: disable=unused-argument
    ) -> None:
        """Test that invalid SSE transport options are handled properly."""
        # Test with invalid port (should fail to start)
        with subprocess.Popen(
            [
                sys.executable,
                "-m",
                "fabric_mcp.cli",
                "--transport",
                "sse",
                "--host",
                "127.0.0.1",
                "--port",
                "99999",  # Invalid port
                "--sse-path",
                "/sse",
                "--log-level",
                "info",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as server_process:
            # Wait for process to complete (should fail)
            return_code = server_process.wait(timeout=5.0)
            stdout, stderr = server_process.communicate()

            # Should fail to start with invalid port
            assert return_code != 0, (
                f"Expected failure but got success. stdout: {stdout}, stderr: {stderr}"
            )
