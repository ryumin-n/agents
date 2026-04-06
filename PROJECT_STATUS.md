# Project Status — Cognitive Trading Agent

> Last updated: 2026-04-04

## Current Phase: ENVIRONMENT READY

The repo contains the cloned Polymarket/agents framework. Environment is set up and imports verified. Model upgraded to gpt-5.4-mini. Ready for first pipeline run.

## What Exists (from Polymarket/agents)

### Working Infrastructure
- [x] Gamma API client for market/event discovery (`agents/polymarket/gamma.py`)
- [x] Polymarket CLOB integration with order building and Web3 signing (`agents/polymarket/polymarket.py`)
- [x] ChromaDB RAG pipeline for context vectorization (`agents/connectors/chroma.py`)
- [x] NewsAPI connector (`agents/connectors/news.py`)
- [x] Pydantic data models for markets, events, trades (`agents/utils/objects.py`)
- [x] CLI framework with Typer (`scripts/python/cli.py`)
- [x] Basic pipeline: fetch events → RAG filter → LLM analyze → trade signal (`agents/application/trade.py`)
- [x] `.env.example` with required API keys template

### Known Issues in Foundation Code
- `agents/application/cron.py` — Circular import (`from scheduler import Scheduler` then `class Scheduler`)
- `agents/application/prompts.py` — `prompts_polymarket()` defined twice with different signatures
- `agents/polymarket/polymarket.py` — Leftover test functions (test(), gamma(), main()) polluting module
- `agents/application/trade.py` — Infinite retry loop in `one_best_trade()` without backoff
- `agents/connectors/search.py` — Tavily connector is an incomplete stub
- Token estimation uses crude `len(text) / 4` instead of tiktoken
- Trade execution is commented out (by design — requires manual uncommenting)

## What Needs to Be Built

### Phase 1: Core Infrastructure (Weeks 1-2)
- [x] Python venv + dependencies (Windows-compatible)
- [x] API keys configured (Polymarket wallet + OpenAI)
- [x] Upgrade from gpt-3.5-turbo-16k to gpt-5.4-mini in executor
- [ ] First successful pipeline dry run (fetch → filter → analyze → trade suggestion)
- [ ] SQLite database schema (markets, evaluations, trades, outcomes, config)
- [ ] Configuration management (settings.py, .env integration)
- [ ] Logging infrastructure
- [ ] Fix foundation code issues (when they block progress)
- [ ] Replace string-parsed LLM outputs with structured JSON (Pydantic schemas)
- [ ] Basic Telegram notification integration

### Phase 2: Cognitive Model (Weeks 2-4) — THE CRITICAL PATH
- [ ] Bias detection prompt architecture (`agents/application/prompts.py` rewrite)
- [ ] Base rate estimation module
- [ ] Context assembler (structured signal bundling per market)
- [ ] Market scanner with narrative-density filtering
- [ ] Evaluation schema: base rate, active biases, true probability, edge, confidence
- [ ] SQLite persistence for all evaluations

### Phase 3: Paper Trading (Weeks 4-6)
- [ ] Full pipeline running end-to-end: scan → assemble → detect → log
- [ ] Paper trade mode (log predictions without placing orders)
- [ ] Resolution tracker (check if markets resolved, record outcomes)
- [ ] Calibration analysis (are 70% predictions hitting 70%?)
- [ ] Bias accuracy audit (which bias detections were correct?)
- [ ] Collect 50-100 resolved predictions

### Phase 4: Live Trading (Weeks 6-8)
- [ ] Order manager with maker-only limit orders
- [ ] Kelly criterion position sizing (quarter-Kelly)
- [ ] Position monitoring and thesis invalidation
- [ ] P&L tracking and attribution
- [ ] Risk limits (per-position max, portfolio max)

### Phase 5: Iteration (Ongoing)
- [ ] Prompt refinement based on calibration data
- [ ] Expand to additional market categories
- [ ] Social sentiment signal integration
- [ ] Historical base rate database
- [ ] Dashboard (Streamlit or Flask) for visibility

## Key Metrics to Track

| Metric | Target | Measurement |
|---|---|---|
| Calibration | Brier score < 0.20 | Predicted probability vs. outcome |
| Bias detection accuracy | > 60% | Did identified bias explain the mispricing? |
| Edge identification | > 55% win rate on trades | Trades where our probability was closer to truth than market |
| P&L | Positive after fees/rebates | Net returns including maker rebates |
| Volume | 2-5 new positions/day | Evaluations that pass conviction threshold |

## Environment Setup (Completed 2026-04-04)

- [x] Python 3.12 venv created at `.venv/`
- [x] Dependencies installed with Windows-specific fixes:
  - Removed `uvloop` (Unix-only, doesn't build on Windows)
  - Removed `pysha3` (C compilation fails without MSVC; `pycryptodome` covers keccak)
  - Removed pinned `chroma-hnswlib==0.7.6` and `chromadb==0.5.5` (no Windows wheel); installed `chromadb==1.5.5` (pure Python)
  - Removed `eip712-structs==1.1.0` (pulls pysha3); `poly_eip712_structs` covers the need
  - Upgraded `jq` to 1.11.0 (1.7.0 had no Windows wheel)
  - Upgraded `langchain-chroma` to 1.1.0 (works with new chromadb)
  - Downgraded `setuptools` to <81 (`web3==6.11.0` uses deprecated `pkg_resources`)
- [x] Model switched from `gpt-3.5-turbo-16k` to `gpt-5.4-mini` in `agents/application/executor.py`
- [x] All imports verified working (Gamma, Chroma, Executor, Prompter, Polymarket)
- [x] `POLYGON_WALLET_PRIVATE_KEY` and `OPENAI_API_KEY` configured as Windows system env vars
- [ ] `NEWSAPI_API_KEY` — not yet set (not needed for core pipeline)
- [ ] `TAVILY_API_KEY` — not yet set (search.py is a stub anyway)
- [ ] Telegram bot token — future

## Known Version Conflicts (Non-blocking)

- `langchain-chroma 1.1.0` wants `langchain-core>=1.1.3`, installed `0.2.26` — works at runtime
- `pkg_resources` deprecation warning from `web3` — harmless

## Design Decisions (2026-04-04)

- **Get it running first, cognitive tuning later.** Priority is end-to-end pipeline, not bias detection sophistication.
- **Known bugs are non-blocking** — cron.py circular import, duplicate prompts, leftover test functions, infinite retry. None prevent a simple pipeline run. Fix when they get in the way.
- **Base rate engine, maker-only liquidity, adversarial dynamics** — all deferred. Not preconditions.
- **Paper trading gate threshold** — decide on the go, not a hard precondition.
- **Model choice (gpt-5.4-mini)** — pragmatic, can switch later.
