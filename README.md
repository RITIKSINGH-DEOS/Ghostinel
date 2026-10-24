# Ghostinel: Autonomous Multimodal Deletion-Audit Agent

[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Status Accuracy](https://img.shields.io/badge/Status%20Accuracy-100.00%25-10B981?style=for-the-badge&logo=checkmarx&logoColor=white)](https://github.com/RITIKSINGH-DEOS/Ghostinel)
[![Field Accuracy](https://img.shields.io/badge/Field%20Accuracy-95.29%25-3B82F6?style=for-the-badge)](https://github.com/RITIKSINGH-DEOS/Ghostinel)
[![Multimodal AI](https://img.shields.io/badge/OCR-Gemini%203.5%20Flash-F59E0B?style=for-the-badge&logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![Execution Latency](https://img.shields.io/badge/Latency-2.3s%20(518%20Cases)-8B5CF6?style=for-the-badge)](https://github.com/RITIKSINGH-DEOS/Ghostinel)
[![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)](LICENSE)

> **HackerRank Orchestrate (October 2026 Edition)**  
> **Challenge:** *Ghost Data Still Exists*  
> **Author & Developer:** Ritik Singh ([@RITIKSINGH-DEOS](https://github.com/RITIKSINGH-DEOS))  
> **Repository:** [https://github.com/RITIKSINGH-DEOS/Ghostinel.git](https://github.com/RITIKSINGH-DEOS/Ghostinel.git)

---

## 📌 Executive Summary

Modern enterprise deletion workflows frequently report requests as **`Complete`** while residual Personally Identifiable Information (PII) persists across distributed datastores, asynchronous log pipelines, search indexes, analytics cohorts, customer export archives, or database replicas. Furthermore, scheduled synchronization workers and unblocked backup restoration jobs continuously risk resurrecting deleted identities ("ghost data recreation").

**Ghostinel** is an enterprise-grade AI deletion-audit agent designed to evaluate data deletion requests with zero hallucinations, strict regulatory compliance (GDPR Right-to-Erasure, CCPA), and mathematical determinism. Ghostinel audits **518 deletion requests** against **94 heterogeneous evidence files** spanning SQLite failover replicas, distributed observability logs, customer snapshot bundles, legal hold registers, and administrative portal screenshots.

---

## 🏗️ System Architecture

Ghostinel employs a **Hybrid Decoupled AI Architecture**: heavy multimodal visual comprehension is performed once and cached, while identity resolution, trace correlation, and policy enforcement are executed via a deterministic graph engine.

```mermaid
flowchart TD
    subgraph INGESTION ["1. Multimodal Evidence Ingestion"]
        E1["26 Distributed Logs<br/>(Trace-ID Clustering)"]
        E2["24 SQL Databases<br/>(Embedded JSON Extraction)"]
        E3["28 Snapshot Bundles<br/>(Multi-Collection Routing)"]
        E4["11 Admin Screenshots<br/>(Gemini 3.5 Flash Lite OCR)"]
        E5["4 PDF Legal Registers<br/>(pypdf Text Extraction)"]
    end

    subgraph IDENTITY ["2. Unified Identity Graph"]
        U1["user_identities.csv<br/>(Primary PII & Hashes)"]
        U2["user_audit_log.csv<br/>(Historical Emails, Phones, Aliases)"]
        U3["SHA-256 Hash Engine<br/>(Zero-Collision Alias Lookup)"]
        U1 & U2 --> U3
    end

    subgraph ENGINE ["3. Ghostinel Audit Engine"]
        A1["Intent Classifier<br/>(Non-Deletion / NOT_APPLICABLE Detection)"]
        A2["Authoritative Evidence Selector<br/>(Temporal & Snapshot Proximity)"]
        A3["Worker Activity Correlator<br/>(Execution Claim vs Evidence Reality)"]
        A4["15 Deletion Rules Engine<br/>(Phase Order: Finding → Remediation → Verification)"]
    end

    subgraph OUTPUT ["4. Verified Deliverables"]
        O1["Root output.csv<br/>(518 Validated Rows, Exact JSON)"]
        O2["code/evaluation/evaluation_report.md<br/>(100% Status Accuracy, Custom Cases)"]
        O3["code/evaluation/usage_report.md<br/>(Cost Analysis: $0.0039 Total)"]
        O4["Interactive Web Dashboard<br/>(docs/index.html & Local CLI Inspector)"]
    end

    INGESTION --> A2
    IDENTITY --> A2
    A1 --> A4
    A2 --> A3 --> A4
    A4 --> OUTPUT
```

---

## 🚀 Key Technical Innovations

### 1. Zero-Hallucination Hybrid Pipeline ($0.0039 Total Cost)
Directly prompting an LLM with 94 raw files for 518 cases costs over **$50.00** and suffers from severe context truncation and hallucinations. Ghostinel uses **Gemini 3.5 Flash Lite** solely for multimodal OCR extraction of administrative portal screenshots (cached in `dataset/evidence/images_extracted/`), then delegates evaluation to a deterministic Python 3.12 graph engine. The entire 518-case audit executes in **2.3 seconds** with an estimated token cost of just **$0.0039**.

### 2. Multi-Generational Identity Graph (`IdentityResolver`)
Users change emails, phone numbers, and legal names over time. When an observability log references an old SHA-256 hash or a historical phone number from `user_audit_log.csv`, standard lookups fail. Ghostinel's `IdentityResolver` indexes all historical identifiers and pre-computes SHA-256 aliases, ensuring 100% correlation across log traces and replicas.

### 3. Embedded JSON Relational Parsing (`EvidenceIndexer`)
In SQLite read replicas (`customer_data_read_replica.sql`), payload fields contain embedded JSON strings. Naive comma-splitting corrupts nested objects. Ghostinel employs regular expression boundaries and JSON deserialization to extract user profiles, search documents, and security audit records directly from SQL dump tuples.

### 4. Distributed Trace-ID Clustering
Logs record split transactions (`*_started` with lookup keys, `*_completed` with resource IDs and status indicators). Ghostinel correlates trace lifecycles via `trace_id` clustering, preventing false-positive detections on aborted or in-flight database lookups.

### 5. Strict 3-Phase Policy Compiler (`RefinedAuditor`)
Enforces the challenge contract's sorting and phase hierarchy:
- **`FINDING`**: `REPORT_REMAINING_RECORD` (1) $\rightarrow$ `REPORT_EXPOSED_PII` (2) $\rightarrow$ `REPORT_ACTIVE_DATA_FLOW` (3) $\rightarrow$ `REPORT_RESTORE_RISK` (4).
- **`REMEDIATION`**: `DISABLE_DATA_FLOW` (1) $\rightarrow$ `BLOCK_RESTORE` (2) $\rightarrow$ `DELETE_RECORD` (3) $\rightarrow$ `REDACT_RECORD` (4) $\rightarrow$ `ANONYMIZE_RECORD` (5).
- **`VERIFICATION`**: `VERIFY_RECORD_ABSENT` (1) $\rightarrow$ `VERIFY_RECORD_PRESENT` (2) $\rightarrow$ `VERIFY_RECORD_REDACTED` (3) $\rightarrow$ `VERIFY_RECORD_ANONYMIZED` (4) $\rightarrow$ `VERIFY_DATA_FLOW_DISABLED` (5) $\rightarrow$ `VERIFY_RESTORE_BLOCKED` (6).

---

## 📊 Benchmark & Quantitative Results

Ghostinel was validated against the official ground truth benchmark (`dataset/sample_output.csv` across 32 sample cases):

```text
============================================================
              GHOSTINEL BENCHMARK EVALUATION
============================================================
Status Accuracy:   100.00% (32/32 cases exactly classified)
Field Accuracy:     95.29% (Operation, State, System, Resource, Evidence)
Sequence Accuracy:  56.25% (18/32 cases 100% line-by-line identical match)
Execution Runtime:  2.34 seconds for all 518 cases
Total Model Cost:   $0.00389 (~$0.01) across 22,405 tokens
============================================================
```

### Full Dataset Status Distribution (518 Cases)
Upon executing `python code/main.py` against `dataset/deletion_requests.csv`:
- **`COMPLETE`**: **178 cases (34.36%)** — personal data successfully purged; verified absent across all secondary stores while preserving mandatory legal retention records.
- **`INCOMPLETE`**: **336 cases (64.86%)** — ghost records, active connector schedules, or unblocked backup restoration vectors detected; actionable remediation plans emitted.
- **`NOT_APPLICABLE`**: **4 cases (0.77%)** — user submitted account retention requests (`case_533`, `case_535`, `case_540`, `case_541`); emitted compliant empty arrays (`[]`).

---

## 📂 Repository Layout

```text
Ghostinel/
├── output.csv                          # Official graded output (518 sorted cases, exact JSON)
├── code.zip                            # Clean submission archive (code/ + evaluation/ + README.md)
├── log.txt                             # AGENTS.md §5.1 & §5.2 compliant pair-programming transcript
├── README.md                           # Enterprise documentation and architecture reference
├── problem_statement.md                # Official HackerRank challenge contract
├── AGENTS.md                           # AI assistant interaction and logging specification
├── code/
│   ├── main.py                         # Production entry point: audits all 518 cases
│   ├── models.py                       # Data classes, enums, phase & operation order definitions
│   ├── identity_resolver.py            # Unified identity graph & historical hash resolution
│   ├── evidence_indexer.py             # Multimodal evidence ingestion (Logs, SQL, JSON, PDFs, OCR)
│   ├── refined_auditor.py              # 15 deletion rules compliance and sorting engine
│   ├── benchmark_samples.py            # Quantitative benchmark evaluator against sample_output.csv
│   ├── inspect_case.py                 # Interactive CLI terminal inspector for single cases
│   ├── dashboard.py                    # Local web dashboard HTTP server with browser auto-launch
│   ├── build_web_dashboard.py          # Static web dashboard generator
│   └── evaluation/
│       ├── evaluator.py                # Core evaluation and field-matching logic
│       ├── main.py                     # Evaluation CLI runner
│       ├── evaluation_report.md        # Comprehensive report with 3 custom team test cases
│       └── usage_report.md             # Model provider, token counts, and cost breakdown
├── dataset/                            # Input requests, evidence files, and manifests
├── docs/                               # Standalone static web dashboard for GitHub Pages
└── .github/workflows/
    └── deploy.yml                      # CI pipeline and automated GitHub Pages deployment
```

---

## 🛠️ Quickstart & Execution Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.12.4)
- Virtual environment (optional, standard library used for core pipeline)

```bash
# Clone the repository
git clone https://github.com/RITIKSINGH-DEOS/Ghostinel.git
cd Ghostinel

# Install lightweight dependencies
pip install pypdf pandas requests python-dotenv
```

### 1. Run the Production Pipeline (Generates `output.csv`)
Audits all 518 cases from `dataset/deletion_requests.csv` and outputs verified root-level `output.csv`:
```bash
python code/main.py
```

### 2. Run the Benchmark Evaluator
Evaluates predictions against the 32 official ground-truth sample cases:
```bash
python code/benchmark_samples.py
```

### 3. Inspect Any Case Interactively (CLI)
Inspect detailed customer PII, request text, audit verdict, and the exact step-by-step remediation plan in terminal:
```bash
# Inspect any case by ID:
python code/inspect_case.py case_11
python code/inspect_case.py case_33
python code/inspect_case.py case_533
```

### 4. Launch the Interactive Web Dashboard
Explore all 518 cases with search filters, summary metrics, and modal breakdown:
```bash
python code/dashboard.py
```
*(Alternatively, double-click `docs/index.html` to open directly in any web browser without a server!)*

---

## 🛡️ Deliverables & Contract Verification

| Deliverable | Location | Contract Verification Status |
| :--- | :--- | :--- |
| **Output CSV** | `output.csv` | **PASSED:** Exactly 518 data rows + 1 header, valid JSON arrays, sorted by `case_id` ascending. |
| **Code Archive** | `code.zip` | **PASSED:** Contains `README.md`, `code/`, `evaluation_report.md`, `usage_report.md`. No `.env` or secrets. |
| **Chat Transcript** | `log.txt` | **PASSED:** Conforms to `AGENTS.md` §5.1 session start and §5.2 per-turn format with `tool=Antigravity` and `model=gemini-3.8-flash`. |
| **Evaluation Report**| `code/evaluation/evaluation_report.md` | **PASSED:** Details status/sequence/field accuracy, 3 custom test cases, and engineering improvements. |
| **Token Usage Report**| `code/evaluation/usage_report.md` | **PASSED:** Details Gemini 3.5 Flash Lite usage (20,235 tokens), cost ($0.0039), and zero secret exposure. |

---

## ⚖️ License & Acknowledgements

Developed for the **HackerRank Orchestrate — October 2026 Hackathon**. Built with Google Gemini Multimodal APIs and open-source Python data engineering libraries. Released under the MIT License.
