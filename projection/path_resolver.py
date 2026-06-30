"""Path-based value resolution for candidate projection."""
from __future__ import annotations

from typing import Any, Sequence
import re


class PathResolver:
    """Resolve simple dotted paths against nested dictionaries and lists.

    Supported forms include:
    - full_name
    - emails[0]
    - skills[].name
    - experience[0].company
    """

    def __init__(self, path: str):
        self.path = path.strip()
        if not self.path:
            raise ValueError("path cannot be empty")

    def resolve(self, data: Any, on_missing: str = "error") -> Any:
        if on_missing not in {"error", "null", "omit"}:
            raise ValueError(f"unsupported on_missing policy: {on_missing}")

        try:
            return self._resolve_path(data, self.path.split("."))
        except KeyError:
            return self._handle_missing(on_missing)
        except IndexError:
            return self._handle_missing(on_missing)
        except TypeError:
            return self._handle_missing(on_missing)
        except ValueError:
            return self._handle_missing(on_missing)

    def _resolve_path(self, current: Any, segments: Sequence[str]) -> Any:
        if not segments:
            return current

        match = re.fullmatch(r"([A-Za-z0-9_]+)(?:\[(\d+|\*|)\])?", segments[0])
        if not match:
            raise ValueError(f"unsupported path segment: {segments[0]}")

        name = match.group(1)
        bracket = match.group(2)

        if isinstance(current, dict):
            if name not in current:
                raise KeyError(name)
            child = current[name]
        elif hasattr(current, name):
            child = getattr(current, name)
        else:
            raise TypeError("object access requires a dictionary or object attribute")

        if bracket in {"*", ""}:
            if not isinstance(child, list):
                raise TypeError("wildcard access requires a list")
            if not child:
                return []
            if len(segments) == 1:
                return child
            return [self._resolve_path(item, list(segments[1:])) for item in child]

        if bracket is not None:
            if not isinstance(child, list):
                raise TypeError("index access requires a list")
            index = int(bracket)
            if index >= len(child):
                raise IndexError(index)
            return self._resolve_path(child[index], list(segments[1:]))

        return self._resolve_path(child, list(segments[1:]))

    def _handle_missing(self, on_missing: str) -> Any:
        if on_missing == "error":
            raise KeyError(self.path)
        return None
