# Project Overview — Cognitive Trading Agent

## What This Is

A Polymarket prediction bot whose primary edge is cognitive bias detection. Built on the [Polymarket/agents](https://github.com/Polymarket/agents) open-source framework, extended with a behavioral science layer derived from Kahneman (TFAS), Kahneman/Sibony/Sunstein (Noise), and Cialdini (Influence).

## Core Thesis

Current Polymarket AI bots estimate probabilities by feeding news to an LLM and asking "what's likely?" Nobody models *the mechanism of the market's error*. This bot does. It identifies which cognitive bias is causing retail participants to misprice a contract, quantifies the gap between market price and base-rate-adjusted true probability, and trades against the bias as a maker.

The edge is not speed (latency bots are dead after Polymarket's dynamic fee changes). The edge is not information (everyone has access to the same news). The edge is *understanding why the crowd is systematically wrong on a specific contract at a specific moment*.

## Foundation: Polymarket/agents

This repo was forked from `Polymarket/agents` (MIT license). The foundation provides:

### What We Keep (~70% of the codebase)

| Component | File(s) | Purpose |
|---|---|---|
| Gamma API client | `agents/polymarket/gamma.py` | Market/event discovery and metadata |
| Polymarket API + execution | `agents/polymarket/polymarket.py` | CLOB orderbook, order building, Web3 signing |
| RAG infrastructure | `agents/connectors/chroma.py` | ChromaDB vectorization for context retrieval |
| News connector | `agents/connectors/news.py` | NewsAPI integration for market context |
| Data models | `agents/utils/objects.py` | Pydantic models: SimpleMarket, SimpleEvent, etc. |
| CLI framework | `scripts/python/cli.py` | Typer-based command interface |
| Pipeline structure | `agents/application/trade.py` | Event → Filter → Analyze → Trade flow |

### What We Replace (~30%)

| Component | Current State | Target State |
|---|---|---|
| All LLM prompts | Generic "superforecaster" prompt | Structured bias detection framework with scoring rubrics |
| Filtering logic | RAG similarity to "profitable markets" | Bias-opportunity detector: narrative density, retail flow, base-rate divergence |
| Trade selection | Single LLM call → parse price/size from text | Multi-step: base rate → bias identification → edge calculation → Kelly sizing |
| Model | gpt-3.5-turbo-16k | GPT-5.4 (full-size reasoning for bias detection) |
| Output format | Regex-parsed strings | Structured JSON schemas (Pydantic) |
| Storage | Ephemeral ChromaDB dirs (deleted each run) | Persistent SQLite for predictions, outcomes, calibration |

### What We Add (new components)

| Component | Purpose |
|---|---|
| **Bias Detector** | Core edge: structured LLM evaluation identifying active cognitive biases per market |
| **Base Rate Engine** | Historical frequency estimation for event types |
| **Context Assembler** | Structured signal bundling (orderbook + news + sentiment + base rate) per market |
| **Feedback Loop** | Post-resolution calibration tracking and model improvement |
| **Position Manager** | Active position monitoring with thesis invalidation logic |
| **SQLite persistence** | Local database for predictions, trades, outcomes, P&L |
| **Notifications** | Telegram alerts for trades, position updates, resolved markets |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (main.py / cron)            │
│                                                              │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────────┐  │
│  │ SCANNER  │───>│  CONTEXT  │───>│   BIAS DETECTOR      │  │
│  │          │    │ ASSEMBLER │    │   (THE EDGE)         │  │
│  │ Gamma API│    │           │    │                      │  │
│  │ Filter:  │    │ Orderbook │    │ Base rate estimate   │  │
│  │ narrative│    │ News      │    │ Bias identification  │  │
│  │ density  │    │ Sentiment │    │ True probability     │  │
│  │ liquidity│    │ Base rate │    │ Edge calculation     │  │
│  │ category │    │ Price hx  │    │ Confidence score     │  │
│  └──────────┘    └───────────┘    └──────────┬───────────┘  │
│                                               │              │
│                                    ┌──────────▼───────────┐  │
│                                    │   ORDER MANAGER      │  │
│                                    │                      │  │
│                                    │ Kelly sizing         │  │
│                                    │ Maker-only orders    │  │
│                                    │ Position tracking    │  │
│                                    │ Thesis invalidation  │  │
│                                    └──────────┬───────────┘  │
│                                               │              │
│                                    ┌──────────▼───────────┐  │
│                                    │   FEEDBACK LOOP      │  │
│                                    │                      │  │
│                                    │ Resolution tracking  │  │
│                                    │ Calibration analysis │  │
│                                    │ Bias accuracy audit  │  │
│                                    │ P&L attribution      │  │
│                                    └──────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              SQLite (data/cognitive_trader.db)        │    │
│  │  markets | evaluations | trades | outcomes | config  │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

External APIs:
  - Polymarket Gamma API (market discovery)
  - Polymarket CLOB API (orderbook, orders) via py-clob-client
  - Polygon RPC (Web3 signing) via web3.py
  - OpenAI API (GPT-5.4 for bias detection)
  - NewsAPI (news context)
  - Tavily (web search for contrarian evidence)
```

## Target Markets

The cognitive model has edge on markets where humans form probability estimates from narratives rather than statistics:

- **Event-driven crypto**: Will ETH break $X by date Y, token milestone events
- **Regulatory/political**: SEC decisions, legislative outcomes touching crypto
- **Project-specific**: Launches, partnerships, protocol upgrades
- **Cross-category macro**: Fed decisions, economic indicators with crypto spillover

NOT targeting: 5-min/15-min up/down crypto (pure volatility, no narrative), sports (different bias profile), ultra-low-liquidity markets (<$10K).

## Model and Cost

- **Scanner**: GPT-4.1 Nano ($0.05/$0.20 per M tokens) — lightweight classification
- **Bias Detector**: GPT-5.4 (full-size) — reasoning quality matters for bias identification
- **Estimated monthly cost**: $30–50 at 2–5 trades/day volume
- **Infrastructure cost**: $0 (runs on local PC, SQLite, no cloud)

## Trading Strategy

- **Maker-only**: Zero fees, earns 20% rebate on crypto markets
- **Position sizing**: Fractional Kelly criterion (quarter-Kelly initially)
- **Paper trading first**: 2–4 weeks, 50–100 resolved predictions before live capital
- **Risk management**: Per-position max, total portfolio max, thesis invalidation triggers

## Related Research

The behavioral framework behind this bot is documented in the parallel research project (see `/docs/COGNITIVE_FRAMEWORK.md`):
- TFAS_framework.md — System 1/2, probability overweighting, WYSIATI, substitution
- NOISE_framework.md — Judgment variance, pattern noise, objective ignorance
- INFLUENCE_framework.md — Social proof, commitment/consistency, pre-cognitive triggers
- TRADEABLE_EDGES.md — Bias → instrument mapping methodology
- DISCOVERY_ENGINE.md — Systematic edge discovery process
