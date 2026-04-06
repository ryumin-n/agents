# Prior Art — Patterns from the Cayosoft Churn Pipeline

> This documents the production AI pipeline Nik built at Cayosoft (PulseCenter).
> The patterns here should be replicated in this trading bot.
> Source: E:\Cayosoft\AI analytics agent project\Repo\Dashboards

## What PulseCenter Is

An AI-powered customer health analytics platform that ingests data from Salesforce, Zendesk, Gong, and Maxio, runs structured LLM analysis on each customer account, and outputs churn risk scores with evidence. Deployed in production, running on Azure Data Factory with Azure SQL and Azure OpenAI (GPT-5.4-mini).

## Architecture Pattern (Replicate This)

```
Multi-source ingestion → Signal pre-computation → Structured LLM prompt → JSON output → Action

PulseCenter:
  Salesforce + Zendesk + Gong + Maxio
    → vw_Churn_Risk_AI_Feed (pre-computed metrics per account)
    → usp_AI_Generate_Churn_Snapshots (structured prompt with rubric)
    → JSON: {Risk_Score, Risk_Level, Summary, Evidence, Drivers}
    → Insert into CHURN_RISK_SNAPSHOT__c → Sync to Salesforce

Trading Bot:
  Polymarket + NewsAPI + Social Sentiment + Base Rates
    → Context bundle per market (pre-computed signals)
    → Bias detection prompt (structured prompt with rubric)
    → JSON: {base_rate, biases, true_probability, edge, action}
    → Insert into SQLite evaluations → Place maker order
```

The key insight: **the LLM is not doing the analysis from scratch. It's evaluating pre-computed signals against a structured rubric.** The signal engineering happens before the LLM call. The LLM's job is judgment, not data gathering.

## Prompt Engineering Pattern (Critical to Replicate)

The churn snapshot prompt (`usp_AI_Generate_Churn_Snapshots.sql`) is ~2,000 words of structured evaluation rules. Key patterns:

### 1. Separate Structured Signals from Raw Context
The prompt has two parts:
- **STRUCTURED RISK METRICS** — pre-computed numbers (engagement quality, champion health, coverage, support, keywords). The LLM uses these to guide scoring.
- **INTERACTION CONTEXT** — raw JSON of recent tickets, calls, tasks. The LLM reads the actual words.

**Trading bot equivalent:**
- Structured signals: base rate, orderbook depth, price history slope, social mention count, narrative recency
- Raw context: news article summaries, social media excerpts, market description

### 2. Explicit Evaluation Rules with Priority Tiers
The churn prompt defines 5 tiers:
- CRITICAL (Score 8-10): explicit cancellation intent, complete silence, active outage
- HIGH (Score 6-8): any TWO of [champion lost, negative Gong trend, silence > 30d, etc.]
- ELEVATED (Score 5-7): any ONE of [champion lost, competitors in Gong, etc.]
- MODERATE (Score 3-5): negative trend, no CS rep, coverage gap
- STABILIZERS (reduce by up to 2): recent renewal, positive calls, active contacts

**Trading bot equivalent:**
- HIGH CONFIDENCE EDGE (trade aggressively): base rate divergence > 15% AND two or more biases detected AND high narrative density
- MODERATE EDGE (trade conservatively): base rate divergence > 10% AND one bias with strong evidence
- WEAK EDGE (log but don't trade): divergence 5-10%, bias detection ambiguous
- NO EDGE (skip): divergence < 5% OR legitimate information explains the price

### 3. Mandatory Evidence Requirements
The churn prompt requires:
- AI_Key_Evidence must contain at least 3 direct quotes from interactions
- Driver_Evidence must include at least one verbatim quote
- Recommended_Actions must name specific people, open issues, or topics
- "Generic advice like 'schedule a meeting' is not acceptable"

**Trading bot equivalent:**
- Bias evidence must reference specific news headlines, social media patterns, or price data points
- Base rate estimate must cite the source or reasoning
- "Generic reasoning like 'the market seems overpriced' is not acceptable"

### 4. Counter-Signal Awareness
The churn prompt warns:
- "High interaction volume does NOT automatically mean low risk"
- "Zero Gong calls alone is NOT a risk signal"
- "If Manual Risk Flag is true, verify with telemetry"

**Trading bot equivalent:**
- "High social media activity does NOT automatically mean mispricing"
- "Price divergence from your estimate does NOT mean the market is wrong — it might know something you don't"
- "If base rate data is sparse, reduce confidence accordingly"

### 5. Structured JSON Output
The churn prompt requires exact JSON schema: `{Snapshot: {Risk_Score, Risk_Level, ...}, Drivers: [{Driver_Name, Driver_Category, Driver_Score, ...}]}`. Parsed with `JSON_VALUE()` and `OPENJSON()`.

**Trading bot equivalent:** Use `response_format: {"type": "json_object"}` with GPT-5.4 and validate against Pydantic schemas.

## Two-Pass LLM Pattern (from ChatFunction)

The chat function (`ChatFunction/function_app.py`) uses a two-pass pattern:
1. **Pass 1:** LLM generates SQL from natural language question (with schema context as system prompt)
2. **Pass 2:** LLM formats raw query results into executive prose

**Trading bot equivalent:**
1. **Pass 1 (Scanner):** Cheap model (GPT-4.1 Nano) evaluates market list, flags candidates
2. **Pass 2 (Bias Detector):** Full model (GPT-5.4) does deep evaluation with structured context

## Batch Processing with Error Isolation

The churn pipeline processes accounts in a cursor loop with TRY...CATCH per account. If one API call times out or fails, it logs the error and moves to the next account without killing the batch.

**Trading bot equivalent:** Process each market evaluation independently. If one LLM call fails, log it and move to the next market. Never let a single failure stop the pipeline.

## Signal Engineering Examples

From `vw_Churn_Risk_AI_Feed` and `vw_Account_Risk_Metrics`, the churn pipeline pre-computes:
- Days_Since_Last_Interaction (across all channels)
- Gong_Positive_Pct / Gong_Negative_Pct (sentiment trending)
- Contact_Concentration_Pct (single-point-of-failure risk)
- Champion_Lost_Flag (binary risk indicator)
- Max_Outbound_Gap_Days (coverage hole detection)
- Competitor_Mentions_180d, Cancellation_Mentions_180d (keyword risk)
- Negative_Sentiment_Tickets_90d (support health)

**Trading bot equivalents to pre-compute:**
- base_rate_estimate (historical frequency of similar events)
- price_vs_base_rate_divergence (current market price minus base rate)
- narrative_intensity_score (news article count + social mention count in last 24h)
- narrative_recency (hours since last major article/thread)
- orderbook_imbalance (bid depth vs. ask depth)
- price_trend_slope (direction and speed of recent price movement)
- social_consensus_direction (is crypto Twitter bullish or bearish on this outcome?)
- influencer_mention_flag (has a major figure commented?)
- time_to_resolution (days/hours until market resolves)
- volume_concentration (are a few wallets driving most of the volume?)
