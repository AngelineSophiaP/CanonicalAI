"""Source adapter abstractions.

Defines the abstract `SourceAdapter` contract for reading input sources
and emitting `ParseResult` objects.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union
import logging

from models.candidate import ParseResult


class SourceAdapter(ABC):
    """Abstract base for all source adapters.

    Implementations should read the underlying file(s) and return a list
    of `ParseResult` objects. Adapters must not raise on individual
    record errors; instead, they should attach warnings to the returned
    `ParseResult` instances.
    """

    def __init__(self, path: Union[str, Path], source_name: str) -> None:
        self.path = Path(path)
        self.source_name = source_name
        self.logger = logging.getLogger(f"candidate_transformer.inputs.{self.__class__.__name__}")

    @abstractmethod
    def read(self) -> List[ParseResult]:
        """Read the source and return a list of ParseResult objects.

        Returns an empty list if the file cannot be read; callers should
        handle the empty case gracefully.
        """

        raise NotImplementedError()
