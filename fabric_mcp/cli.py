"CLI entry point for fabric-mcp."

import argparse
import asyncio
import sys

from .__about__ import __version__
from .server import run_server_stdio


def main():
    "Argument parsing and entrypoint or fabric-mcp CLI."
    parser = argparse.ArgumentParser(
        prog="fabric-mcp",
        description="A Model Context Protocol server for Fabric AI.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit.",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run the server in stdio mode (default).",
    )
    # Add other arguments and subcommands here in the future
    args = parser.parse_args()

    # If no arguments are given (besides --version handled by action='version'),
    # print help for now. Replace this with default behavior later.
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Add main logic based on args here
    if args.stdio:
        try:
            asyncio.run(run_server_stdio())
        except KeyboardInterrupt:
            print("\nServer interrupted by user. Exiting.", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
