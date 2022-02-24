"""Censys Cloud Connectors Version."""
try:  # pragma: no cover
    import importlib_metadata  # pyright: reportMissingImports=false
except ImportError:  # pragma: no cover
    import importlib.metadata as importlib_metadata  # type: ignore

# TODO: Fix this for local development.
__version__: str = importlib_metadata.version("censys.cloud_connectors")
