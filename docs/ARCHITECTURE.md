# Architecture

## Components

```
CLI (app.py / src/agent.py)
  └─ src/research_agent.py
       ├─ get_config()        env → Config (fails fast, names missing vars)
       ├─ build_agent()       deepagents + ChatNebius + TavilySearch
       ├─ run_research()      invoke agent → extract → format
       ├─ dedupe_sources()    URL dedup, first-seen order, drop URL-less
       ├─ extract_report()    last message wins (objects or dicts)
       └─ format_final_report()  "Deep research report:" + Sources list
```

Both entry points delegate to the same `main()` in
`src/research_agent.py`: `python app.py` (cookbook) and
`python src/agent.py` (template) behave identically.

## Why this shape

- **Lazy heavy imports.** `deepagents` / `langchain-*` are imported inside
  `build_agent()` only. The pure helpers (dedup, formatting, extraction)
  import with just the standard library, so unit tests run fast and
  dependency-free, and a missing dependency produces a clear import error
  at build time rather than at module load.
- **Injectable agent.** `run_research(question, agent=...)` accepts any
  object with an `invoke(state)` method returning `{"messages": [...]}`.
  Tests and the offline demo inject stubs; production injects nothing and
  the real deep agent is built. The agent result may also carry a
  `"sources"` list, which is deduplicated and rendered as the Sources list.
- **Evidence before synthesis.** The synthesis prompt constrains the model
  to the numbered sources and forces an explicit insufficient-evidence
  answer when they do not support one. `format_final_report()` enforces
  the same rule on the output side: empty report + no sources yields the
  insufficient-evidence message, never a bare or invented paragraph.
- **No secrets in code paths.** Keys live only in `os.environ` / `Config`
  attributes and are never printed, logged, or interpolated into prompts.
  `Config.__repr__` masks them. Errors name missing variables, not values.

## Failure modes

| Failure | Behaviour |
|---|---|
| Missing `NEBIUS_API_KEY` / `TAVILY_API_KEY` | Exit 2, stderr names the missing variables |
| Search returns nothing usable | `Deep research report: Insufficient evidence: …`, exit 0 |
| Agent / network exception mid-run | Exit 1, stderr `Error: research run failed: …` |
| Empty final message | Treated as insufficient evidence |

## What is intentionally not here

- No retrieval cache, no reranker, no browser fetching: Tavily's advanced
  search + the model's own reading loop are the retrieval layer, per the
  cookbook. A cache would risk serving stale facts — the opposite of the
  point of this agent.
- No persistent memory between runs: each invocation is one question, one
  report, one exit, matching the container contract (`python app.py` runs
  once and exits zero).
