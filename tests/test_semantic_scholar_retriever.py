import sys
import types

import pytest

if "requests" not in sys.modules:
    sys.modules["requests"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)

if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)

if "langchain_openai" not in sys.modules:
    module = types.ModuleType("langchain_openai")

    class ChatOpenAI:
        def __init__(self, **_kwargs):
            self.response = types.SimpleNamespace(content="DUMMY")

        def invoke(self, _messages):
            return self.response

    module.ChatOpenAI = ChatOpenAI
    sys.modules["langchain_openai"] = module

if "langchain_anthropic" not in sys.modules:
    module = types.ModuleType("langchain_anthropic")

    class ChatAnthropic:
        def __init__(self, **_kwargs):
            self.response = types.SimpleNamespace(content="DUMMY")

        def invoke(self, _messages):
            return self.response

    module.ChatAnthropic = ChatAnthropic
    sys.modules["langchain_anthropic"] = module

if "langchain_core.messages" not in sys.modules:
    core_module = types.ModuleType("langchain_core")
    messages_module = types.ModuleType("langchain_core.messages")

    class HumanMessage:
        def __init__(self, content):
            self.content = content

    messages_module.HumanMessage = HumanMessage
    sys.modules["langchain_core"] = core_module
    sys.modules["langchain_core.messages"] = messages_module
    setattr(core_module, "messages", messages_module)

from src.retrievers.semantic_scholar import SemanticScholarRetriever


def make_paper(venue: str):
    return {
        "paperId": "abc123",
        "title": "Sample Title",
        "abstract": "Sample abstract",
        "authors": [{"name": "Alice"}],
        "year": 2024,
        "venue": venue,
        "journal": None,
        "citationCount": 10,
        "url": "https://example.com",
        "openAccessPdf": {"url": "https://example.com/pdf"},
    }


def test_normalize_paper_uses_llm_mapping(monkeypatch):
    calls = []

    def fake_map(label: str) -> str:
        calls.append(label)
        return "S&P"

    monkeypatch.setattr(
        "src.retrievers.semantic_scholar.map_conference_to_abbreviation",
        fake_map,
    )

    paper = SemanticScholarRetriever._normalize_paper(make_paper("IEEE Symposium on Security and Privacy"))

    assert paper["conference"] == "S&P"
    assert calls == ["IEEE Symposium on Security and Privacy"]


def test_normalize_paper_fallback_on_error(monkeypatch):
    def failing_map(label: str) -> str:
        raise RuntimeError("LLM failure")

    monkeypatch.setattr(
        "src.retrievers.semantic_scholar.map_conference_to_abbreviation",
        failing_map,
    )

    paper = SemanticScholarRetriever._normalize_paper(make_paper("IEEE Symposium on Security and Privacy"))

    assert paper["conference"] == "IEEE Symposium on Security and Privacy"
