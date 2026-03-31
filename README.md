# OCI AWR Sizing Advisor — Progress Overview

## Overview

The OCI AWR Sizing Advisor is an **agentic AI system** that transforms Oracle AWR reports into **actionable performance insights and OCI sizing guidance**.

The system progresses from raw AWR parsing to deterministic analysis, and ultimately to **recommendations, narrative insights, and infrastructure decisions**.

It is designed to replace manual AWR interpretation with a **repeatable, explainable, and automation-ready workflow**.

---

## Why This Matters

Traditional AWR analysis relies on manual interpretation, requiring deep expertise and significant time investment.

This system introduces:
- Deterministic analysis → consistent outcomes  
- Structured metrics → machine-readable insights  
- Automated recommendations → immediate actionability  
- AI narrative layer → executive-level communication  

Bridging the gap between **performance engineering and business decision-making**.

---

## Design Principles

- Deterministic analysis is the source of truth
- AI augments, but does not replace, evidence-based findings
- Dual AI providers enable flexibility and OCI alignment
- AI is stateless by design; state and history are introduced explicitly via ADB
- Historical context (ADB) enables trend-based decisions

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
Parsing Layer (Day 1)
        ↓
Structured Metrics (Day 2)
        ↓
Issue Detection (Day 3)
        ↓
Recommendation Engine (Day 4)
        ↓
────────────────────────────────────────────
Deterministic Truth Layer (Source of Truth)
────────────────────────────────────────────
        ↓
AI Narrative Layer (Day 5 - Grounded, Stateless)
   → OpenAI (advanced reasoning)
   → OCI Generative AI (Oracle-native AI)
        ↓
────────────────────────────────────────────
Context & State Layer
────────────────────────────────────────────
        ↓
ADB (Day 6 - History / Trends)
        ↓
Agentic Decision Layer (Day 6 - Stateful, Context-Aware)
        ↓
OCI Sizing Guidance (Day 7)
```

---

## Agentic AI Model

This system is designed as an **agentic AI architecture**, not a chatbot.

### What makes it agentic:

- Deterministic reasoning engine (issues + recommendations)
- AI narrative layer (explains and contextualizes decisions)
- Historical awareness via ADB (Day 6)
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
- will support historical trend analysis via ADB (Day 6)

### Why this matters

Real environments are not single snapshots.

Multi-AWR analysis enables:
- trend detection over time
- anomaly identification
- capacity planning based on actual workload evolution

---

## Development Progress

### Day 1 — AWR Parsing Foundation (Complete)

- Implemented ingestion of Oracle AWR .out files
- Built section detection (CPU, waits, SQL, etc.)
- Extracted run metadata (DB name, host, snapshots)
- Established canonical data model (ParseResult, RunMetadata)

**Outcome:** Reliable, structured extraction from raw AWR reports

---

### Day 2 — Structured Metrics Extraction (Complete)

- Parsed CPU load profile metrics
- Parsed foreground wait events
- Parsed Top SQL (elapsed time, CPU, reads)
- Mapped SQL text to SQL IDs
- Introduced structured metric objects

**Outcome:** Raw AWR text converted into structured, queryable data

---

### Day 3 — Automated Performance Issue Detection (Complete)

The system performs deterministic performance analysis, converting metrics into prioritized, evidence-backed findings.

#### Detected Issue Types

- **CPU Pressure** — Detects CPU bottlenecks
- **SQL Concentration** — Identifies dominant SQL workloads (with module attribution)
- **I/O Pressure** — Highlights User I/O wait events
- **Commit Pressure** — Detects latency via log file sync
- **Concurrency Pressure** — Identifies contention patterns

**Outcome:** The system can identify what is wrong and why

---

### Day 4 — Recommendation Engine (Complete)

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

## Day 5 — AI Narrative Layer (Completed)

The AI layer generates a structured, executive-ready narrative based strictly on deterministic findings.

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
  - Executive Summary
  - Technical Narrative
  - Root Cause Interpretation
  - Recommended Action Plan
  - OCI Sizing Considerations

### Important

The AI layer:
- does NOT analyze raw AWR data
- does NOT replace deterministic logic
- is purely a **narrative and interpretation layer**

This ensures credibility and repeatability.

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

This is not:
- a report generator
- a chatbot

This is:
- an autonomous performance and sizing advisor

---

## Roadmap

### Completed

- Day 1 — AWR Parsing
- Day 2 — Structured Metrics
- Day 3 — Issue Detection
- Day 4 — Recommendation Engine
- Day 5 — AI Narrative Layer (grounded, no hallucination)

### Next

### Day 6 — Agentic Decision Layer + ADB Integration

Evolve from recommendations to guided execution planning.

Planned capabilities:
- Introduce ADB for historical storage and trend analysis
- Prioritize actions based on impact
- Sequence tuning steps
- Suggest next best actions
- Enable advisor-style workflows

**Outcome:** Stateful, context-aware performance advisor

---

### Day 7 — OCI Sizing & Demo Packaging

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
scripts/
data/
```

---

## Status

**Day 5 Complete — AI Narrative Layer**  
Next: **Day 6 ADB (History / Trends) and Agentic Decision Layer
