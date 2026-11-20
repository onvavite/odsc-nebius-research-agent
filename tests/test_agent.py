"""Deterministic tests for the research agent.

Both the model client and the search tool are stubbed: no test here makes
a live API call, needs a key, or touches the network.
Run:  python -m pytest tests/ -v
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.research_agent import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    INSUFFICIENT_EVIDENCE,
    OFFLINE_DEMO_REPORT,
    REPORT_PREFIX,
    Config,
    MissingCredentialsError,
    dedupe_sources,
    extract_report,
    format_final_report,
    format_sources,
    get_config,
    run_offline_demo,
    run_research,
)


class StubAgent:
    """Fake deep agent: returns a canned final message and canned sources."""

    def __init__(self, report, sources):
        self._report = report
        self._sources = sources

    def invoke(self, _state):
        return {
            "messages": [{"role": "assistant", "content": self._report}],
            "sources": self._sources,
        }


SAMPLE_RESULTS = [
    {"title": "Alpha", "url": "https://example.com/a",
     "content": "alpha body", "score": 0.9},
    {"title": "Beta", "url": "https://example.com/b",
     "content": "beta body", "score": 0.8},
    {"title": "Alpha again", "url": "https://example.com/a",
     "content": "duplicate url", "score": 0.7},
    {"title": "No URL", "content": "cannot be cited"},
]


# --- evidence handling -----------------------------------------------------

def test_dedupe_sources_dedupes_by_url_and_keeps_order():
    sources = dedupe_sources(SAMPLE_RESULTS)
    assert [s["url"] for s in sources] == [
        "https://example.com/a", "https://example.com/b"]
    assert sources[0]["title"] == "Alpha"  # first occurrence wins


def test_dedupe_sources_drops_entries_without_url():
    assert dedupe_sources([{"title": "x", "content": "y"}]) == []
    assert dedupe_sources([]) == []
    assert dedupe_sources(None) == []


def test_format_sources_numbers_from_one():
    out = format_sources(dedupe_sources(SAMPLE_RESULTS))
    assert out.splitlines() == [
        "[1] Alpha — https://example.com/a",
        "[2] Beta — https://example.com/b",
    ]


# --- report extraction / formatting ---------------------------------------

def test_extract_report_takes_last_message():
    result = {"messages": [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "first"},
        {"role": "assistant", "content": "final report"},
    ]}
    assert extract_report(result) == "final report"


def test_extract_report_handles_message_objects():
    class Msg:
        content = "object content"
    assert extract_report({"messages": [Msg()]}) == "object content"


def test_extract_report_empty_when_no_messages():
    assert extract_report({}) == ""
    assert extract_report({"messages": []}) == ""
    assert extract_report({"messages": [{"role": "assistant", "content": "  "}]}) == ""


def test_format_final_report_prefix_and_sources():
    out = format_final_report("Answer with a claim [1].",
                              dedupe_sources(SAMPLE_RESULTS))
    assert out.startswith(REPORT_PREFIX)
    assert "[1] Alpha — https://example.com/a" in out
    assert "[2] Beta — https://example.com/b" in out


def test_format_final_report_insufficient_when_nothing_found():
    out = format_final_report("", [])
    assert out.startswith(REPORT_PREFIX)
    assert INSUFFICIENT_EVIDENCE in out


def test_format_final_report_does_not_duplicate_sources_section():
    body = "Answer [1].\n\nSources:\n[1] Alpha — https://example.com/a"
    assert format_final_report(body, dedupe_sources(SAMPLE_RESULTS)).count("Sources:") == 1


# --- full run with a stubbed agent ----------------------------------------

def test_run_research_with_stub_agent_returns_prefixed_cited_report():
    agent = StubAgent("The answer is 42 [1][2].",
                      dedupe_sources(SAMPLE_RESULTS))
    out = run_research("What is the answer?", agent=agent)
    assert out.startswith(REPORT_PREFIX)
    assert "The answer is 42 [1][2]." in out
    assert "[1] Alpha — https://example.com/a" in out


def test_run_research_with_stub_agent_and_no_sources_is_insufficient():
    agent = StubAgent("", [])
    out = run_research("Unanswerable question?", agent=agent)
    assert INSUFFICIENT_EVIDENCE in out


# --- configuration ---------------------------------------------------------

def test_get_config_defaults():
    cfg = get_config({"NEBIUS_API_KEY": "k1", "TAVILY_API_KEY": "k2"})
    assert isinstance(cfg, Config)
    assert cfg.model == DEFAULT_MODEL == "MiniMaxAI/MiniMax-M3"
    assert cfg.base_url == DEFAULT_BASE_URL == "https://api.tokenfactory.nebius.com/v1"


def test_get_config_missing_keys_names_variables_not_values():
    with pytest.raises(MissingCredentialsError) as excinfo:
        get_config({})
    assert "NEBIUS_API_KEY" in str(excinfo.value)
    assert "TAVILY_API_KEY" in str(excinfo.value)
    # a present key's value must never leak into the error
    with pytest.raises(MissingCredentialsError) as excinfo2:
        get_config({"NEBIUS_API_KEY": "secret-value-123"})
    assert "secret-value-123" not in str(excinfo2.value)
    assert "TAVILY_API_KEY" in str(excinfo2.value)


def test_config_repr_never_shows_keys():
    cfg = Config("neb-secret", "tav-secret")
    assert "neb-secret" not in repr(cfg)
    assert "tav-secret" not in repr(cfg)


# --- offline demo / CLI smoke (no live APIs) -------------------------------

def test_offline_demo_report_is_prefixed_and_cited():
    out = run_offline_demo()
    assert out.startswith(REPORT_PREFIX)
    assert "[1]" in out and "[2]" in out
    assert "dev.nebius.com/cookbook/deep-research-agent-tavily" in out
    assert "OFFLINE DEMO" in out
    assert OFFLINE_DEMO_REPORT.split("] ", 1)[1][:40] in out


def _run_cli(args, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("NEBIUS_API_KEY", "TAVILY_API_KEY")}
    if env_extra:
        env.update(env_extra)
    root = os.path.join(os.path.dirname(__file__), "..")
    return subprocess.run(
        [sys.executable, "app.py", *args],
        cwd=root, env=env, capture_output=True, text=True, timeout=120,
    )


def test_cli_offline_demo_exits_zero_and_prints_prefix():
    proc = _run_cli(["--offline-demo"])
    assert proc.returncode == 0
    assert proc.stdout.startswith(REPORT_PREFIX)


def test_cli_without_keys_exits_two_with_clear_error():
    proc = _run_cli(["What is the capital of France?"])
    assert proc.returncode == 2
    assert "NEBIUS_API_KEY" in proc.stderr
    assert "TAVILY_API_KEY" in proc.stderr
