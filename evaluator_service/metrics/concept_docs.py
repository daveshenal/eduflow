from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptDoc:
    """
    Concept lists extracted from one curriculum document.

    ASSUMES:
      Concepts the document uses as prerequisites (reader must already know).

    INTRODUCES:
      Concepts the document explicitly introduces/defines for later use.
    """

    ASSUMES: list[str]
    INTRODUCES: list[str]

