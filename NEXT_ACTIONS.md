# Next Actions — Prioritized Implementation Steps

> Priority order matters. Each step builds on the previous one.

## STEP 1: Environment Setup and Foundation Fixes
**Goal:** Get the existing codebase running on your PC. Fix known bugs.

**Status: MOSTLY COMPLETE (2026-04-04)**

- [x] Create Python 3.12 venv at `.venv/`
- [x] Install dependencies (with Windows-specific fixes — see PROJECT_STATUS.md for details)
- [x] API keys: `POLYGON_WALLET_PRIVATE_KEY` and `OPENAI_API_KEY` set as Windows system env vars
- [x] Model upgraded to `gpt-5.4-mini` in `agents/application/executor.py`
- [x] All imports verified working
- [ ] First pipeline dry run: `python -m scripts.python.cli run-autonomous-trader`
- [ ] `NEWSAPI_API_KEY` — set later (not used by core pipeline)
- [ ] `TAVILY_API_KEY` — set later (search.py is a stub)

**Bug fixes — deferred (non-blocking for simple runs):**
- [ ] Fix `agents/application/cron.py` circular import (only matters for scheduler)
- [ ] Fix `agents/application/prompts.py` duplicate `prompts_polymarket()` (Python uses second def)
- [ ] Remove test functions from `agents/polymarket/polymarket.py` (dead code)
- [ ] Implement Tavily connector in `agents/connectors/search.py` (stub, not called)

**Deliverable:** Pipeline runs end-to-end: fetch markets → filter → LLM analyze → trade suggestion (no execution).

---

## STEP 2: SQLite Persistence Layer
**Goal:** Replace ephemeral ChromaDB-only storage with persistent local database.

- [ ] Create `agents/storage/database.py` with SQLite schema:
  - `markets` — cached market metadata (id, question, category, prices, volume, last_updated)
  - `evaluations` — every bias detection run (market_id, timestamp, base_rate, biases_detected, true_probability, edge, confidence, raw_llm_response)
  - `trades` — placed orders (market_id, evaluation_id, side, price, size, status, fill_time)
  - `outcomes` — resolved markets (market_id, actual_outcome, our_prediction, our_trade_pnl)
  - `config` — runtime settings (paper_mode, max_position_size, kelly_fraction, etc.)
- [ ] Create `agents/storage/models.py` with Pydantic schemas for all tables
- [ ] Wire database into existing pipeline (replace `clear_local_dbs()` pattern in trade.py)

**Deliverable:** All evaluations and trade decisions persist across runs.

---

## STEP 3: Market Scanner with Narrative Filtering
**Goal:** Replace generic RAG filtering with bias-opportunity detection.

- [ ] Create `agents/application/scanner.py`:
  - Fetch all active events/markets from Gamma API
  - Filter for target categories: crypto events, regulatory, macro, project-specific
  - Score each market on "narrative density": text length of description, number of related news articles, social media mention count, time to resolution
  - Score on "bias opportunity": price at extreme (favorite-longshot zone), high retail volume, recent narrative shift, divergence from category base rates
  - Return ranked list of markets worth deep evaluation
- [ ] Integrate with existing `Executor.get_polymarket_llm()` for initial filtering
- [ ] Use GPT-4.1 Nano for scanner (cheap, fast) — add model selection to config

**Deliverable:** Running the scanner produces a ranked list of 10-30 markets with bias opportunity scores.

---

## STEP 4: Context Assembler
**Goal:** Build structured signal bundles per market (equivalent of churn snapshot's @AccountData).

- [ ] Create `agents/application/context_assembler.py`:
  - **Market metadata**: question, description, current prices, volume, time to resolution, category
  - **Orderbook state**: bid/ask depth, spread, recent trade sizes (retail vs. institutional signal)
  - **News context**: Top 3-5 relevant articles via NewsAPI + Tavily search, summarized
  - **Social sentiment**: Basic web search for crypto Twitter/Reddit mentions, narrative direction
  - **Base rate data**: Historical frequency of similar events (manually seeded initially, automated later)
  - **Price history**: Contract price trajectory since creation (trending, mean-reverting, or stale)
- [ ] Output: structured dict/Pydantic model that becomes the LLM input
- [ ] Store assembled context in SQLite for audit trail

**Deliverable:** Each market evaluation has a structured context bundle with all signal dimensions.

---

## STEP 5: Bias Detection Prompts — THE CRITICAL STEP
**Goal:** Rewrite `agents/application/prompts.py` with the cognitive framework.

- [ ] Create the main bias detection prompt following the pattern of `usp_AI_Generate_Churn_Snapshots`:
  - **Section 1: Structured signals** — pre-computed metrics the LLM evaluates (like engagement signals, champion health, etc. in the churn prompt)
  - **Section 2: Evaluation rules** — explicit rubric for scoring (like the SIGNAL PRIORITY tiers in churn)
  - **Section 3: Bias identification taxonomy** — the model must identify which specific bias from the framework:
    - `Availability_Bias` — recent salient event inflating probability
    - `Social_Proof_Cascade` — crypto Twitter consensus driving price
    - `Favorite_Longshot_Bias` — extreme contracts overpriced relative to base rate
    - `Substitution_Heuristic` — "can I imagine this?" replacing "what's the frequency?"
    - `WYSIATI` — headline-driven betting, no base rate calculation
    - `Anchoring` — price stuck near a recent salient number
    - `Commitment_Consistency` — positioned traders resisting update
    - `Noise_Aggregate` — price reflects noisy average rather than calibrated estimate
  - **Section 4: Output schema** — structured JSON:
    ```json
    {
      "base_rate_estimate": 0.15,
      "market_price": 0.35,
      "biases_detected": [
        {
          "bias_type": "Social_Proof_Cascade",
          "direction": "OVERPRICED",
          "magnitude": "HIGH",
          "evidence": "...",
          "confidence": 0.7
        }
      ],
      "true_probability_estimate": 0.18,
      "edge": 0.17,
      "recommended_action": "SELL",
      "recommended_price": 0.30,
      "overall_confidence": 0.65,
      "reasoning": "..."
    }
    ```
  - **Section 5: Narrative quality rules** — same as churn prompt's mandatory rules: must include specific evidence, must tell a story not just report numbers, no generic advice

- [ ] Create `agents/application/schemas.py` with Pydantic models matching the output schema
- [ ] Wire into Executor with `response_format: { "type": "json_object" }` and GPT-5.4

**Deliverable:** The bias detector produces structured, evidence-backed assessments for each market.

---

## STEP 6: Paper Trading Pipeline
**Goal:** Run the full pipeline end-to-end without placing real orders. Collect calibration data.

- [ ] Create `main.py` orchestrator that runs: Scanner → Context Assembler → Bias Detector → Log to SQLite
- [ ] Add paper trade mode flag in config (default: ON)
- [ ] Create `agents/feedback/resolution_tracker.py`:
  - Poll Polymarket for resolved markets
  - Match against our evaluations
  - Record actual outcome vs. our prediction
- [ ] Create `agents/feedback/calibration.py`:
  - Brier score calculation
  - Calibration plot (predicted probability vs. actual frequency)
  - Bias detection accuracy (which bias calls were correct?)
  - Win rate analysis (would our trades have been profitable?)
- [ ] Set up cron/scheduler to run pipeline every 15-30 minutes
- [ ] Telegram notifications for: new evaluation logged, market resolved, daily summary

**Deliverable:** Pipeline runs autonomously, collecting 3-5 evaluations/day. After 2-4 weeks, you have 50-100 data points for calibration analysis.

---

## STEP 7: Go Live
**Goal:** Place real orders based on validated model.

- [ ] Review calibration data from paper trading phase
- [ ] Decision gate: Is Brier score < 0.25? Is bias detection accuracy > 50%? Is simulated win rate > 55%?
- [ ] If yes: switch paper_mode to OFF
- [ ] Implement order manager:
  - Maker-only limit orders via `polymarket.execute_order()`
  - Fractional Kelly sizing (start at quarter-Kelly)
  - Per-position max (configurable, e.g. $500)
  - Portfolio max (configurable, e.g. $5000)
- [ ] Position monitoring:
  - Thesis invalidation: if new information contradicts the bias thesis, close position
  - Price-based stops: if market moves significantly against us
  - Time-based: close if market hasn't moved and resolution is approaching
- [ ] P&L tracking and attribution in SQLite

**Deliverable:** Live trading with real capital, risk-managed, with full audit trail.

---

## Future Enhancements (Post-MVP)

- [ ] Historical base rate database (automated, not manually seeded)
- [ ] Social sentiment API integration (Twitter/Reddit beyond basic search)
- [ ] Streamlit dashboard for real-time visibility
- [ ] Multi-model ensemble (run GPT-5.4 + Claude Sonnet, compare)
- [ ] Orderbook flow analysis (detect retail vs. bot order patterns)
- [ ] Expand to non-crypto event markets where behavioral model applies
- [ ] Automated prompt refinement based on calibration feedback
