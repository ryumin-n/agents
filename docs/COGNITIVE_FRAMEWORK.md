# Cognitive Framework — Behavioral Science for Prediction Market Trading

> This document summarizes the three research layers that produce the trading edge.
> Full frameworks are maintained in the parallel research project.
> This file is the reference for prompt engineering in `agents/application/prompts.py`.

## Architecture: Three Layers of Human Error

```
Layer 1: INTERNAL COGNITION (Thinking, Fast and Slow)
  How individual minds form probability estimates
  → System 1 errors: anchoring, substitution, WYSIATI, probability overweighting

Layer 2: SYSTEMIC ERROR (Noise)
  Why groups of judges produce variable, unreliable estimates
  → Pattern noise, level noise, occasion noise, objective ignorance underestimation

Layer 3: INTERPERSONAL TRANSMISSION (Influence)
  How beliefs spread between people and override individual judgment
  → Social proof cascades, commitment/consistency, authority bias
```

Each layer adds a *different* error mechanism. A prediction market price reflects the aggregate of all three layers operating simultaneously on retail participants.

---

## Layer 1: TFAS — System 1/2 Architecture

### Core Mechanism
Two cognitive systems: System 1 (fast, automatic, always on) generates impressions. System 2 (slow, effortful, lazy) is supposed to check them but usually rubber-stamps whatever System 1 produces. Over 50% of elite university students fail simple logic problems because System 2 doesn't engage.

### Tradeable Mechanisms in Prediction Markets

**Probability Overweighting (TFAS §7.2)**
- People treat 10% probabilities as ~15-20%. They treat 90% as ~75-80%.
- In prediction markets: longshot contracts (5-15¢) are systematically overpriced. Near-certainty contracts (85-95¢) are systematically underpriced.
- Empirical magnitude: 10¢ contracts on Polymarket often have ~3% true probability. That's a 7¢ edge per contract.

**Substitution Heuristic (TFAS §4.1)**
- When faced with a hard question ("What's the probability the SEC approves X?"), System 1 substitutes an easier question ("Can I imagine the SEC approving X?").
- Imagineability ≠ probability. Vivid, narrative-rich outcomes get overpriced because they're easy to imagine.
- Detection signal: market price significantly above historical base rate for similar events + high narrative intensity (many news articles, social media threads).

**WYSIATI — What You See Is All There Is (TFAS §3.3)**
- System 1 builds the best story from available information and ignores what's missing.
- In prediction markets: people bet based on the headline they saw, not on the base rate they didn't look up.
- Detection signal: market price diverges from base rate + recent salient headline in the direction of divergence.

**Anchoring (TFAS §5)**
- First number encountered biases the estimate, even when irrelevant.
- In prediction markets: the price a contract opened at, or a recent price level, anchors subsequent estimates.
- Detection signal: price stuck near a psychologically salient level (round numbers, opening price) despite changed fundamentals.

**Loss Aversion and Prospect Theory (TFAS §8-9)**
- Losses feel 2.25x worse than equivalent gains.
- In prediction markets: people overpay for "insurance" positions (contracts that pay out if bad things happen). Tail-risk contracts are overpriced.

---

## Layer 2: NOISE — Systemic Judgment Variance

### Core Mechanism
All judgment error = Bias² + Noise². Noise (random variability between judges) is as damaging as bias but receives almost no attention. In prediction markets, the "price" is the noisy aggregate of many retail judgments.

### Tradeable Mechanisms

**Pattern Noise (50-80% of system noise)**
- Different bettors weigh the same evidence differently based on their personal weighting schemes. One person overweights the technical analysis, another overweights the news headline, a third overweights an influencer's opinion.
- Result: the market price is a noisy average that doesn't reflect any single calibrated view.
- Detection signal: wide bid-ask spread, high volume but price oscillating without new information.

**Objective Ignorance Underestimation**
- People think they can predict with 75-85% accuracy. Actual ceiling for complex events is ~59%.
- In prediction markets: contracts on inherently unpredictable events (geopolitical, novel crypto regulatory) trade at extreme prices (>80¢ or <20¢) when true probability should be closer to 50/50.
- Detection signal: complex, first-of-its-kind event priced with high confidence (>75¢ or <25¢).

**Occasion Noise**
- The same person makes different judgments depending on mood, fatigue, hunger, time of day, sequence effects.
- In prediction markets: price can shift simply because the active trading cohort changed (US hours vs. Asia hours), not because of new information.
- Detection signal: price moves on no news, correlated with time-of-day or day-of-week patterns.

---

## Layer 3: INFLUENCE — Social Transmission

### Core Mechanism
Individual judgment errors get amplified when beliefs transmit between people. Social proof, authority bias, and commitment/consistency create self-reinforcing loops that push market prices further from truth.

### Tradeable Mechanisms

**Social Proof Cascades**
- When uncertain, people look to what others are doing. In crypto prediction markets, "what others are doing" = crypto Twitter consensus.
- A viral thread saying "BTC will definitely break $200K by June" can move contract prices independent of any fundamental change.
- This is pre-cognitive (Influence framework) — it bypasses even System 1 analysis. People see consensus and follow.
- Detection signal: sudden price move correlated with social media spike, no fundamental news trigger.

**Commitment and Consistency**
- Once people take a position (buy a contract), they become psychologically committed to the thesis. They seek confirming evidence, dismiss disconfirming evidence, and resist updating.
- In prediction markets: "sticky" positions where price doesn't respond to new disconfirming information because holders refuse to sell.
- Detection signal: market price doesn't move despite material counter-evidence. Open interest stays high while news turns against the position.

**Authority Bias**
- Influencer endorsement moves prices independent of evidence quality.
- "Elon tweeted about X" is not evidence of probability, but it moves prediction markets.
- Detection signal: price correlated with authority figure's public statement rather than with underlying fundamentals.

---

## Bias Detection Taxonomy (for prompts.py)

When evaluating a market, the Bias Detector should check for each of these and score presence/magnitude:

| Bias Code | Name | Detection Signal | Typical Direction |
|---|---|---|---|
| `PROB_OVERWEIGHT` | Probability Overweighting | Price at 5-15¢ with base rate < 3% | Longshots overpriced |
| `SUBSTITUTION` | Substitution Heuristic | High narrative intensity + price above base rate | Imaginable outcomes overpriced |
| `WYSIATI` | What You See Is All There Is | Recent headline in direction of price divergence from base rate | Headline-driven overpricing |
| `ANCHORING` | Anchoring | Price near round number or opening price despite changed fundamentals | Sticky price, slow update |
| `SOCIAL_CASCADE` | Social Proof Cascade | Price move correlated with social spike, no fundamental trigger | Consensus-driven overpricing |
| `COMMITMENT` | Commitment/Consistency | Price non-responsive to counter-evidence, high open interest | Resistant to correction |
| `AUTHORITY` | Authority Bias | Price move following influencer statement | Endorsement-driven |
| `NOISE_AGG` | Noisy Aggregate | Wide spread, oscillating price, no new info | Price reflects noise not signal |
| `IGNORANCE_UNDER` | Objective Ignorance Underestimation | Complex/novel event priced with high confidence | False certainty |
| `LOSS_AVERSION` | Loss Aversion / Prospect Theory | Tail-risk or "insurance" contracts overpriced | Downside overpriced |

---

## How This Translates to the Prompt

The bias detection prompt should force the LLM through this evaluation sequence:

1. **What is the base rate?** Historical frequency of this type of event. Force System 2.
2. **What is the market saying?** Current contract price as implied probability.
3. **Is there a gap?** Base rate vs. market price. If gap < 5%, skip — no edge.
4. **If gap exists, which bias explains it?** Walk through the taxonomy above. Require specific evidence for each identified bias.
5. **How confident are we in the bias identification?** Could the market know something we don't? Is there a legitimate reason for the price?
6. **What is the true probability?** Base rate adjusted for any legitimate information the market has.
7. **What is the edge?** True probability minus market price. Size determines position.

This mirrors the churn snapshot prompt's structure: structured signals → evaluation rules → priority tiers → mandatory evidence → output schema.
