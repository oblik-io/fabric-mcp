"""Fabric MCP server in stdio mode."""

from fabric_mcp.core import FabricMCPServer
from fabric_mcp.utils import Log

LOG_LEVEL = "DEBUG"

log = Log(LOG_LEVEL)
logger = log.logger

logger.info("Starting server with log level %s", LOG_LEVEL)
fabric_mcp = FabricMCPServer(log_level=log.level_name)

mcp = fabric_mcp.mcp
