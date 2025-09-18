"""
CLI Main Entry Point

Main entry point for the FastAPI Microservices SDK CLI.
"""

import sys
from typing import List, Optional

from .framework import create_cli


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    cli = create_cli()
    return cli.run(argv)


if __name__ == "__main__":
    sys.exit(main())