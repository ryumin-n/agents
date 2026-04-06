# Cognitive Trading Agent — Claude Code Context

## What Is This Project

A personal Polymarket prediction bot that uses cognitive bias detection as its primary edge. Built on the Polymarket/agents open-source framework (MIT license), extended with a behavioral science layer.

Not a latency arb bot. Not a generic "ask LLM for probability" bot. This bot identifies *when and why the market is wrong* by detecting specific behavioral mechanisms (System 1 overreaction, noise, social proof cascades, availability bias, favorite-longshot bias) and trading against them as a maker.

## Owner

Nik — solo operator. No team, no clients, no service business. Anonymous market participant only. Has meaningful capital to allocate. Full market access: crypto/DeFi/prediction markets globally, US/EU equities via Freedom Finance.

## Technical Background

Nik built a production AI analytics pipeline at Cayosoft (see `docs/PRIOR_ART.md`). The pattern he knows: multi-source data ingestion → signal engineering → structured LLM prompts with detailed rubrics → JSON output → action. That same pattern is the backbone of this bot. Beginner-to-intermediate Python, strong on data architecture and prompt engineering.

## Current State (as of 2026-04-04)

- **Environment**: Python 3.12, venv at `.venv/`, all deps installed (Windows-specific fixes applied — see PROJECT_STATUS.md)
- **Model**: `gpt-5.4-mini` (changed from gpt-3.5-turbo-16k in `agents/application/executor.py:32`)
- **API keys**: `POLYGON_WALLET_PRIVATE_KEY` and `OPENAI_API_KEY` configured as Windows system env vars (not in .env file)
- **Imports**: All verified working. Harmless warnings: `pkg_resources` deprecation (web3), regex escape sequence (executor.py)
- **Priority**: Get pipeline running end-to-end first. Cognitive tuning, bug fixes, base rate engine — all come later. Don't block on strategic concerns.
- **Known non-blocking bugs**: cron.py circular import, duplicate prompts_polymarket(), leftover test functions, infinite retry in trade.py. None prevent a pipeline run.

## Foundation Codebase

This repo is forked from `Polymarket/agents`. Key files from the foundation:

### Keep and Use As-Is
- `agents/polymarket/gamma.py` — GammaMarketClient: market/event discovery via Gamma API
- `agents/polymarket/polymarket.py` — Polymarket class: CLOB orderbook, Web3 signing, order execution
- `agents/connectors/chroma.py` — PolymarketRAG: ChromaDB vectorization pipeline
- `agents/connectors/news.py` — News: NewsAPI integration
- `agents/utils/objects.py` — Pydantic models (SimpleMarket, SimpleEvent, Trade, etc.)
- `scripts/python/cli.py` — Typer CLI framework

### Modify Heavily
- `agents/application/prompts.py` — Replace ALL prompts with cognitive bias framework. This is the most important file in the project.
- `agents/application/executor.py` — Upgrade model to GPT-5.4, replace string parsing with structured JSON, add bias detection pipeline
- `agents/application/trade.py` — Replace RAG-only filtering with narrative-density + bias-opportunity scoring

### Fix Known Issues (deferred — non-blocking for pipeline runs)
- `agents/application/cron.py` — Circular import (only matters if using scheduler)
- `agents/application/prompts.py` — Duplicate method `prompts_polymarket()` (Python uses second def, harmless)
- `agents/polymarket/polymarket.py` — Leftover test functions (dead code, never called)
- `agents/connectors/search.py` — Incomplete Tavily stub (not used by pipeline)

### Add New
- SQLite database layer (evaluations, trades, outcomes, calibration)
- Bias detector module with structured evaluation schemas
- Base rate estimation engine
- Context assembler (orderbook + news + sentiment + base rate per market)
- Feedback loop (resolution tracking, calibration analysis)
- Position manager with thesis invalidation
- Telegram notifications
- Configuration management (settings.py)

## Core Design Principles

1. **Maker-only strategy**: Zero fees, earns 20% rebate on crypto markets. Never compete on speed.
2. **Narrative-rich markets only**: Event-driven crypto, regulatory, macro. NOT 5-min up/down.
3. **GPT-5.4 for bias detection**: Full-size model. The reasoning quality matters for identifying which cognitive bias is active.
4. **Paper trade first**: 50-100 resolved predictions before live capital.
5. **Personal infrastructure**: SQLite, local files, cron/scheduler. No Docker, no cloud, no microservices.
6. **Signal engineering > model sophistication**: Pre-compute structured context before the LLM sees it. Same pattern as the Cayosoft churn pipeline.

## Behavioral Framework Summary

Three research layers produce the trading edge (full details in `docs/COGNITIVE_FRAMEWORK.md`):

1. **TFAS (Thinking, Fast and Slow)** — System 1/2 architecture. Key tradeable mechanisms:
   - Probability overweighting (10% events priced at 15-20%)
   - Substitution heuristic ("can I imagine this?" replaces "what's the frequency?")
   - WYSIATI (What You See Is All There Is): headline-driven betting without base rates
   - Anchoring on recent salient events

2. **NOISE** — Judgment variance. Key tradeable mechanisms:
   - Pattern noise: different retail bettors weigh the same evidence differently → prices reflect noisy aggregate rather than calibrated estimate
   - Objective ignorance underestimation: people think they can predict with 75-85% accuracy when actual ceiling is ~59% for complex events
   - Occasion noise: crowd sentiment shifts based on time-of-day, news cycle position, market fatigue

3. **INFLUENCE** — Social transmission. Key tradeable mechanisms:
   - Social proof cascades: crypto Twitter consensus drives price away from base rate
   - Commitment/consistency: once positioned, traders seek confirming evidence and resist updating
   - Authority bias: influencer endorsement moves contract prices independent of evidence quality

## Connection Map

```
CLI (scripts/python/cli.py)
  └─ Trader (agents/application/trade.py)
      ├─ Polymarket (agents/polymarket/polymarket.py)
      │   ├─ GammaMarketClient (agents/polymarket/gamma.py) → Gamma REST API
      │   ├─ ClobClient (py_clob_client) → CLOB REST API
      │   └─ Web3 (web3.py) → Polygon RPC
      ├─ Executor (agents/application/executor.py)
      │   ├─ Prompter (agents/application/prompts.py) ← REWRITE THIS
      │   ├─ OpenAI GPT-5.4
      │   └─ PolymarketRAG (agents/connectors/chroma.py)
      ├─ News (agents/connectors/news.py) → NewsAPI
      ├─ [NEW] BiasDetector → structured evaluation pipeline
      ├─ [NEW] ContextAssembler → signal bundling per market
      ├─ [NEW] FeedbackLoop → calibration tracking
      └─ [NEW] SQLite → persistent local storage
```

## Important Notes for Code Generation

- The prompt engineering in `agents/application/prompts.py` is the most important file. Treat it with the same care as the churn snapshot prompt in the Cayosoft pipeline.
- When generating LLM prompts, use the same pattern as `usp_AI_Generate_Churn_Snapshots.sql`: structured signal sections, explicit evaluation rules, signal priority tiers, scoring rubrics, mandatory evidence requirements.
- Always use structured JSON output with Pydantic schemas. Never parse LLM output with regex.
- Nik prefers dense, mechanism-focused explanations. Don't over-abstract.
- Reference `PROJECT_STATUS.md` for current implementation state and `NEXT_ACTIONS.md` for prioritized work.
- Reference `docs/COGNITIVE_FRAMEWORK.md` for the behavioral science that drives the bias detection prompts.
- Reference `docs/PRIOR_ART.md` for patterns from the Cayosoft pipeline that should be replicated here.

## Windows Environment Notes

- Platform: Windows 10 Pro, Git Bash shell
- Venv activation: `source .venv/Scripts/activate` (not `bin/activate`)
- Packages removed from requirements.txt for Windows compatibility: `uvloop`, `pysha3`, `eip712-structs`, pinned `chroma-hnswlib`, pinned `chromadb==0.5.5`, pinned `jq==1.7.0`, pinned `langchain-chroma==0.1.2`
- `setuptools` pinned to <81 (web3 uses deprecated `pkg_resources`)
- API keys are Windows system environment variables, not in .env file
