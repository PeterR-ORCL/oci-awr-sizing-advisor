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

The system follows a layered approach:

```text
AWR Report (.out)
        ↓
Parsing Layer (Day 1)
        ↓
Structured Metrics (Day 2)
        ↓
Issue Detection (Day 3)
        ↓
Recommendation Engine (Day 4)
        ↓
AI Narrative Layer (Day 5 - Next)
        ↓
OCI Sizing Guidance (Day 7)
```

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

## Key Capabilities
- Deterministic, explainable performance analysis
- Evidence-backed insights with precise metrics
- Priority-based issue detection
- DBA-grade recommendations with execution guidance
- Workload attribution to application modules
- Executive-level summary generation

---

## Value Proposition

This system replaces manual AWR analysis with:
- Rapid identification of performance bottlenecks
- Consistent and repeatable analysis
- Clear, prioritized remediation steps
- A foundation for automated OCI sizing decisions

---

## Roadmap

### Day 5 — AI Narrative Layer (Next)

Introduce the mandatory AI layer for explanation and synthesis.

Planned capabilities:
- Generate executive summaries in natural language
- Explain root causes in business-friendly terms
- Produce narrative action plans
- Answer “why this matters” and “what to do next”

**Outcome:** The system becomes explainable, conversational, and demo-ready

---

### Day 6 — Agentic Decision Layer

Evolve from recommendations to guided execution planning.

Planned capabilities:
- Prioritize actions by impact
- Sequence tuning steps
- Suggest next best actions
- Enable advisor-style workflows

**Outcome:** The system behaves like a performance advisor, not just a reporting tool

---

### Day 7 — OCI Sizing & Demo Packaging

Connect performance analysis to OCI infrastructure decisions.

Planned capabilities:
- Map workload → OCPU, memory, storage guidance
- Provide initial sizing recommendations
- Align performance findings with cloud architecture
- Deliver full demo workflow

**Outcome:** End-to-end pipeline from AWR → analysis → recommendations → OCI sizing

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

**Day 4 Complete — Recommendation Engine Delivered**  
Next: **Day 5 — AI Narrative Layer**
