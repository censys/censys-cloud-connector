"""Censys Cloud Connector Main Function."""
import importlib

from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.settings import (
    Settings,
    get_platform_settings_from_file,
)


def main():
    """Main function."""
    settings = Settings()
    settings.platforms = get_platform_settings_from_file(settings.platforms_config_file)
    for platform_name in settings.platforms.keys():
        connector_class = getattr(
            importlib.import_module(f"censys.cloud_connectors.{platform_name}"),
            f"{platform_name.title()}CloudConnector",
        )
        connector: CloudConnector = connector_class(settings)
        connector.scan_all()


if __name__ == "__main__":
    main()
