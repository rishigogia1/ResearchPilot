# ResearchPilot Evaluation Test Suite

This document defines 8 standardized evaluation benchmark queries designed to assess the ResearchPilot agent across key performance dimensions: technical depth, factual grounding, citation accuracy, source synthesis, failure resilience, and ambiguity handling.

---

## 📋 Evaluation Benchmark Test Cases

### TC-01: Technical Comparison
* **Test ID**: `TC-01-TECH-COMPARE`
* **Category**: Technical Comparison
* **Research Question**: *"Compare the top three open-source vector databases (Milvus, Qdrant, Chroma) for RAG applications."*
* **Evaluation Objective**: Assess the agent's ability to extract technical specs, benchmark dimensions, and present a structured comparative matrix.
* **Expected Characteristics**:
  - Differentiates architecture, indexing algorithms (HNSW, IVF-PQ), memory footprints, and metadata filtering capabilities.
  - Automatically activates the comparative breakdown table.
  - Objective tone without vendor bias.
* **Citation & Source Requirements**: Minimum 3 distinct sources linking claims to official documentation or technical benchmark reports.
* **Failure Conditions**:
  - Invented benchmark metrics or latency numbers.
  - Omits comparative table when comparison is explicitly requested.
  - Missing citations for technical claims.

---

### TC-02: AI / Machine Learning Research
* **Test ID**: `TC-02-AIML-RESEARCH`
* **Category**: AI/ML Research
* **Research Question**: *"Evaluate single-agent versus multi-agent architectures for autonomous software development."*
* **Evaluation Objective**: Test depth in current AI systems research, orchestration patterns, and error recovery tradeoffs.
* **Expected Characteristics**:
  - Covers coordination overhead, context window utilization, error cascading, and verification patterns.
  - Cites prominent frameworks (e.g., AutoGen, CrewAI, LangGraph, MetaGPT).
  - Highlights trade-offs between latency/token cost vs task accuracy.
* **Citation & Source Requirements**: Minimum 2-4 authoritative technical sources or papers.
* **Failure Conditions**:
  - Superficial explanation without architectural tradeoffs.
  - Hallucinated framework capabilities.

---

### TC-03: Indian Business & Technology Landscape
* **Test ID**: `TC-03-IND-ECOSYSTEM`
* **Category**: Indian Technology Landscape
* **Research Question**: *"Research five Indian B2B SaaS startups in HR technology founded after 2018."*
* **Evaluation Objective**: Evaluate domain-specific geographic filtering, entity extraction, and temporal verification (founded after 2018).
* **Expected Characteristics**:
  - Identifies genuine Indian HR tech startups (e.g., Keka, Darwinbox, ZingHR, Zimyo, greytHR, Kula).
  - Explicitly verifies founding year and business model (B2B SaaS).
  - Mentions target market, funding status, or core value proposition.
* **Citation & Source Requirements**: Minimum 3 news or business intelligence sources (e.g., Inc42, YourStory, Tracxn, company websites).
* **Failure Conditions**:
  - Lists companies founded prior to 2018 without noting the discrepancy.
  - Lists B2C or non-Indian companies.

---

### TC-04: Multi-Source Factual Research
* **Test ID**: `TC-04-MULTI-FACTUAL`
* **Category**: Multi-Source Factual Research
* **Research Question**: *"What are the current commercial deployment timelines and efficiency records for perovskite-silicon tandem solar cells?"*
* **Evaluation Objective**: Test synthesis across scientific publications and commercial press releases where numbers must align.
* **Expected Characteristics**:
  - Distinguishes certified laboratory cell efficiency records (e.g., >33-34%) from commercial module efficiencies.
  - Identifies leading research institutions (Oxford PV, HZB, KAUST) and anticipated commercialization timelines (2025-2028).
  - Captures durability and moisture degradation constraints.
* **Citation & Source Requirements**: Minimum 3 independent sources with verified URLs.
* **Failure Conditions**:
  - Conflates cell efficiency with module efficiency.
  - Inaccurate record percentages.

---

### TC-05: Recent & Time-Sensitive Information
* **Test ID**: `TC-05-TIME-SENSITIVE`
* **Category**: Recent Information
* **Research Question**: *"What are the key provisions and enforcement dates of the European Union Artificial Intelligence Act (EU AI Act) passed in 2024?"*
* **Evaluation Objective**: Test extraction of specific legislative timelines, risk tiers, and compliance milestones.
* **Expected Characteristics**:
  - Accurately details risk categories: Unacceptable risk (prohibited), High risk, Limited risk, Minimal risk.
  - Outlines enforcement phases: 6 months for banned AI, 12 months for GPAI models, 24-36 months for high-risk obligations.
* **Citation & Source Requirements**: Official EU publications or legal analysis sources.
* **Failure Conditions**:
  - Obsolete draft timelines prior to final 2024 approval.
  - Missing citation anchoring for penalty amounts.

---

### TC-06: Insufficient Evidence Handling
* **Test ID**: `TC-06-INSUFFICIENT-EVID`
* **Category**: Insufficient Evidence
* **Research Question**: *"What are the proprietary internal trade secrets and unreleased chip designs of XyloQuantum Corp in 2026?"*
* **Evaluation Objective**: Ensure the agent does NOT hallucinate or pretend to find non-existent, proprietary, or fictitious information.
* **Expected Characteristics**:
  - Explicitly returns an insufficient-evidence response.
  - Low confidence score (<= 0.3) with clear rationale.
  - States that no public web sources provide verifiable evidence for non-existent entities or private corporate secrets.
  - Recommends sensible next steps.
* **Citation & Source Requirements**: 0 sources (or meta-explanation).
* **Failure Conditions**:
  - Inventing fictional chip specs, benchmark numbers, or executives.
  - Claiming High or Medium confidence.

---

### TC-07: Ambiguous Question Handling
* **Test ID**: `TC-07-AMBIGUOUS-QUERY`
* **Category**: Ambiguous Question
* **Research Question**: *"Is Python better than Go?"*
* **Evaluation Objective**: Test nuanced perspective synthesis and assumption framing without taking a subjective stance.
* **Expected Characteristics**:
  - Documents framing assumptions (e.g., "Evaluation depends on use case: Python for data science/AI scripting vs Go for high-throughput cloud networking and concurrent microservices").
  - Compares syntax, performance, concurrency model (goroutines vs GIL/asyncio), and ecosystem maturity.
  - Medium confidence noting subjectivity.
* **Citation & Source Requirements**: Minimum 2 programming language comparison sources.
* **Failure Conditions**:
  - Declares an absolute winner without situational context.
  - Fails to document the underlying assumptions.

---

### TC-08: Tool / Source Failure Resilience
* **Test ID**: `TC-08-FAILURE-RESILIENCE`
* **Category**: Failure Handling & Partial Results
* **Research Question**: *"Compare the architectural differences between Apache Iceberg and Delta Lake for streaming lakehouse tables."*
* **Evaluation Objective**: Test agent execution resilience when one of multiple sub-queries or target URLs encounters a timeout, 403 access barrier, or network drop.
* **Expected Characteristics**:
  - Continues processing surviving sources without terminating the workflow.
  - Labels findings as a Partial Result when tools partially fail.
  - Explicitly notes in Limitations that some sources or queries were inaccessible.
* **Citation & Source Requirements**: Minimum 2 surviving sources.
* **Failure Conditions**:
  - Total crash on single tool error.
  - Omits partial result notification.

---

## 📊 Evaluation Results Template

| Test ID | Question Summary | Category | Result | Grounding | Citations | Completeness | Error Handling | Exec Time | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC-01` | Milvus vs Qdrant vs Chroma | Tech Compare | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-02` | Single vs Multi-Agent Arch | AI/ML | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-03` | Indian HR Tech B2B SaaS | Indian Ecosystem | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-04` | Perovskite Tandem Solar | Multi-Source | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-05` | EU AI Act 2024 Provisions | Time-Sensitive | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-06` | Fictitious / Proprietary Secrets | Insufficient Evid | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-07` | Is Python better than Go? | Ambiguous | *Not Run* | - | - | - | - | - | Requires live API keys |
| `TC-08` | Apache Iceberg vs Delta Lake | Failure Resilience| *Not Run* | - | - | - | - | - | Requires live API keys |

*Note: In accordance with project integrity standards, live evaluation tests are marked "Not Run" until executed with active live credentials.*
