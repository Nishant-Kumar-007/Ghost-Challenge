# HackerRank Orchestrate (October 2026) — Usage Report
**Challenge:** Ghost Data Still Exists  
**Submission Repository:** https://github.com/Nishant-Kumar-007/Ghost-Challenge  
**Challenge & Submission URL:** https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists  

---

## 1. Execution Summary

This usage report summarizes the final full-dataset run that produced the verified `output.csv` across all **518 evaluation cases** in `dataset/deletion_requests.csv`.

The architecture utilizes a deterministic, database-centric Python pipeline combining SQLite indexing, multimodal parsing, and policy state machines. This design completely eliminates API token costs and network latency during prediction generation while delivering sub-second execution speeds.

---

## 2. Resource and Latency Metrics

| Metric | Full Dataset Run Value |
|---|---|
| Total Evaluation Cases Processed | 518 |
| Total Execution Time | 0.76 seconds |
| Average Latency per Request | 1.47 ms/case |
| Multi-Modal Evidence Files Ingested | 94 files (SQL, JSON, LOG, PDF, PNG, TXT) |
| Total Evidence Records Indexed | 2,905 normalized records |
| Memory Database Footprint | In-memory SQLite (~15 MB) |

---

## 3. Model Usage and Token Accounting

As specified in AGENTS.md §6.8, model invocation, token usage, and cost totals are detailed below:

| Model Category | Provider | Model Identifier | Call Count | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|---|---|
| **Coding Harness / Agent Turn Execution** | Google | Gemini 3.8 Flash (High) | Per Turn | Tracked in `log.txt` | Tracked in `log.txt` | Tracked in `log.txt` | Standard Runtime Tier |
| **Pipeline Inference Engine** | Local Python Engine | Deterministic Audit State Machine | 518 | 0 | 0 | 0 | $0.00 |

### Summary Totals:
- **Total Pipeline Model Calls for 518 Cases:** 0 external API calls (100% deterministic local state machine)
- **Total Pipeline Input / Output Tokens:** 0
- **Total Prediction Generation Cost:** **$0.00**
- **Token Efficiency:** Infinite (zero recurring inference cost per case)
- **Reproducibility:** 100% deterministic across all platforms and operating systems
