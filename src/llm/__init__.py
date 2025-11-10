"""LLM helper package."""

from .conferences import (
    build_conference_abbreviation_prompt,
    map_conference_to_abbreviation,
)

__all__ = [
    "build_conference_abbreviation_prompt",
    "map_conference_to_abbreviation",
]
