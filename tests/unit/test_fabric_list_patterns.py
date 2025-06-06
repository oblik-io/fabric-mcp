"""Unit tests for fabric_list_patterns MCP tool."""

import inspect
import json
from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest
from mcp.shared.exceptions import McpError

from fabric_mcp.core import FabricMCP


class TestFabricListPatterns:
    """Test cases for the fabric_list_patterns MCP tool."""

    server: FabricMCP
    fabric_list_patterns: Any

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.server = FabricMCP()
        # Get the fabric_list_patterns tool function
        self.fabric_list_patterns = getattr(self.server, "_FabricMCP__tools")[0]

    @patch("fabric_mcp.core.FabricApiClient")
    def test_successful_response_with_multiple_patterns(
        self, mock_api_client_class: Any
    ):
        """Test successful API response with multiple pattern names."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.return_value = ["pattern1", "pattern2", "pattern3"]
        mock_api_client.get.return_value = mock_response

        # Act
        result = self.fabric_list_patterns()

        # Assert
        assert result == ["pattern1", "pattern2", "pattern3"]
        mock_api_client.get.assert_called_once_with("/patterns/names")
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_successful_response_with_empty_list(self, mock_api_client_class: Any):
        """Test successful API response with empty pattern list."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_api_client.get.return_value = mock_response

        # Act
        result = self.fabric_list_patterns()

        # Assert
        assert result == []
        mock_api_client.get.assert_called_once_with("/patterns/names")
        mock_api_client.close.assert_called_once()

    @patch("fabric_mcp.core.FabricApiClient")
    def test_connection_error_handling(self, mock_api_client_class: Any):
        """Test handling of connection errors (httpx.RequestError)."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        connection_error = httpx.RequestError("Connection failed")
        mock_api_client.get.side_effect = connection_error

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Failed to connect to Fabric API" in str(exc_info.value.error.message)
        assert exc_info.value.error.code == -32603

    @patch("fabric_mcp.core.FabricApiClient")
    def test_http_status_error_handling(self, mock_api_client_class: Any):
        """Test handling of HTTP status errors (httpx.HTTPStatusError)."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"

        http_error = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        )
        mock_api_client.get.side_effect = http_error

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Fabric API error: 500 Internal Server Error" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603

    @patch("fabric_mcp.core.FabricApiClient")
    def test_invalid_response_format_not_list(self, mock_api_client_class: Any):
        """Test handling of invalid response format (not a list)."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid response"}
        mock_api_client.get.return_value = mock_response

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Invalid response format from Fabric API: expected list" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603

    @patch("fabric_mcp.core.FabricApiClient")
    def test_mixed_types_in_response_filters_non_strings(
        self, mock_api_client_class: Any
    ):
        """Test handling of mixed types in response - filters out non-strings."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.return_value = [
            "pattern1",
            123,
            "pattern2",
            None,
            "pattern3",
        ]
        mock_api_client.get.return_value = mock_response

        # Act
        with patch("fabric_mcp.core.logging") as mock_logging:
            result = self.fabric_list_patterns()

        # Assert
        assert result == ["pattern1", "pattern2", "pattern3"]
        # Verify warnings were logged for non-string items
        assert mock_logging.warning.call_count == 2

    @patch("fabric_mcp.core.FabricApiClient")
    def test_json_parsing_error_handling(self, mock_api_client_class: Any):
        """Test handling of JSON parsing errors."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_api_client.get.return_value = mock_response

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Unexpected error retrieving patterns" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603

    @patch("fabric_mcp.core.FabricApiClient")
    def test_unexpected_exception_handling(self, mock_api_client_class: Any):
        """Test handling of unexpected exceptions."""
        # Arrange
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        mock_api_client.get.side_effect = ValueError("Unexpected error")

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Unexpected error retrieving patterns" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603

    def test_tool_signature_and_return_type(self):
        """Test that the tool has the correct signature and return type annotation."""
        # Get the function signature
        sig = inspect.signature(self.fabric_list_patterns)

        # Verify no parameters
        assert len(sig.parameters) == 0

        # Verify return type annotation
        assert sig.return_annotation == list[str]

    def test_tool_docstring(self):
        """Test that the tool has appropriate documentation."""
        assert self.fabric_list_patterns.__doc__ is not None
        assert "available fabric patterns" in self.fabric_list_patterns.__doc__.lower()
