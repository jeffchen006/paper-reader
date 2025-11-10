import datetime
import sys
import types
from types import SimpleNamespace

import pytest

if "arxiv" not in sys.modules:
    class _DummyClient:
        def results(self, *_args, **_kwargs):
            return []

    arxiv_stub = types.SimpleNamespace(
        Client=_DummyClient,
        SortCriterion=types.SimpleNamespace(Relevance="relevance"),
        Search=lambda **_kwargs: None,
    )
    sys.modules["arxiv"] = arxiv_stub

if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)

if "langchain_openai" not in sys.modules:
    module = types.ModuleType("langchain_openai")

    class ChatOpenAI:
        def __init__(self, **_kwargs):
            self.response = SimpleNamespace(content="DUMMY")

        def invoke(self, _messages):
            return self.response

    module.ChatOpenAI = ChatOpenAI
    sys.modules["langchain_openai"] = module

if "langchain_anthropic" not in sys.modules:
    module = types.ModuleType("langchain_anthropic")

    class ChatAnthropic:
        def __init__(self, **_kwargs):
            self.response = SimpleNamespace(content="DUMMY")

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

from src.retrievers.arxiv_retriever import ArxivRetriever


def make_result(venue: str) -> SimpleNamespace:
    return SimpleNamespace(
        authors=[SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob")],
        entry_id="http://arxiv.org/abs/1234.5678v1",
        published=datetime.datetime(2024, 1, 1),
        journal_ref=venue,
        comment="",
        title="Sample Title",
        summary="Sample abstract",
        pdf_url="http://arxiv.org/pdf/1234.5678v1",
    )


def test_normalize_paper_uses_llm_mapping(monkeypatch):
    retriever = ArxivRetriever()
    calls = []

    def fake_map(label: str) -> str:
        calls.append(label)
        return "S&P"

    monkeypatch.setattr(
        "src.retrievers.arxiv_retriever.map_conference_to_abbreviation",
        fake_map,
    )

    paper = retriever._normalize_paper(make_result("IEEE Symposium on Security and Privacy 2024"))

    assert paper["conference"] == "S&P"
    assert calls == ["IEEE Symposium on Security and Privacy 2024"]


def test_normalize_paper_fallback_on_llm_error(monkeypatch):
    retriever = ArxivRetriever()

    def failing_map(label: str) -> str:
        raise RuntimeError("LLM failure")

    monkeypatch.setattr(
        "src.retrievers.arxiv_retriever.map_conference_to_abbreviation",
        failing_map,
    )

    paper = retriever._normalize_paper(make_result("IEEE Symposium on Security and Privacy 2024"))

    assert paper["conference"] == "IEEE Symposium on Security and Privacy 2024"
