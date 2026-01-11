# scripts/create_ledger.py
import argparse
import asyncio
import os
import sys
from typing import Any, Dict

# Adjust path to import from src
# This assumes the script is run from the project root or scripts directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.infrastructure.config import load_config
from src.infrastructure.services.ledger.client import LedgerManager
from src.infrastructure.settings import ENVIRONMENT
from src.types.blnk.dtos import CreateLedgerRequest
from src.types.error import Error  # For error handling


async def main():
    parser = argparse.ArgumentParser(
        description="Create a new ledger in the Blnk service."
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="dev",
        help="Environment to use (dev, staging, prod). Default is 'dev'.",
    )
    parser.add_argument(
        "--name", type=str, required=True, help="Name of the ledger to create."
    )
    parser.add_argument(
        "--description",
        type=str,
        default="A new ledger",
        help="Description of the ledger.",
    )
    parser.add_argument(
        "--application",
        type=str,
        default="YourApp",
        help="Application name for ledger metadata.",
    )
    # Add more arguments for metadata if needed

    args = parser.parse_args()

    try:
        env = ENVIRONMENT(args.environment)
    except ValueError:
        print(
            f"Error: Invalid environment '{args.environment}'. Must be one of {list(e.value for e in ENVIRONMENT)}"
        )
        sys.exit(1)

    # Load configuration based on environment
    app_config = load_config()

    # Instantiate LedgerManager
    # LedgerManager expects LedgderServiceConfig
    ledger_manager = LedgerManager(config=app_config.ledger)

    # Construct CreateLedgerRequest
    ledger_metadata: Dict[str, Any] = {
        "description": args.description,
        "application": args.application,
    }
    create_request = CreateLedgerRequest(name=args.name, meta_data=ledger_metadata)

    # Call create_ledger
    print(
        f"Attempting to create ledger '{args.name}' in {args.environment} environment..."
    )
    ledger_response, err = await ledger_manager.create_ledger(create_request)

    if err:
        print(f"Error creating ledger: {err.message}")
        sys.exit(1)

    print(
        f"Successfully created ledger '{ledger_response.name}' with ID: {ledger_response.ledger_id}"
    )
    print(f"Full response: {ledger_response.model_dump_json(indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
