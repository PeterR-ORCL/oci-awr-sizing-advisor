# OCI AWR Agentic AI Sizing Advisor

<p align="center">
  <b>From AWR → Decision → Action</b><br/>
  Autonomous Performance & OCI Sizing Advisor
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue"/>
  <img src="https://img.shields.io/badge/Oracle-ADB-red"/>
  <img src="https://img.shields.io/badge/Status-Active-green"/>
  <img src="https://img.shields.io/badge/AI-Agentic-orange"/>
</p>

---

## Overview

The OCI AWR Agentic AI Sizing Advisor is an **agentic AI system** that transforms Oracle AWR reports into:

- Performance insights  
- Root cause analysis  
- Actionable recommendations  
- OCI sizing guidance  

It replaces manual AWR interpretation with a **deterministic, explainable, and automation-ready system**.

---

## Environment Awareness (Key Differentiator)

The system automatically identifies the database environment from AWR data, including:

- Single Instance
- RAC (Clustered databases)
- Exadata
- Data Guard (DG)
- Active Data Guard (ADG)

This enables:
- Context-aware analysis  
- Correct interpretation of wait events (e.g., GC vs local waits)  
- Environment-specific recommendations  
- Accurate OCI sizing decisions  

---

## Key Capabilities

- Deterministic AWR analysis (no guesswork)
- Issue detection (CPU, I/O, SQL, waits)
- Evidence-based recommendations
- AI-generated executive summaries
- Interactive HTML dashboard
- Multi-AWR ready architecture
- OCI sizing guidance
- Environment-aware diagnostics (RAC, Exadata, DG/ADG)

---

## Architecture

```
AWR (.out)
   ↓
Parser
   ↓
Metrics Extraction
   ↓
Environment Detection
   ↓
Issue Detection
   ↓
Recommendations
   ↓
---------------------------
Deterministic Truth Layer
---------------------------
   ↓
AI Narrative Layer
   ↓
---------------------------
Context Layer (ADB)
---------------------------
   ↓
Decision Engine
   ↓
OCI Sizing Guidance
```

---

## Dashboard

### Includes
- Executive Summary
- Decision Layer
- Supporting Evidence

### Visualizations
- DB Time Breakdown
- Top SQL Contribution
- Violin Workload Distributions

### Design Rules
- No synthetic distributions
- No interpolation
- Only real AWR-derived data

---

## ADB Integration

Fully implemented ingestion pipeline into **Oracle Autonomous Database (ADB)**

### Tables
- AWR_INGEST_RUN
- AWR_SOURCE_SYSTEM
- AWR_REPORT
- AWR_METRIC_FACT
- AWR_TOP_SQL_FACT
- AWR_WAIT_EVENT_FACT
- AWR_FEATURE_VECTOR

### Capabilities
- Wallet-based secure connection
- Transaction-safe ingestion
- Structured analytics-ready data

---

## Deterministic Analysis

Detects:
- CPU pressure
- SQL concentration
- I/O bottlenecks
- Commit latency
- Concurrency contention
- Cluster (GC) contention (RAC)
- Interconnect-related waits
- Storage offload inefficiencies (Exadata)
- Replication / transport lag signals (DG/ADG)

---

## Recommendation Engine

- Deterministic mapping: issue → action
- Prioritized recommendations
- Evidence-backed decisions

Focus:
**Fix workload before scaling infrastructure**

---

## AI Narrative Layer

Generates:
- Executive Summary
- Root Cause Analysis
- Action Plan
- OCI Sizing Considerations
- Confidence & Risk

Constraints:
- No fabricated metrics
- No contradiction of facts

---

## Multi-AWR Vision

- Historical trend analysis
- Anomaly detection
- Capacity planning
- Learning via ADB

---

## Quick Start

```
pip install -r requirements.txt
python scripts/run_analysis.py
```

---

## Project Structure

```
src/
  parser/
  analysis/
  reporting/
scripts/
data/
dbschema/
```

---

## Roadmap

- Multi-AWR time-series analysis
- Scoring engine
- Decision automation
- OCI sizing integration
- Learning feedback loop

---

## Value Proposition

**From AWR → Decision → Action**

This is:
- Not a report  
- Not a chatbot  

This is:
- Autonomous performance advisor  
- OCI sizing decision engine  

---

## Status

- Parsing: Complete  
- Analysis: Complete  
- Recommendations: Complete  
- AI Layer: Complete  
- Dashboard: Complete  
- ADB Ingestion: Complete  

Next:
- Multi-AWR intelligence  
- Agentic decision layer  

---

## Final Note

This project has moved beyond reporting.

It is now:
**An autonomous performance and sizing system.**
