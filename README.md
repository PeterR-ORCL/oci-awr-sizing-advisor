# Agentic AI AWR Advisor

<p align="center">
  <b>From AWR Data to Deterministic Intelligence, Memory, and Action</b><br/>
  Autonomous Database Performance Intelligence Platform
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue"/>
  <img src="https://img.shields.io/badge/Oracle-ADB-red"/>
  <img src="https://img.shields.io/badge/Object%20Storage-Enabled-blue"/>
  <img src="https://img.shields.io/badge/Status-Phase%206%20Active-blue"/>
  <img src="https://img.shields.io/badge/AI-Agentic-orange"/>
  <img src="https://img.shields.io/badge/Trend%20Engine-Enabled-purple"/>
  <img src="https://img.shields.io/badge/Architecture-Cloud%20Native-blueviolet"/>
  <img src="https://img.shields.io/badge/Intelligence-Deterministic-purple"/>
</p>

---

# Executive Summary

The Agentic AI AWR Advisor is an Autonomous Database Performance Intelligence Platform that transforms Oracle AWR data into deterministic insights, autonomous decisions, actionable outcomes, and persistent memory.

It combines a deterministic analysis engine with an agentic AI layer to deliver:

- Root-cause diagnostics with full explainability  
- Prioritized and evidence-based recommendations  
- Autonomous decision support  
- Persistent run and action memory  
- Scalable, cloud-native performance intelligence  
- Built to operate reliably across heterogeneous AWR formats without requiring schema normalization or manual adjustment

> **This system replaces manual AWR interpretation with a repeatable, auditable, and automation-ready decision framework.**

---

## Executive Overview

The Agentic AI  AWR Sizing Advisor is a **deterministic + agentic AI + memory system** that transforms Oracle AWR reports into:

- Root-cause performance diagnostics  
- Prioritized remediation actions  
- AI-guided decision support  
- Infrastructure sizing recommendations  
- Action tracking and memory-backed intelligence  

This system eliminates subjective interpretation and replaces it with:

> **Repeatable, explainable, and automation-ready intelligence**

---

## Why This System Exists

Traditional AWR analysis suffers from:

- Manual interpretation  
- Inconsistent conclusions  
- Time-intensive workflows  
- Heavy reliance on expert intuition  

This platform introduces:

- Deterministic reasoning  
- Structured data pipelines  
- Automated analysis  
- AI-assisted interpretation  
- Persistent memory and action tracking  
- Scalable architecture for enterprise environments  

---

## Core Design Principles

- Deterministic analysis is the source of truth  
- AI augments interpretation, not facts  
- Memory is downstream and non-influencing  
- Stateless reasoning + stateful context (ADB)  
- No fabricated data or synthetic distributions  
- Observability-first architecture  
- Full auditability of decisions  

---

## AWR Format Resilience (NEW)

AWR parsing is inherently **non-deterministic** due to format variability in report structure across database versions, configurations, and deployment topologies.

Observed sources of variability include:
- Version differences (11g, 12c, 19c, 23ai)
- Topology differences (Single Instance, RAC, Data Guard, Exadata)
- Feature-dependent sections (licensing / options enabled)
- Section ordering inconsistencies
- Formatting drift across patch levels and platforms

This variability makes position-based or rigid parsing approaches unreliable in production environments.

### Design Approach

The parsing engine is implemented using a **section-driven, pattern-based architecture.**

Key characteristics:
- **Section discovery via semantic headers**
Sections are identified using pattern matching rather than fixed offsets
- **Loose coupling between detection and extraction**
Section boundaries are resolved independently from parsing logic
- **Content normalization layer**
Raw text is sanitized to remove formatting artifacts and delimiters
- **Graceful degradation model**
Missing or partial sections do not interrupt ingestion
- **Deterministic extraction rules**
All parsed outputs are derived from explicit patterns (no inference)
- **Parse diagnostics and validation signals**
The system produces structured diagnostics for traceability and audit

### Operational Behavior
- Parsing is resilient to missing sections
- Partial data is still ingested and classified
- Invalid or ambiguous content is isolated without pipeline failure
- All outputs remain deterministic and reproducible

### Outcome
- Stable ingestion across heterogeneous AWR datasets
- Compatibility with mixed-version enterprise environments
- No dependency on a canonical AWR format

> **The system is engineered to operate on real-world AWR data, not controlled or idealized report structures.**

---

## End-to-End Architecture

### Data Flow

AWR (.out files)  
→ Parsing Layer  
→ Structured Metrics  
→ Feature Vector Layer  
→ ADB (State Layer)  
→ Scoring Engine  
→ Trend & Anomaly Engine  
→ Agentic Decision Engine  
→ Dashboard + OCI Sizing  

---

## Architecture Diagram

```mermaid
flowchart LR
    A[AWR Files] --> B[Parsing Pipeline]
    B --> C[Structured Metrics and Metadata]
    C --> D[Feature Vector Layer]
    D --> E[Autonomous Database ADB]
    E --> F[Intelligence Layer - Scoring + Trends]
    F --> G[Agentic Decision Engine]
    G --> H[Dashboard / OCI Sizing Output]
```

---

## Object Storage Ingestion Flow (ADDED)

```mermaid
flowchart LR
    A[AWR Upload] --> B[OCI Object Storage]
    B --> C[Ingestion Pipeline]
    C --> D[Parser Engine]
    D --> E[Feature Vector Layer]
    E --> F[ADB State Layer]
    F --> G[Decision Engine]
    G --> H[Insights + Recommendations]
```

---

## Cloud-Native Design

The platform is designed as a cloud-native pipeline:

- Object Storage for raw AWR ingestion
- Autonomous Database (ADB) for state and analytics
- Deterministic parsing and feature extraction
- Scalable ingestion for multi-AWR workloads

**This enables enterprise-scale performance intelligence across environments.**

---

## Machine Learning Readiness

The feature vector layer provides a foundation for:

- Similarity-based workload analysis  
- Pattern recognition across environments  
- Future supervised learning models  
- Outcome-based optimization  

This **enables a transition from deterministic intelligence to adaptive learning systems.**

---

## Feature Vector System

Each AWR snapshot is transformed into a **feature vector** stored in:

- AWR_FEATURE_VECTOR

### Contents

- Raw extracted metrics  
- Engineered metrics  
- Derived ratios  
- Classification signals  

### Examples

- DB_CPU_PCT_DB_TIME  
- REDO_GENERATION_PER_SEC  
- CELL_SINGLE_BLOCK_LATENCY_MS  
- NETWORK_WAIT_PCT_DB_TIME  

### Purpose

Feature vectors enable:

- Scoring  
- Trend analysis  
- ML readiness  

---

## Vector Intelligence Layer (ADDED)

The feature vector layer is the foundation for:

- Similarity search  
- Pattern clustering  
- Workload fingerprinting  
- Future supervised ML models  

---

## DB-Level Trend & Anomaly Engine

### Storage

Table:
- AWR_DB_METRIC_TREND  

Granularity:
- DB_NAME  
- DBID  
- METRIC_NAME  
- SNAP_BEGIN_TIME  

---

### Trend Computation

Each metric produces:

- Rolling mean  
- Rolling standard deviation  
- Slope (trend direction)  
- Percent change  
- Baseline mean / variance  

---

### Anomaly Semantics

#### Continuous Metrics

Detects:

- SPIKE  
- DROP  
- TREND_SHIFT  
- VOLATILITY_INCREASE  
- ZERO_ANOMALY  

#### State / Flag Metrics

Detects:

- ACTIVATED  
- CLEARED  
- STATE_CHANGE  

---

### Noise Control

- Absolute threshold gating  
- Low-variance suppression  
- History-aware anomaly detection  

---

## ADB (State Layer)

### Tables

- AWR_INGEST_RUN  
- AWR_SOURCE_SYSTEM  
- AWR_REPORT  
- AWR_METRIC_FACT  
- AWR_TOP_SQL_FACT  
- AWR_WAIT_EVENT_FACT  
- AWR_FEATURE_VECTOR  
- AWR_DB_METRIC_TREND  

---

### Capabilities

- Secure wallet-based connection  
- Transaction-safe ingestion  
- Time-series persistence  
- Analytical query layer  

---

## Deterministic Analysis Engine

Detects:

- CPU pressure  
- SQL concentration  
- I/O bottlenecks  
- Commit latency  
- Concurrency contention  
- RAC interconnect stress  
- Exadata inefficiencies  
- Data Guard transport issues  

---

## Scoring Engine

- Weighted deterministic scoring  
- Risk classification  
- Confidence scoring  

Used for:

- prioritization  
- decision ranking  

---

## Recommendation Engine

- Deterministic mapping (issue → action)  
- Prioritized execution plans  
- Evidence-based recommendations  

Guiding principle:

> Fix workload before scaling infrastructure  

---

## AI Narrative Layer

Produces:

- Executive Summary  
- Root Cause Analysis  
- Action Plan  
- OCI Sizing Considerations  
- Confidence + Risk  

### Constraints

- No hallucinated metrics  
- No contradiction of facts  
- Fully grounded in deterministic outputs  

---

## Dashboard Layer

### Sections

- Executive Summary  
- Decision Layer  
- Evidence Panel  
- Trend & anomaly visualization  

### Rules

- No synthetic data  
- No interpolation  
- Only real AWR-derived signals  

---

## Multi-AWR Intelligence

Enables:

- Historical trend analysis  
- Cross-snapshot anomaly detection  
- Capacity planning  
- ML pipeline readiness  

---

## Learning Loop (ADDED)

```mermaid
flowchart LR
    A[AWR Data] --> B[Analysis Engine]
    B --> C[Recommendations]
    C --> D[Actions Taken]
    D --> E[New AWR Data]
    E --> F[Outcome Tracking]
    F --> G[Model Improvement]
```

---

## Agentic Model

This is not a chatbot.

This is:

- Deterministic reasoning engine  
- AI interpretation layer  
- Stateful decision system  

### Decision Flow

AWR → Metrics → Issues → Recommendations → AI → Decision  

---

## Roadmap

### Phase 4
- Dashboard wiring  
- Domain-based insights  

### Phase 5
- Recommendation persistence  
- Action tracking  

### Phase 6
- Outcome tracking  
- ML feedback loop  

---

## Value Proposition

From AWR → Decision → Action

This is NOT:

- A report  
- A chatbot  

This IS:

- Autonomous performance advisor  
- OCI sizing decision engine  

---

## Status

- Parsing: Complete  
- Feature Vectors: Complete  
- Scoring Engine: Complete  
- Trend Engine: Complete  
- Anomaly Detection: Refined  
- ADB Integration: Complete  
- Object Storage Integration: Complete  

Next:

- Dashboard wiring  
- Decision layer  
- Learning system  

---

## Quick Start

pip install -r requirements.txt  
python scripts/run_analysis.py  

---

## Project Structure

src/
  parser/
  analysis/
  reporting/
scripts/
data/
dbschema/

---

## Final Statement

This project has evolved beyond reporting.

It is now:

**A deterministic intelligence platform evolving into a fully autonomous decision system.**


---

## Phase 6 — Memory & Action Tracking

The system now includes a structured memory layer:

- Run Memory (6G)  
- Action Tracking (6H)  
- Unknown Signal Capture  

Memory is:

- Deterministic-safe  
- Non-influencing (does not affect scoring or decisions)  
- Fully auditable  

### Oracle Agent Memory (6N.1)

Oracle Agent Memory can be integrated as a non-authoritative augmentation layer:

- Provides contextual recall and conversational continuity  
- Enhances phrasing and interpretation only  
- Does NOT influence scoring, parsing, decisions, or recommendations  

This ensures strict separation between:

Deterministic Truth → Phase 4  
Memory & Context → Phase 6  
Adaptive Learning → Phase 7  

---

