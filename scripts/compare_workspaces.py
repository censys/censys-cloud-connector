#!/usr/bin/env python3

# This is a script to compare two workspaces' seeds and cloud assets.
# It will print out the differences between the two workspaces.

import argparse
import json
from typing import Optional

from jsondiff import diff

from censys.asm import Seeds
from censys.asm.assets import ObjectStorageAssets


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Compare two workspaces.")
    parser.add_argument(
        "--workspace1",
        type=str,
        required=True,
        help="The first workspace API key to use.",
        dest="workspace1_api_key",
    )
    parser.add_argument(
        "--workspace2",
        type=str,
        required=True,
        help="The second workspace API key to use.",
        dest="workspace2_api_key",
    )
    return parser.parse_args()


def clean_seeds(seeds: list) -> list:
    """Remove the ID and createdOn field from the seeds, as it is not relevant to the comparison.

    Args:
        seeds (list): The list of seeds to clean.

    Returns:
        list: The cleaned list of seeds.
    """
    for seed in seeds:
        if "id" in seed:
            del seed["id"]
        if "createdOn" in seed:
            del seed["createdOn"]
    return seeds


def compare_seeds(workspace_1_api_key: str, workspace_2_api_key: str) -> Optional[dict]:
    """Compare the seeds of two workspaces.

    Args:
        workspace_1_api_key (str): The first workspace API key to use.
        workspace_2_api_key (str): The second workspace API key to use.

    Returns:
        Optional[dict]: The difference between the two workspaces.
    """
    # Create the clients
    seed_client_1 = Seeds(workspace_1_api_key)
    seed_client_2 = Seeds(workspace_2_api_key)

    # Get the seeds from both workspaces
    seeds_1 = seed_client_1.get_seeds()
    seeds_2 = seed_client_2.get_seeds()

    # Remove irrelevant fields
    seeds_1 = clean_seeds(seeds_1)
    seeds_2 = clean_seeds(seeds_2)

    # Sort the seeds by value
    seeds_1 = sorted(seeds_1, key=lambda k: k["value"])
    seeds_2 = sorted(seeds_2, key=lambda k: k["value"])

    # Compare the seeds
    difference = diff(seeds_1, seeds_2, syntax="symmetric")

    # If there is no difference, print a message
    if not difference:
        print("Both workspaces have the same seeds.")
        return None

    # Print the difference
    print(json.dumps(difference, indent=4))

    return difference


def compare_object_storage_assets(
    workspace_1_api_key: str, workspace_2_api_key: str
) -> Optional[dict]:
    """Compare the object storage assets of two workspaces.

    Args:
        workspace_1_api_key (str): The first workspace API key to use.
        workspace_2_api_key (str): The second workspace API key to use.

    Returns:
        Optional[dict]: The difference between the two workspaces.
    """
    # Create the clients
    object_storage_assets_client_1 = ObjectStorageAssets(workspace_1_api_key)
    object_storage_assets_client_2 = ObjectStorageAssets(workspace_2_api_key)

    # Get the object storage assets from both workspaces
    object_storage_assets_1 = list(object_storage_assets_client_1.get_assets())
    object_storage_assets_2 = list(object_storage_assets_client_2.get_assets())

    # Compare the assets
    difference = diff(object_storage_assets_1, object_storage_assets_2)

    # If there is no difference, print a message
    if not difference:
        print("Both workspaces have the same object storage assets.")
        return None

    # Print the difference
    print(json.dumps(difference, indent=4))

    return difference


def main() -> None:
    """The main function."""
    # Parse the arguments
    args = parse_args()

    # Compare the seeds
    compare_seeds(args.workspace1_api_key, args.workspace2_api_key)

    # Compare the object storage assets
    compare_object_storage_assets(args.workspace1_api_key, args.workspace2_api_key)


if __name__ == "__main__":
    main()
