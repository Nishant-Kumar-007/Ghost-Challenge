"""
Ghost Data Still Exists — Autonomous Deletion-Audit Dashboard Demo
==================================================================
Standalone, read-only visualization prototype for auditing GDPR/CCPA
data erasure compliance, remaining ghost records, and recreation risks.

CRITICAL: Read-only demonstration UI. Does not modify backend files.
"""

import os
import csv
import json
import pandas as pd
import streamlit as st

# Configure page metadata
st.set_page_config(
    page_title="Ghost Data Still Exists | Deletion Audit Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom minimal audit styling
st.markdown("""
<style>
    /* Clean audit dashboard typography & colors */
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .badge-complete {
        background-color: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }
    .badge-incomplete {
        background-color: #fffbeb;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-na {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
    }
    .phase-finding {
        color: #1e40af;
        background-color: #eff6ff;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .phase-remediation {
        color: #b45309;
        background-color: #fffbeb;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .phase-verification {
        color: #047857;
        background-color: #ecfdf5;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .mono-text {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_evidence_manifest(repo_root: str):
    """Loads evidence manifest mapping in read-only mode if available."""
    manifest_path = os.path.join(repo_root, "dataset", "evidence_files.csv")
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    manifest[r["file_id"]] = r
        except Exception:
            pass
    return manifest


@st.cache_data
def load_request_metadata(repo_root: str):
    """Loads deletion request context in read-only mode if available."""
    meta = {}
    for fn in ["deletion_requests.csv", "sample_deletion_requests.csv"]:
        fp = os.path.join(repo_root, "dataset", fn)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        meta[r["case_id"]] = r
            except Exception:
                pass
    return meta


def parse_output_data(file_source):
    """Parses output CSV from file path or uploaded file object in read-only mode."""
    rows = []
    if isinstance(file_source, str):
        if not os.path.exists(file_source):
            return []
        with open(file_source, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    else:
        # Uploaded file buffer
        content = file_source.getvalue().decode("utf-8")
        reader = csv.DictReader(content.splitlines())
        for r in reader:
            rows.append(r)

    parsed = []
    for r in rows:
        cid = r.get("case_id", "").strip()
        status = r.get("deletion_status", "").strip()
        raw_steps = r.get("steps_json", "[]").strip()
        try:
            steps = json.loads(raw_steps)
        except Exception:
            steps = []
        parsed.append({
            "case_id": cid,
            "deletion_status": status,
            "steps": steps,
            "step_count": len(steps)
        })
    return parsed


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    evidence_manifest = load_evidence_manifest(repo_root)
    request_metadata = load_request_metadata(repo_root)

    # Sidebar: Data Source Selection
    st.sidebar.title("🛡️ Audit Engine Demo")
    st.sidebar.caption("Ghost Data Still Exists | Orchestrate 2026")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Source")
    data_source_mode = st.sidebar.radio(
        "Select Dataset:",
        [
            "Root Evaluation Run (output.csv)",
            "Public Sample Dataset (dataset/sample_output.csv)",
            "Upload Custom Output CSV"
        ]
    )

    data_rows = []
    dataset_label = ""
    is_demo_sample = False

    if data_source_mode == "Root Evaluation Run (output.csv)":
        path = os.path.join(repo_root, "output.csv")
        data_rows = parse_output_data(path)
        dataset_label = "Official Full Evaluation Run (518 Cases)"
    elif data_source_mode == "Public Sample Dataset (dataset/sample_output.csv)":
        path = os.path.join(repo_root, "dataset", "sample_output.csv")
        data_rows = parse_output_data(path)
        dataset_label = "Public Sample Benchmark (32 Demonstration Cases)"
        is_demo_sample = True
    else:
        uploaded_file = st.sidebar.file_uploader("Upload output.csv", type=["csv"])
        if uploaded_file is not None:
            data_rows = parse_output_data(uploaded_file)
            dataset_label = f"Uploaded File: {uploaded_file.name} ({len(data_rows)} Cases)"
        else:
            st.info("Please upload an output.csv file to inspect audit results.")
            return

    if not data_rows:
        st.warning(f"No valid case data found for {data_source_mode}.")
        return

    # Banner for demonstration dataset
    if is_demo_sample:
        st.info("ℹ️ **Demonstration Mode:** Currently inspecting `dataset/sample_output.csv` (Public reference dataset).")

    # Header section
    st.title("Data Deletion Audit & Remediation Dashboard")
    st.markdown(
        "Automated verification of GDPR/CCPA data erasure across databases, read replicas, search indexes, "
        "support attachments, and distributed observability logs."
    )

    # 1. Overview Metrics Cards
    total_cases = len(data_rows)
    complete_count = sum(1 for r in data_rows if r["deletion_status"] == "COMPLETE")
    incomplete_count = sum(1 for r in data_rows if r["deletion_status"] == "INCOMPLETE")
    na_count = sum(1 for r in data_rows if r["deletion_status"] == "NOT_APPLICABLE")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Cases Audited", f"{total_cases:,}", help="Total number of evaluated deletion requests")
    with m2:
        pct_c = (complete_count / max(total_cases, 1)) * 100
        st.metric("Complete Deletions", f"{complete_count:,}", f"{pct_c:.1f}%")
    with m3:
        pct_i = (incomplete_count / max(total_cases, 1)) * 100
        st.metric("Incomplete (Ghost Data)", f"{incomplete_count:,}", f"{pct_i:.1f}%", delta_color="inverse")
    with m4:
        pct_na = (na_count / max(total_cases, 1)) * 100
        st.metric("Not Applicable (Non-Erasure)", f"{na_count:,}", f"{pct_na:.1f}%", delta_color="off")

    st.markdown("---")

    # 2. Case Explorer & Filter Section
    st.subheader("Case Explorer")
    f_col1, f_col2, f_col3 = st.columns([2, 2, 4])
    with f_col1:
        status_filter = st.selectbox(
            "Filter by Status:",
            ["ALL", "COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"],
            index=0
        )
    with f_col2:
        search_query = st.text_input("Search Case ID / Keywords:", "").strip().lower()

    # Filter rows
    filtered_rows = data_rows
    if status_filter != "ALL":
        filtered_rows = [r for r in filtered_rows if r["deletion_status"] == status_filter]
    if search_query:
        filtered_rows = [
            r for r in filtered_rows
            if search_query in r["case_id"].lower()
            or any(search_query in str(step).lower() for step in r["steps"])
        ]

    st.caption(f"Displaying **{len(filtered_rows)}** of **{total_cases}** cases from *{dataset_label}*")

    # Table preview & selection
    if not filtered_rows:
        st.warning("No cases match the selected filter criteria.")
        return

    table_data = []
    for r in filtered_rows:
        meta = request_metadata.get(r["case_id"], {})
        table_data.append({
            "Case ID": r["case_id"],
            "Deletion Status": r["deletion_status"],
            "Steps Count": r["step_count"],
            "Supplied Email": meta.get("email", "—"),
            "Reported Status": meta.get("reported_status", "—"),
            "Audit Cutoff": meta.get("audit_at", "—")
        })

    df = pd.DataFrame(table_data)

    # Explorer layout: Master table on top, Case details below
    case_ids = [r["case_id"] for r in filtered_rows]
    selected_case_id = st.selectbox("Select Case to Inspect:", case_ids, index=0)

    selected_case = next((r for r in data_rows if r["case_id"] == selected_case_id), None)

    if selected_case:
        st.markdown("---")
        # 3. Case Details Section
        st.subheader(f"Case Inspection: `{selected_case['case_id']}`")

        c_meta = request_metadata.get(selected_case_id, {})
        status = selected_case["deletion_status"]

        # Status badge formatting
        if status == "COMPLETE":
            badge_html = '<span class="status-badge badge-complete">COMPLETE — Data Erasure Verified</span>'
        elif status == "INCOMPLETE":
            badge_html = '<span class="status-badge badge-incomplete">INCOMPLETE — Ghost Records / Risks Found</span>'
        else:
            badge_html = '<span class="status-badge badge-na">NOT_APPLICABLE — Non-Deletion Request</span>'

        st.markdown(f"### Verdict: {badge_html}", unsafe_allow_html=True)

        # Context details
        if c_meta:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"**Supplied Email:** `{c_meta.get('email', 'N/A')}`")
                st.markdown(f"**Requested At:** `{c_meta.get('requested_at', 'N/A')}`")
            with col_b:
                st.markdown(f"**Reported Status:** `{c_meta.get('reported_status', 'N/A')}`")
                st.markdown(f"**Reported At:** `{c_meta.get('reported_at', 'N/A')}`")
            with col_c:
                st.markdown(f"**Audit Cutoff (`audit_at`):** `{c_meta.get('audit_at', 'N/A')}`")

            req_text = c_meta.get("request_text", "")
            if req_text:
                st.info(f"**Request Text:** *\"{req_text}\"*")

        # Steps Breakdown
        steps = selected_case["steps"]
        st.markdown(f"#### Audit Action Plan & Steps ({len(steps)} Steps)")

        if not steps:
            if status == "NOT_APPLICABLE":
                st.write("*(No remediation or verification steps required for non-deletion requests. Output is an empty array `[]` as mandated by contract.)*")
            else:
                st.write("*(Zero steps recorded for this case)*")
        else:
            # Render ordered steps cleanly
            step_table = []
            for s in steps:
                phase = s.get("phase", "")
                step_table.append({
                    "Step": s.get("step_no", 0),
                    "Phase": phase,
                    "System ID": s.get("system_id", ""),
                    "Resource ID": s.get("resource_id", ""),
                    "Operation": s.get("operation", ""),
                    "State": s.get("state", ""),
                    "Evidence ID": s.get("evidence_id", "") or "—"
                })

            st.dataframe(pd.DataFrame(step_table), use_container_width=True, hide_index=True)

            # 4. Evidence References Section
            evidence_ids = [s.get("evidence_id") for s in steps if s.get("evidence_id")]
            unique_evidence = sorted(list(set(evidence_ids)))

            if unique_evidence:
                st.markdown("#### Evidence Citations & Provenance")
                ev_cols = st.columns(min(len(unique_evidence), 4))
                for idx, ev_id in enumerate(unique_evidence):
                    with ev_cols[idx % min(len(unique_evidence), 4)]:
                        ev_info = evidence_manifest.get(ev_id, {})
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>Citation:</strong> <code>{ev_id}</code><br/>
                            <small><strong>Origin:</strong> {ev_info.get('origin_service', 'Grounded Artifact')}</small><br/>
                            <small><strong>File:</strong> <code>{ev_info.get('file_path', 'evidence artifact')}</code></small><br/>
                            <small><strong>Captured:</strong> {ev_info.get('captured_at', 'Pre-cutoff')}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                if status == "INCOMPLETE":
                    st.caption("*(Proposed remediation and future verification checks use empty evidence IDs as mandated by contract.)*")

        # Raw JSON expander for auditors
        with st.expander("View Raw JSON Output (`steps_json`)"):
            st.code(json.dumps(steps, indent=2), language="json")


if __name__ == "__main__":
    main()
