"""Small source adapters that emit canonical RailSync records."""

from .json_snapshot import load_json_list
from .resource_context import load_resource_context

ADAPTERS = {"json_list": load_json_list}

__all__ = ["ADAPTERS", "load_json_list", "load_resource_context"]
