"""
Data structures for Model Context Protocol (MCP) messages.
Based on https://modelcontextprotocol.io/specification/2025-03-26
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# Based on MCP Specification 2025-03-26
# https://modelcontextprotocol.io/specification/2025-03-26


class MCPRequest(BaseModel):
    """Base model for an MCP request."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None


class MCPResponseResult(BaseModel):
    """Base model for a successful MCP response result."""

    # Specific results will inherit from this


class MCPErrorData(BaseModel):
    """Optional data field for MCP errors."""

    # Define specific error data structures as needed


class MCPError(BaseModel):
    """Structure for an MCP error response."""

    code: int
    message: str
    data: Optional[MCPErrorData] = None


class MCPResponse(BaseModel):
    """Base model for an MCP response."""

    jsonrpc: Literal["2.0"] = "2.0"
    result: Optional[MCPResponseResult] = None
    error: Optional[MCPError] = None
    id: Union[str, int, None]  # Must match the request ID


# --- Specific Method Payloads ---


# list_tools
class MCPToolParameter(BaseModel):
    """Describes a parameter for an MCP tool."""

    name: str
    description: str
    type: str  # e.g., "string", "number", "boolean", "object", "array"
    required: bool = False
    # Add other JSON schema properties if needed (e.g., enum, properties for object)


class MCPToolDefinition(BaseModel):
    """Describes a tool available via MCP."""

    name: str
    description: str
    parameters: List[MCPToolParameter] = Field(default_factory=list)
    # Add information about return type if needed


class MCPListToolsResponse(MCPResponseResult):
    """Result structure for the list_tools method."""

    tools: List[MCPToolDefinition]


# TODO: Add structures for other methods as they are implemented
# e.g., fabric_run_pattern, fabric_list_patterns etc.
