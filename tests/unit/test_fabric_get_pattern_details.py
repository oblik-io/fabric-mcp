"""Unit tests for fabric_get_pattern_details tool."""

import json
import os
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from mcp.shared.exceptions import McpError

from fabric_mcp.core import FabricMCP
from tests.shared.mocking_utils import (
    assert_api_client_calls,
    assert_connection_error_test,
    assert_unexpected_error_test,
    create_fabric_api_mock,
)


class TestFabricGetPatternDetails:
    """Test suite for fabric_get_pattern_details tool."""

    @pytest.fixture
    def server(self) -> FabricMCP:
        """Create a FabricMCP server instance for testing."""
        return FabricMCP(log_level="DEBUG")

    @pytest.fixture
    def get_pattern_details_tool(
        self, server: FabricMCP
    ) -> Callable[[str], dict[str, str]]:
        """Get the fabric_get_pattern_details tool function."""
        tools: list[Callable[..., Any]] = getattr(server, "_FabricMCP__tools")
        return tools[1]  # fabric_get_pattern_details is the second tool

    @patch("fabric_mcp.core.FabricApiClient")
    def test_successful_pattern_details_retrieval(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test successful retrieval of pattern details."""
        # Arrange
        custom_pattern_data = {
            "Name": "summarize",
            "Description": "Create a concise summary",
            "Pattern": "# IDENTITY\nYou are an expert summarizer...",
        }
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_successful_response(custom_pattern_data)
            .build()
        )

        # Act
        result = get_pattern_details_tool("summarize")

        # Assert
        assert isinstance(result, dict)
        assert result["name"] == "summarize"
        assert result["description"] == "Create a concise summary"
        assert result["system_prompt"] == "# IDENTITY\nYou are an expert summarizer..."

        assert_api_client_calls(mock_api_client, "/patterns/summarize")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_successful_pattern_details_with_empty_description(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test successful retrieval when description is empty."""
        # Arrange
        custom_pattern_data = {
            "Name": "test_pattern",
            "Description": "",  # Empty description
            "Pattern": "# Test pattern content",
        }
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_successful_response(custom_pattern_data)
            .build()
        )

        # Act
        result = get_pattern_details_tool("test_pattern")

        # Assert
        assert result["name"] == "test_pattern"
        assert result["description"] == ""
        assert result["system_prompt"] == "# Test pattern content"
        assert_api_client_calls(mock_api_client, "/patterns/test_pattern")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_pattern_not_found_500_error(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test pattern not found (500 error with file not found message)."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.status_code = 500
        home_dir = os.environ.get("HOME", "/Users/testuser")
        mock_response.text = (
            f"open {home_dir}/.config/fabric/patterns/nonexistent/system.md: "
            "no such file or directory"
        )
        mock_response.reason_phrase = "Internal Server Error"

        http_error = httpx.HTTPStatusError(
            "Server error '500 Internal Server Error'",
            request=Mock(),
            response=mock_response,
        )
        mock_api_client.get.side_effect = http_error

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            get_pattern_details_tool("nonexistent")

        assert exc_info.value.error.code == -32602  # Invalid params
        assert "Pattern 'nonexistent' not found" in str(exc_info.value.error.message)
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_other_500_error(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test other 500 errors that are not pattern not found."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error - database connection failed"
        mock_response.reason_phrase = "Internal Server Error"

        http_error = httpx.HTTPStatusError(
            "Server error '500 Internal Server Error'",
            request=Mock(),
            response=mock_response,
        )
        mock_api_client.get.side_effect = http_error

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            get_pattern_details_tool("test_pattern")

        assert exc_info.value.error.code == -32603  # Internal error
        assert "Fabric API internal error" in str(exc_info.value.error.message)
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_http_4xx_error(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test HTTP 4xx errors."""
        # Arrange
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_http_status_error(403, "Forbidden")
            .build()
        )

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            get_pattern_details_tool("test_pattern")

        assert exc_info.value.error.code == -32603  # Internal error
        assert "Fabric API error: 403 Forbidden" in str(exc_info.value.error.message)
        assert_api_client_calls(mock_api_client, "/patterns/test_pattern")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_connection_error(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test connection errors."""
        assert_connection_error_test(
            mock_api_client_class,
            lambda: get_pattern_details_tool("test_pattern"),
            "Failed to connect to Fabric API",
        )

    @patch("fabric_mcp.core.FabricApiClient")
    def test_malformed_json_response(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test handling of malformed JSON response."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_api_client.get.return_value = mock_response

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            get_pattern_details_tool("test_pattern")

        assert exc_info.value.error.code == -32603  # Internal error
        assert "Unexpected error during retrieving pattern details" in str(
            exc_info.value.error.message
        )
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_missing_required_fields_in_response(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test handling when required fields are missing from response."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.return_value = {
            # Missing "Name", "Description", "Pattern" fields
            "SomeOtherField": "value"
        }
        mock_api_client.get.return_value = mock_response

        # Act
        result = get_pattern_details_tool("test_pattern")

        # Assert - should handle missing fields gracefully with defaults
        assert result["name"] == ""
        assert result["description"] == ""
        assert result["system_prompt"] == ""
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_api_client_close_called_on_success(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test that API client is properly closed on successful execution."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.return_value = {
            "Name": "test",
            "Description": "test desc",
            "Pattern": "test pattern",
        }
        mock_api_client.get.return_value = mock_response

        # Act
        get_pattern_details_tool("test_pattern")

        # Assert
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_api_client_close_called_on_exception(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test that API client is properly closed even when exceptions occur."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_api_client.get.side_effect = httpx.RequestError("Connection failed")

        # Act & Assert
        with pytest.raises(McpError):
            get_pattern_details_tool("test_pattern")

        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_unexpected_exception_handling(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test handling of unexpected exceptions."""
        assert_unexpected_error_test(
            mock_api_client_class,
            lambda: get_pattern_details_tool("test_pattern"),
            "Unexpected error during retrieving pattern details",
        )

    @patch("fabric_mcp.core.FabricApiClient")
    def test_response_transformation_format(
        self,
        mock_api_client_class: MagicMock,
        get_pattern_details_tool: Callable[[str], dict[str, str]],
    ):
        """Test that response is properly transformed to expected MCP format."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        fabric_api_response = {
            "Name": "youtube_summary",
            "Description": "",
            "Pattern": "# IDENTITY and PURPOSE\n\nYou are an AI assistant...",
        }

        mock_response = Mock()
        mock_response.json.return_value = fabric_api_response
        mock_api_client.get.return_value = mock_response

        # Act
        result = get_pattern_details_tool("youtube_summary")

        # Assert - verify exact transformation
        expected_result = {
            "name": "youtube_summary",
            "description": "",
            "system_prompt": "# IDENTITY and PURPOSE\n\nYou are an AI assistant...",
        }
        assert result == expected_result

        # Ensure return type is correct
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
