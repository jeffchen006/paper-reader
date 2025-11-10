"""Conference-related helpers for LLM abbreviation prompts."""

from __future__ import annotations

import sys
from pathlib import Path
import re
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_conference_llm_config
from src.llm.client import LLMClient

EXAMPLE_MAPPINGS = [
    ("ACM Conference on Computer and Communications Security", "CCS"),
    ("IEEE Symposium on Security and Privacy", "S&P"),
    ("USENIX Security Symposium", "USENIX Security"),
    ("Network and Distributed System Security Symposium", "NDSS"),
    ("International Conference on Software Engineering", "ICSE"),
    ("ACM SIGSOFT Symposium on the Foundations of Software Engineering", "FSE"),
    ("ACM SIGSOFT International Symposium on Software Testing and Analysis", "ISSTA"),
    ("International Conference on Automated Software Engineering", "ASE"),
    ("ACM SIGPLAN Conference on Programming Language Design and Implementation", "PLDI"),
    ("ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages", "POPL"),
    ("ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications", "OOPSLA"),
    ("ACM Symposium on Operating Systems Principles", "SOSP"),
    ("USENIX Symposium on Operating Systems Design and Implementation", "OSDI"),
    ("Conference on Neural Information Processing Systems", "NeurIPS"),
    ("International Conference on Machine Learning", "ICML"),
    ("International Conference on Learning Representations", "ICLR"),
]


def build_conference_abbreviation_prompt(conference_name: str) -> str:
    """Craft a prompt asking an LLM to return the canonical abbreviation."""
    if not conference_name:
        raise ValueError("conference_name must be provided")

    examples_text = "\n".join(
        f'- "{long_name}" -> "{abbreviation}"' for long_name, abbreviation in EXAMPLE_MAPPINGS
    )

    return (
        "You are an expert academic assistant. Convert each long-form conference or journal "
        "name into the short official abbreviation. Respond with the abbreviation only.\n\n"
        "Examples:\n"
        f"{examples_text}\n\n"
        f'Conference or Journal: "{conference_name}"\n'
        "Abbreviation:"
    )


def map_conference_to_abbreviation(
    conference_name: str,
    llm_client: Optional[LLMClient] = None,
) -> str:
    """Send a prompt to the configured LLM and return its abbreviation."""
    prompt = build_conference_abbreviation_prompt(conference_name)

    if llm_client is None:
        llm_config = get_conference_llm_config()
        llm_client = LLMClient.from_config(llm_config, temperature=0.0)

    raw_response = llm_client.complete(prompt)
    return _normalize_llm_response(raw_response)


def _normalize_llm_response(response: str) -> str:
    """Reduce the LLM output to a clean abbreviation token."""
    if not response:
        return ""

    # Strip quotes, whitespace, punctuation, and take the first alphanumeric token.
    cleaned = response.strip().strip('"\'.')
    first_line = cleaned.splitlines()[0].strip()
    match = re.search(r"[A-Za-z0-9][A-Za-z0-9 &+/.-]*", first_line)
    return match.group(0).upper() if match else first_line.upper()


def _run_test_cases(test_cases: Iterable[str]):
    """Utility to run sample lookups against the live LLM."""
    for idx, name in enumerate(test_cases, start=1):
        try:
            abbreviation = map_conference_to_abbreviation(name)
            print(f"{idx}. {name} -> {abbreviation}")
        except Exception as exc:
            print(f"{idx}. {name} -> ERROR: {exc}")
        print("-" * 60)


def main():
    """Manual smoke tests for live LLM abbreviation lookups."""
    cases = [
        "IEEE Symposium on Security and Privacy",
        "International Conference on Software Engineering",
        "ACM SIGPLAN Conference on Programming Language Design and Implementation",
        "USENIX Symposium on Operating Systems Design and Implementation",
        "Conference on Neural Information Processing Systems",
        "International Conference on Learning Representations",
    ]
    _run_test_cases(cases)


if __name__ == "__main__":
    main()
