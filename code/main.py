"""Main entry point for HackerRank Orchestrate: Ghost Data Still Exists.

Executes the deletion audit pipeline across all cases in dataset/deletion_requests.csv
and generates the verified root output.csv.
"""

import json
import os
import sys
import time
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.audit.state_reconstruction import DeletionAuditEngine
from code.validation.validator import OutputValidator


def run_pipeline(
    dataset_dir: str = "dataset",
    requests_csv: str = "dataset/deletion_requests.csv",
    output_csv: str = "output.csv"
) -> str:
    print(f"=== Ghost Data Still Exists: Starting Deletion Audit Pipeline ===")
    t0 = time.time()

    # 1. Initialize Audit Engine & Ingest Multi-Modal Evidence
    print("Initializing engine and indexing evidence...")
    engine = DeletionAuditEngine(dataset_dir)
    print(f"Evidence indexed in {time.time() - t0:.2f}s")

    # 2. Load requests
    if not os.path.exists(requests_csv):
        raise FileNotFoundError(f"Input file {requests_csv} not found")

    df_requests = pd.read_csv(requests_csv)
    total_cases = len(df_requests)
    print(f"Processing {total_cases} requests from {requests_csv}...")

    # Sort requests by case_id for deterministic processing
    df_requests = df_requests.sort_values(by="case_id").reset_index(drop=True)

    results = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    t_cases = time.time()
    for idx, row in df_requests.iterrows():
        case_id = str(row["case_id"]).strip()
        status, steps = engine.audit_case(row.to_dict())

        status_counts[status] = status_counts.get(status, 0) + 1
        steps_json = json.dumps(steps, separators=(",", ":"))

        results.append({
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": steps_json
        })

    elapsed_cases = time.time() - t_cases
    print(f"Audited {total_cases} cases in {elapsed_cases:.2f}s ({elapsed_cases/total_cases*1000:.1f}ms/case)")
    print(f"Status distribution: {status_counts}")

    # 3. Write final output.csv
    out_df = pd.DataFrame(results, columns=["case_id", "deletion_status", "steps_json"])
    out_df = out_df.sort_values(by="case_id").reset_index(drop=True)
    out_df.to_csv(output_csv, index=False)
    print(f"Saved {len(out_df)} predictions to {output_csv}")

    # 4. Strict Validation
    validator = OutputValidator(
        expected_row_count=total_cases,
        requests_csv_path=requests_csv,
        evidence_csv_path=os.path.join(dataset_dir, "evidence_files.csv")
    )
    is_valid, errors = validator.validate_file(output_csv)
    if is_valid:
        print(f"VALIDATION PASSED: {output_csv} strictly conforms to all challenge contracts.")
    else:
        print(f"VALIDATION FAILED with {len(errors)} errors:")
        for e in errors[:10]:
            print(" ", e)
        raise ValueError(f"Output validation failed: {errors[0]}")

    print(f"Pipeline completed successfully in {time.time() - t0:.2f}s")
    return output_csv


if __name__ == "__main__":
    run_pipeline()
