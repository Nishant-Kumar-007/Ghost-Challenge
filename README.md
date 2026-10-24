# HackerRank Orchestrate (October 2026) — Ghost Data Still Exists

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Audit%20Accuracy-100%25%20(32%2F32)-success.svg)]()
[![Validation](https://img.shields.io/badge/16--Point%20Validator-PASSED-success.svg)]()

> **Production Deletion-Audit Engine & Remediation Planner**  
> Challenge URL: [HackerRank Orchestrate October 2026 — Ghost Data Still Exists](https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists)  
> Submission Repository: [https://github.com/Nishant-Kumar-007/Ghost-Challenge](https://github.com/Nishant-Kumar-007/Ghost-Challenge)

---

## 1. Overview & Problem Statement

In modern distributed commerce platforms, deletion workflows frequently claim **`COMPLETE`** while personal data persists across secondary read replicas, unpurged search indexes, customer service attachments, telemetry and observability logs, backup archives, or data export caches. Furthermore, active database synchronization connectors and backup restore jobs introduce data recreation risks.

This solution implements an autonomous, AI-ready deletion-audit agent that:
1. **Verifies Deletion Authorization:** Inspects request text across multiple languages to filter non-deletion requests (`NOT_APPLICABLE`).
2. **Reconstructs Identities:** Resolves current and historical identifiers across audit histories (`user_audit_log.csv` and `user_identities.csv`).
3. **Reconstructs Temporal Cutoff State:** Ingests and correlates multi-modal evidence across 94 files strictly enforcing `captured_at <= audit_at`.
4. **Applies Policy Rules Deterministically:** Maps observed evidence to Deletion Rules 01–15 (`DELETE`, `REDACT`, `ANONYMIZE`, `RETAIN`, `DISABLE`, `BLOCK`).
5. **Generates Dependency-Aware Remediation Plans:** Generates topologically sorted findings, safe remediation sequences (disabling replication and restore flows before record modification), and post-remediation verification checks.
6. **Produces Compliant Predictions:** Writes the official `output.csv` for all 518 evaluation requests in ~1 second.

---

## 2. Solution Architecture

The system is organized into modular subsystems with zero circular dependencies:

```
HackerRank Orchestrate — Ghost Data Still Exists
├── code/
│   ├── identity/
│   │   ├── resolver.py              # Bidirectional current & historical identity resolution
│   │   └── __init__.py
│   ├── classification/
│   │   ├── classifier.py            # Multilingual intent classification & morphological stemming
│   │   └── __init__.py
│   ├── evidence/
│   │   ├── ingestion.py             # Multi-modal evidence parser (SQL, JSON, LOG, PDF, TXT)
│   │   ├── indexer.py               # In-memory SQLite relational index with temporal filtering
│   │   ├── provenance.py            # Grounded citation verifier for participant-visible evidence
│   │   └── __init__.py
│   ├── audit/
│   │   ├── state_reconstruction.py  # Ground-truth state reconstruction at audit_at
│   │   ├── policy_evaluator.py      # Policy engine mapping categories to Rules 01–15
│   │   ├── remediation_planner.py   # Topological dependency sorting & consecutive numbering
│   │   └── __init__.py
│   ├── validation/
│   │   ├── validator.py             # Automated 16-point contract verification suite
│   │   └── __init__.py
│   ├── evaluation/
│   │   ├── main.py                  # Evaluation benchmark runner & report generator
│   │   ├── custom_test_cases.json   # 5 participant-created custom boundary test cases
│   │   ├── evaluation_report.md     # Official evaluation metrics & root-cause diagnostics
│   │   └── usage_report.md          # Real model usage, token accounting, and cost metrics
│   ├── main.py                      # Production entry point: audits all 518 cases -> output.csv
│   └── __init__.py
├── evaluation/                      # Mirrored reports for competition submission packaging
│   ├── custom_test_cases.json
│   ├── evaluation_report.md
│   └── usage_report.md
├── dataset/                         # Participant-facing evaluation inputs and evidence files
├── output.csv                       # Final verified submission predictions (518 cases)
├── log.txt                          # AGENTS.md compliant turn transcript
├── README.md                        # Documentation and run instructions
└── code.zip                         # Evaluator submission bundle
```

### Module Responsibilities:

| Module | Core Functionality |
|---|---|
| [`code/identity/resolver.py`](code/identity/resolver.py) | Follows historical identity change graphs in `user_audit_log.csv` and snapshots in `user_identities.csv`. Resolves historical email addresses used in 19.3% of deletion requests without relying on fuzzy matching. |
| [`code/classification/classifier.py`](code/classification/classifier.py) | Analyzes `request_text` across 7 languages using morphological root stems (`delet`, `suppress`, `eras`, `lösch`, etc.). Accurately classifies non-deletion requests (e.g. data access, export, rectification) as `NOT_APPLICABLE` with `steps_json = []`. |
| [`code/evidence/ingestion.py`](code/evidence/ingestion.py) | Ingests all 94 multi-modal evidence files under `dataset/evidence/`. Recursively unpacks nested JSON document structures inside SQL replica tables and correlates distributed observability trace contexts across multiple log lines. |
| [`code/evidence/indexer.py`](code/evidence/indexer.py) | Centralizes all evidence in an indexed in-memory SQLite store. Queries evidence matching user identifiers (`user_id`, `email`, `phone`, `email_hash`, `resource_id`) strictly filtering `captured_at <= audit_at`. |
| [`code/audit/policy_evaluator.py`](code/audit/policy_evaluator.py) | Implements Rules 01–15 from `dataset/deletion_rules.csv`. Enforces mandatory retention for security audit logs (Rule 12) and legal holds (Rule 13), redacts prohibited identifiers for account tombstones (Rule 15), and identifies active sync/restore risks. |
| [`code/audit/remediation_planner.py`](code/audit/remediation_planner.py) | Performs topological dependency sorting: `FINDING` $\to$ `REMEDIATION` $\to$ `VERIFICATION`. Within remediation, orders `DISABLE_DATA_FLOW` (rank 1) and `BLOCK_RESTORE` (rank 2) before record modifications (`DELETE_RECORD`, `REDACT_RECORD`, `ANONYMIZE_RECORD`). Sorts ties by `system_id` and `resource_id`. Numbering is consecutive 1-indexed. |
| [`code/validation/validator.py`](code/validation/validator.py) | 16-point automated verifier validating row count (518), sorting, valid statuses, consecutive numbering, permitted operations, valid states, dependency priority, evidence provenance against `evidence_files.csv`, and temporal cutoff enforcement. |

---

## 3. Prerequisites & Installation

### Prerequisites
- **Python:** Version 3.8, 3.9, 3.10, 3.11, or 3.12.
- **Operating System:** Platform independent (Windows, macOS, Linux).
- **External Dependencies:** **Zero external packages required.** The entire solution is engineered using Python's high-performance standard library (`sqlite3`, `json`, `csv`, `re`, `datetime`, `os`, `sys`, `zipfile`).

### Installation
Clone the repository and enter the directory:
```bash
git clone https://github.com/Nishant-Kumar-007/Ghost-Challenge.git
cd Ghost-Challenge
```

Verify Python installation:
```bash
python --version
```

---

## 4. Configuration & Security

- **Zero-Secret Core:** The core audit engine executes locally and deterministically without requiring API keys, cloud credentials, or internet access.
- **Environment Variables:** If external LLM providers or vision adapters are configured for experimental extraction, credentials must be supplied via standard environment variables:
  ```bash
  export GEMINI_API_KEY="your-gemini-key"
  export OPENAI_API_KEY="your-openai-key"
  ```
- **Secret Redaction:** In strict compliance with competition rules, no credentials, API keys, or private tokens are stored in source code, committed to Git, or written into `log.txt`.

---

## 5. Execution & Verification

### Step 1: Run Full Deletion Audit Pipeline (All 518 Cases)
Execute the main entry point from the repository root:
```bash
python code/main.py
```
**Expected Output:**
```text
=== Ghost Data Still Exists: Starting Deletion Audit Pipeline ===
Initializing engine and indexing evidence...
Evidence indexed in 0.75s
Processing 518 requests from dataset/deletion_requests.csv...
Audited 518 cases in 0.54s (1.0ms/case)
Status distribution: {'COMPLETE': 183, 'INCOMPLETE': 330, 'NOT_APPLICABLE': 5}
Saved 518 predictions to output.csv
VALIDATION PASSED: output.csv strictly conforms to all challenge contracts.
Pipeline completed successfully in 1.41s
```
This generates the final, verified [`output.csv`](output.csv) at the repository root.

---

### Step 2: Run Evaluation Benchmarks & Generate Reports
Execute the evaluation harness to test the public benchmark (32 sample cases), evaluate the 5 custom boundary cases, and generate formal markdown reports:
```bash
python code/evaluation/main.py
```
**Expected Output:**
```text
=== Ghost Data Still Exists: Running Evaluation & Usage Reporting ===
Evaluating sample benchmark against dataset/sample_output.csv...
Case Status Accuracy: 32/32 (100.0%)
Step Precision: 98.8%, Recall: 81.9%, F1: 89.5%
Evaluating 5 participant-created custom test cases...
  [PASS] custom_case_non_deletion: expected NOT_APPLICABLE, got NOT_APPLICABLE
  [PASS] custom_case_historical_identity: expected INCOMPLETE, got INCOMPLETE
  [PASS] custom_case_recreation_risk: expected INCOMPLETE, got INCOMPLETE
  [PASS] custom_case_retention_exception: expected COMPLETE, got COMPLETE
  [PASS] custom_case_post_cutoff_evidence: expected COMPLETE, got COMPLETE
Generated code\evaluation\evaluation_report.md
Generated evaluation\evaluation_report.md
Generated code\evaluation\usage_report.md
Generated evaluation\usage_report.md
Evaluation & Reporting completed successfully in 1.50s
```

---

## 6. Multi-Modal Evidence Processing Approach

The dataset provides 94 heterogeneous evidence files under `dataset/evidence/` across multiple enterprise systems:

1. **Relational Database Snapshots (`.sql`):**
   - Ingested via SQLite in-memory execution.
   - Specifically handles **replication drift**: compares primary customer databases against read replicas and regional databases.
   - Detects nested JSON structures (e.g., `record_json` containing a nested `"document"` key) and extracts embedded personal data.
2. **Distributed System Observability Logs (`.log`):**
   - Employs a **two-pass trace correlation engine**.
   - Pass 1: Scans all log entries to map query lookups (`lookup_key`) and identity tokens to their distributed `trace_id`.
   - Pass 2: Merges trace context with completed operation events and extracts user IDs, email addresses, and timestamps.
3. **Structured Service Snapshots (`.json`):**
   - Recursively traverses search index records, export bundles, and cache dumps.
4. **Documents & Attachments (`.pdf`, `.png`, `.txt`):**
   - Parses business metadata, support handover notes, and ticket attachments for exposed PII.
5. **System Activity Logs (`system_activity.csv`):**
   - Correlates global workflow claims with grounded physical evidence.
   - Flags active replication connectors (`REPORT_ACTIVE_DATA_FLOW`) and backup restore jobs (`REPORT_RESTORE_RISK`).

---

## 7. Submission Artifacts & Packaging

The official submission requires four distinct deliverables:

| Deliverable | Location | Description |
|---|---|---|
| **Predictions** | `output.csv` (repository root) | Exactly 518 data rows sorted by `case_id` conforming to `case_id,deletion_status,steps_json`. |
| **Code Archive** | `code.zip` (repository root) | Runnable code, `README.md`, configuration, and both evaluation reports. Excludes `dataset/`, `.venv`, and `__pycache__`. |
| **Chat Transcript** | `log.txt` (repository root) | Verbatim turn-by-turn development log following `AGENTS.md` §5.1 & §5.2. |
| **Agent Trace Archive** | `agent-trace.zip` (repository root) | Complete Antigravity conversation and tool execution history. |

### Creating and Verifying `code.zip`:

To package `code.zip` cleanly across platforms:

**Python (Cross-Platform Recommended):**
```bash
python -c "import zipfile, os; z = zipfile.ZipFile('code.zip', 'w', zipfile.ZIP_DEFLATED); z.write('README.md', 'README.md'); [z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), '.').replace('\\\\', '/')) for r, d, fs in os.walk('code') if '__pycache__' not in r for f in fs if not f.endswith(('.pyc', '.pyo'))]; [z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), '.').replace('\\\\', '/')) for r, d, fs in os.walk('evaluation') if '__pycache__' not in r for f in fs if not f.endswith(('.pyc', '.pyo'))]; z.close(); print('code.zip packaged successfully')"
```

**PowerShell (Windows):**
```powershell
Get-ChildItem -Path code, evaluation -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force
Compress-Archive -Path README.md, code, evaluation -DestinationPath code.zip -Force
```

**Bash (Linux / macOS):**
```bash
zip -r code.zip README.md code evaluation -x "*/__pycache__/*" "*/.venv/*" "*/.git/*" "*/.DS_Store"
```

### Verification Checklist:
Run the verification check to ensure required files are present and prohibited files are absent:
```bash
python -c "import zipfile; z = zipfile.ZipFile('code.zip'); files = z.namelist(); assert 'README.md' in files; assert 'code/main.py' in files; assert 'code/evaluation/evaluation_report.md' in files; assert 'code/evaluation/usage_report.md' in files; assert not any(f.startswith('dataset') or '.venv' in f or '__pycache__' in f or f.endswith('.zip') for f in files); print('VERIFICATION PASSED: code.zip is strictly compliant.')"
```

---

## 8. Known Limitations & Extensibility

1. **OCR / Vision Dependencies:** The parser relies on structured text headers, XML/text streams, and OCR metadata provided within the challenge evidence directory. In an unconstrained enterprise deployment, a multimodal vision model (e.g. Gemini 1.5 Pro) can be plugged in via `code/evidence/ingestion.py` for arbitrary raw document images.
2. **Deletion Rules:** The policy evaluator directly implements Rules 01–15 as defined in `dataset/deletion_rules.csv`. New jurisdictional rules (e.g. CCPA, HIPAA, LGPD) can be dynamically registered in `code/audit/policy_evaluator.py`.
3. **Deterministic Performance:** Because the prediction pipeline runs as a deterministic local state machine, external model inference costs are $0.00, enabling continuous regression testing without token budget constraints.

---

## 9. Official Contest Submission Link

The official October 2026 challenge submission URL is:  
👉 **[https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists](https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists)**
