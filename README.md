# OCI AWR Agentic AI Sizing Advisor — Progress Overview

## Overview

The OCI AWR Agentic AI Sizing Advisor is an **agentic AI system** that transforms Oracle AWR reports into **actionable performance insights and OCI sizing guidance**.

The system progresses from raw AWR parsing to deterministic analysis, and ultimately to **recommendations, narrative insights, and infrastructure decisions**. It enforces **analytical honesty**: no fabricated metrics, no synthetic distributions, and no misleading visualizations.

It is designed to replace manual AWR interpretation with a **repeatable, explainable, and automation-ready workflow**.

---

## Why This Matters

Traditional AWR analysis relies on manual interpretation, requiring deep expertise and significant time investment.

This system introduces:
- Deterministic analysis → consistent outcomes  
- Structured metrics → machine-readable insights  
- Automated recommendations → immediate actionability  
- AI narrative layer → interpretation, prioritization, and decision support  

Bridging the gap between **performance engineering and business decision-making**.

---

## Design Principles

- Deterministic analysis is the source of truth
- AI augments, but does not replace, evidence-based findings
- Dual AI providers enable flexibility and OCI alignment
- AI is stateless by design; state and history are introduced explicitly via ADB
- Historical context (ADB) enables trend-based decisions
- No synthetic data: distributions are only shown when real multi-sample data exists
- Scalar metrics are never expanded into artificial distributions
- Visualization reflects data fidelity, not presentation convenience

---

## Requirements

- Python 3.10+
- pip

---

## Setup

### Install runtime dependencies
```bash
pip install -r requirements.txt
```

### Install development dependencies (optional)
```bash
pip install -r requirements-dev.txt
```

### Run the analysis
```bash
python scripts/run_analysis.py
```

---

## Architecture

The system follows a layered, deterministic-first approach:

```text
AWR Report(s) (.out)
(single run or batch input)
        ↓
Parsing Layer
        ↓
Structured Metrics
        ↓
Issue Detection
        ↓
Recommendation Engine
        ↓
────────────────────────────────────────────
Deterministic Truth Layer (Source of Truth)
────────────────────────────────────────────
        ↓
AI Narrative Layer (Grounded, Stateless)
   → OpenAI (advanced reasoning)
   → OCI Generative AI (Oracle-native AI)
        ↓
────────────────────────────────────────────
Context & State Layer
────────────────────────────────────────────
        ↓
ADB (History / Trends)
        ↓
Agentic Decision Layer (Stateful, Context-Aware)
        ↓
OCI Sizing Guidance
```
---

## Database Schema

The project includes an Autonomous Database schema under:

```text
dbschema/
```

This schema supports the **stateful layer** of the system and enables:
- Multi-AWR ingestion and replay
- Historical trend analysis
- Metric, wait event, and top SQL fact storage
- JSON-based raw and parsed payload persistence
- Feature vectors and semantic embeddings
- Scoring, recommendation, action, and outcome tracking
- Feedback loops for model retraining

The schema is designed to align with the agentic workflow:

```text
AWR → Parse → Metrics → Feature Vector → Score → Recommendation → Action → Outcome → Retrain
```

This allows the system to evolve from stateless analysis to a **stateful, learning system**.

This schema is the foundation for the **Context & State Layer (ADB)** described in the architecture above.

---

## Agentic AI Model

This system is designed as an **agentic AI architecture**, not a chatbot.

### What makes it agentic:

- Deterministic reasoning engine (issues + recommendations)
- AI narrative layer (explains and contextualizes decisions)
- Historical awareness via ADB
- Future capability:
  - trend-based decision making
  - predictive workload behavior
  - OCI sizing recommendations

### Decision Flow

```text
AWR → Facts → Issues → Recommendations → AI Interpretation → Decision Support
```

The AI does not make decisions blindly — it operates on validated system findings.

---

## Multi-AWR Analysis

The system is designed to process multiple AWR reports.

Each AWR may represent:
- different workloads
- different performance problems
- different system behaviors

The system:
- analyzes each AWR independently
- produces tailored recommendations per workload
- will support historical trend analysis via ADB

### Why this matters

Real environments are not single snapshots.

Multi-AWR analysis enables:
- trend detection over time
- anomaly identification
- capacity planning based on actual workload evolution

---

## Development Progress

### AWR Parsing Foundation (Complete)

- Implemented ingestion of Oracle AWR .out files
- Built section detection (CPU, waits, SQL, etc.)
- Extracted run metadata (DB name, host, snapshots)
- Established canonical data model (ParseResult, RunMetadata)

**Outcome:** Reliable, structured extraction from raw AWR reports

---

### Structured Metrics Extraction (Complete)

- Parsed CPU load profile metrics
- Parsed foreground wait events
- Parsed Top SQL (elapsed time, CPU, reads)
- Mapped SQL text to SQL IDs
- Introduced structured metric objects

**Outcome:** Raw AWR text converted into structured, queryable data

---

### Automated Performance Issue Detection (Complete)

The system performs deterministic performance analysis, converting metrics into prioritized, evidence-backed findings.

#### Detected Issue Types

- **CPU Pressure** — Detects CPU bottlenecks
- **SQL Concentration** — Identifies dominant SQL workloads (with module attribution)
- **I/O Pressure** — Highlights User I/O wait events
- **Commit Pressure** — Detects latency via log file sync
- **Concurrency Pressure** — Identifies contention patterns

**Outcome:** The system can identify what is wrong and why

---

### Recommendation Engine (Complete)

The system now generates senior DBA-grade recommendations with clear execution guidance.

#### Capabilities
- Deterministic issue → recommendation mapping
- Evidence-based rationale
- Prioritized action steps
- Explicit next-step execution guidance
- Executive Summary generation

#### Example Output

> **EXECUTIVE SUMMARY**
> 
> **Primary finding:** CPU-bound workload (64.8% DB time)
>
> The workload is primarily CPU-bound, with DB CPU consuming 64.8% of total database time.
> User I/O remains material, led by 'cell single block physical read' at 12.4%, commit latency
> is also contributing at 8.2%, and concurrency pressure is present at 2.6%.
>
> SQL activity is concentrated in module 'OrderService', where the top statements account
> for 26.6% of elapsed SQL time.
>
> The correct direction is to tune SQL, access paths, and transaction behavior before
> considering additional capacity.

**Outcome:** The system not only identifies problems, but clearly explains what to do and what to do first

---

## AI Narrative Layer (Completed)

The AI layer generates a structured, executive-ready advisory output grounded in deterministic findings and contributes to decision framing.

### Capabilities

- Builds a grounded AI prompt from:
  - Run metadata
  - Detected issues
  - Deterministic recommendations
  - Key metrics
  - Top SQL

- Enforces strict constraints:
  - No invented metrics
  - No contradiction of findings
  - No unsupported root causes
  - No arbitrary sizing values

- Produces structured output sections:
  - Executive Summary (includes decision)
  - Technical Narrative
  - Root Cause Interpretation
  - Recommended Action Plan
  - OCI Sizing Considerations
  - Confidence Assessment
  - Risk of Being Wrong

---

### Decision Framework

The system now produces an explicit decision (e.g., **DO NOT SCALE**, **DEFER**, **INSUFFICIENT DATA**).

Decision strength is influenced by confidence:

- High confidence → definitive recommendation
- Medium confidence → cautious / deferred recommendation
- Low confidence → insufficient evidence to act

This ensures decisions reflect both:
- deterministic evidence
- quality and completeness of available data

---

### Dashboard Visualization Layer (Completed)

The project now generates an interactive HTML dashboard that presents deterministic findings, AI narrative output, and workload visualizations in a single view.

#### Current dashboard capabilities

- AI-first advisory layout
- Deterministic evidence cards
- Decision layer with recommended execution posture
- Interactive performance charts
- Violin-based workload distribution panel (real distributions only, no synthetic expansion)

#### Current visualizations

- DB Time Breakdown
- Top SQL Contribution
- Workload Distribution — Violin Panel

#### Violin metrics currently populated

- CPU %
- Executions per Second
- Read IOPs
- Read MB/s
- Write IOPs
- Write MB/s
- User I/O Wait
- Top SQL Elapsed Time (normalized)
- Log File Sync Latency

#### Metrics currently available as scalar facts

- PGA Spill Pressure
- Temp I/O Pressure
- Hard Parses/s

#### Derived Scalar Metrics

Metrics without sufficient distribution data are surfaced as scalar facts:

- PGA Spill Pressure
- Temp I/O Pressure
- Hard Parses/s

These are:
- Extracted or derived from AWR evidence
- Not visualized as distributions
- Shown separately to preserve analytical integrity

#### Violin chart semantics

Each violin chart currently shows:
- Full workload distribution
- IQR box
- Median line
- Mean marker
- Max marker
- Min annotation

This provides a distribution-based view of workload behavior rather than relying only on averages.

#### Important Constraint

Violin charts are rendered only when real multi-sample distributions exist.

- No synthetic expansion of scalar values
- No interpolated or heuristic-generated series
- Metrics with insufficient data are omitted from the violin panel

This guarantees that all visualizations reflect actual workload behavior.

---

### Important

The AI layer has evolved beyond a pure narrative component and now operates as part of the advisory system.

The AI layer:
- Operates on deterministic findings as its foundation
- Augments analysis with structured interpretation and prioritization
- Contributes to decision framing (not just explanation)
- Can influence OCI sizing guidance through contextual reasoning

However:

- Deterministic analysis remains the source of truth
- AI does not override validated system findings
- All outputs are grounded in extracted metrics and detected issues

This ensures:
- Credibility
- Explainability
- Consistency across runs

The system is transitioning from:
- Narrative generation → to → decision support augmentation

---

## Key Capabilities
- Deterministic, explainable performance analysis
- Evidence-backed insights with precise metrics
- Priority-based issue detection
- DBA-grade recommendations with execution guidance
- Workload attribution to application modules
- Executive-level summary generation

---

## Value Proposition

From AWR → to decision → in seconds

This system provides:

- Deterministic, repeatable analysis
- AI-enhanced explanation (not guesswork)
- Prioritized performance actions
- Future-ready OCI sizing guidance
- Interactive HTML dashboard generation
- Distribution-based workload visualization with violin charts
- Visual comparison of CPU, I/O, SQL, and latency behavior
- Stable dual-provider AI dashboard output (OCI + OpenAI-ready design)
- Strict analytical honesty (no fabricated distributions or synthetic metrics)

This is not:
- A report generator
- A chatbot

This is:
- An autonomous performance and sizing advisor

---

## Roadmap

### Completed

- AWR Parsing
- Structured Metrics
- Issue Detection
- Recommendation Engine
- AI Narrative Layer (grounded, no hallucination)

### Next

### Agentic Decision Layer + ADB Integration

Evolve from recommendations to guided execution planning.

Planned capabilities:
- Introduce ADB for historical storage and trend analysis
- Prioritize actions based on impact
- Sequence tuning steps
- Suggest next best actions
- Enable advisor-style workflows

**Outcome:** Stateful, context-aware performance advisor

---

### OCI Sizing & Demo Packaging

Connect performance analysis to OCI infrastructure decisions.

Planned capabilities:
- Map workload → OCPU, memory, storage guidance
- Use historical trends from ADB
- Generate OCI-aligned recommendations
- Deliver full OCI-native demo workflow

**Outcome:** End-to-end pipeline from AWR → analysis → recommendations → AI insights → OCI sizing

---

## Target End State

A fully agentic system that delivers:
- Structured AWR parsing
- Deterministic issue detection
- DBA-grade recommendations
- AI-generated narrative insights
- Action prioritization
- OCI sizing guidance

Transforming:
```text
AWR Report → Manual Analysis → Guesswork
```
into:
```text
AWR Report → Automated Analysis → Recommendations → AI Insights → OCI Decisions
```

---

## Quick Start
```bash
python scripts/run_analysis.py
```
---

## Project Structure
```text
src/
  models/
  parser/
  analysis/
  reporting/
scripts/
data/
dbschema/
examples/
```

---

## Status

**Complete Milestone — Deterministic Analysis + AI Advisory Dashboard Complete**  

Current state:
- Deterministic analysis working
- AI advisory layer working
- Interactive HTML dashboard working
- Violin workload panel working for core distribution-backed metrics
- Scalar extraction implemented for PGA Spill Pressure, Temp I/O Pressure, Hard Parses/s
- ADB schema completed and provisioned
- Multi-AWR ingestion and historical trend support next

Next: **Multi-AWR ingestion and comparison, ADB history/trend integration, and Agentic Decision Layer**
