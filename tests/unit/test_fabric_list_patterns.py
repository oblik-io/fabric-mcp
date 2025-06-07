"""Unit tests for fabric_list_patterns MCP tool."""

import inspect
from typing import Any
from unittest.mock import patch

import pytest
from mcp.shared.exceptions import McpError

from fabric_mcp.core import FabricMCP
from tests.shared.mocking_utils import (
    COMMON_PATTERN_LIST,
    assert_api_client_calls,
    assert_connection_error_test,
    assert_unexpected_error_test,
    create_fabric_api_mock,
)


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
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_successful_response(COMMON_PATTERN_LIST)
            .build()
        )

        # Act
        result = self.fabric_list_patterns()

        # Assert
        assert result == COMMON_PATTERN_LIST
        assert_api_client_calls(mock_api_client, "/patterns/names")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_successful_response_with_empty_list(self, mock_api_client_class: Any):
        """Test successful API response with empty pattern list."""
        # Arrange
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_successful_response([])
            .build()
        )

        # Act
        result = self.fabric_list_patterns()

        # Assert
        assert result == []
        assert_api_client_calls(mock_api_client, "/patterns/names")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_connection_error_handling(self, mock_api_client_class: Any):
        """Test handling of connection errors (httpx.RequestError)."""
        assert_connection_error_test(
            mock_api_client_class,
            self.fabric_list_patterns,
            "Failed to connect to Fabric API",
        )

    @patch("fabric_mcp.core.FabricApiClient")
    def test_http_status_error_handling(self, mock_api_client_class: Any):
        """Test handling of HTTP status errors (httpx.HTTPStatusError)."""
        # Arrange
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_http_status_error(500, "Internal Server Error")
            .build()
        )

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Fabric API error: 500 Internal Server Error" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603
        assert_api_client_calls(mock_api_client, "/patterns/names")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_invalid_response_format_not_list(self, mock_api_client_class: Any):
        """Test handling of invalid response format (not a list)."""
        # Arrange
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_successful_response({"error": "Invalid response"})
            .build()
        )

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Invalid response format from Fabric API: expected list" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603
        assert_api_client_calls(mock_api_client, "/patterns/names")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_mixed_types_in_response_filters_non_strings(
        self, mock_api_client_class: Any
    ):
        """Test handling of mixed types in response - filters out non-strings."""
        # Arrange
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_successful_response(["pattern1", 123, "pattern2", None, "pattern3"])
            .build()
        )

        # Act
        with patch("fabric_mcp.core.logging") as mock_logging:
            result = self.fabric_list_patterns()

        # Assert
        assert result == ["pattern1", "pattern2", "pattern3"]
        # Verify warnings were logged for non-string items
        assert mock_logging.warning.call_count == 2
        assert_api_client_calls(mock_api_client, "/patterns/names")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_json_parsing_error_handling(self, mock_api_client_class: Any):
        """Test handling of JSON parsing errors."""
        # Arrange
        mock_api_client = (
            create_fabric_api_mock(mock_api_client_class)
            .with_json_decode_error("Invalid JSON")
            .build()
        )

        # Act & Assert
        with pytest.raises(McpError) as exc_info:
            self.fabric_list_patterns()

        assert "Unexpected error during retrieving patterns" in str(
            exc_info.value.error.message
        )
        assert exc_info.value.error.code == -32603
        assert_api_client_calls(mock_api_client, "/patterns/names")

    @patch("fabric_mcp.core.FabricApiClient")
    def test_unexpected_exception_handling(self, mock_api_client_class: Any):
        """Test handling of unexpected exceptions."""
        assert_unexpected_error_test(
            mock_api_client_class,
            self.fabric_list_patterns,
            "Unexpected error during retrieving patterns",
        )

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
