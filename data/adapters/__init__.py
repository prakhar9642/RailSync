"""Small source adapters that emit canonical RailSync records."""

from .json_snapshot import load_json_list

ADAPTERS = {"json_list": load_json_list}

__all__ = ["ADAPTERS", "load_json_list"]
