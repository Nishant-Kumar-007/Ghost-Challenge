# Ghost Data Still Exists — Standalone Demo Prototype

This directory contains a lightweight, read-only demonstration UI for **Ghost Data Still Exists**, an AI-powered data deletion audit and remediation planning platform.

> **CRITICAL ARCHITECTURAL ISOLATION:**  
> This demo dashboard is completely isolated from the challenge backend and evaluation engine. It operates in **read-only mode**, never modifies backend code, and never alters or overwrites `output.csv`, `log.txt`, `code/`, or evaluation reports.

---

## 1. Features

- **Audit Overview:** Visual summary of Total Cases, Complete Deletions, Incomplete (Ghost Data) Cases, and Not Applicable (Non-Erasure) Requests.
- **Case Explorer:** Filter cases by deletion status (`COMPLETE`, `INCOMPLETE`, `NOT_APPLICABLE`) and search by Case ID or keywords.
- **Deep Case Inspection:** Displays selected case metadata, deletion verdict, request text, and ordered action steps.
- **Ordered Steps Visualization:** Clean, responsive tabular display of findings, remediation actions, and verification checks.
- **Evidence Provenance:** Inspects cited evidence identifiers (`evidence_id`), linking them to origin systems, file paths, and capture timestamps.
- **Multi-Source Data Loading:**
  - **Root Evaluation Run (`output.csv`):** Live audit results across all 518 cases.
  - **Demonstration Mode (`dataset/sample_output.csv`):** Public reference sample dataset (32 cases), clearly labeled as a demonstration.
  - **Custom File Upload:** Upload any valid `output.csv` for immediate visual audit inspection.

---

## 2. Prerequisites & Installation

The prototype requires Python 3.8+ and Streamlit. Dependencies are isolated in `demo/requirements.txt`:

```bash
# Navigate to the repository root
cd "HackerRank Orchestrate Oct Edition"

# Install demo dependencies
pip install -r demo/requirements.txt
```

---

## 3. Running the Demo Dashboard

Launch the Streamlit app from the repository root:

```bash
streamlit run demo/app.py
```

Streamlit will automatically open the dashboard in your default browser at `http://localhost:8501`.

---

## 4. Design & Aesthetics

The UI follows a restrained, professional audit-dashboard design:
- Neutral background palettes and clean card borders.
- Restrained, accessible status indicators:
  - **`COMPLETE`**: Forest green badge indicating confirmed data erasure.
  - **`INCOMPLETE`**: Amber badge highlighting detected ghost records or sync/restore risks.
  - **`NOT_APPLICABLE`**: Slate gray badge indicating non-deletion requests (access, export, rectification).
- Monospaced typography for system IDs, resource IDs, and evidence references.
- Zero unnecessary animations or distracting charts.
