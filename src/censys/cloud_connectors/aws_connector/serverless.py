#!/usr/bin/env python3
"""Entrypoint for the AWS Serverless Lambda function."""
import os

from pydantic import BaseSettings, Field

from censys.cloud_connectors.common.cli import main as invoke_cli


class LambdaSettings(BaseSettings):
    """Settings for the Lambda function."""

    providers_files: dict = Field(env="PROVIDERS_SECRETS")


def serverless_scan() -> None:
    """Scan the infrastructure.

    Raises:
        SystemExit: If the scan failed.
    """
    settings = LambdaSettings()

    # Write the providers to a temporary directory (/tmp)
    tmp_dir = "/tmp/providers/"
    secrets_dir = os.path.join(tmp_dir, "secrets")
    os.makedirs(secrets_dir, exist_ok=True)
    for file_name, file_contents in settings.providers_files.items():
        with open(os.path.join(tmp_dir, file_name), "w") as f:
            f.write(file_contents)

    # Update the environment variables
    os.environ.update(
        {
            "SECRETS_DIR": secrets_dir,
            "PROVIDERS_CONFIG_FILE": os.path.join(tmp_dir, "providers.yml"),
        }
    )

    # Invoke the CLI
    try:
        invoke_cli(["scan"])
    except SystemExit as e:
        if e.code != 0:
            raise


if __name__ == "__main__":
    serverless_scan()
