"""
merge_results.py

Combines the per-participant CSVs produced by the SLURM array
(results/mediapipe_summary_<workerid>.csv, one per participant) into a
single combined CSV for the whole study, and reports any participants
whose output is missing (failed job, still queued, etc.).

Usage:
    python merge_results.py <results_dir> <participants_txt> [output_csv]
"""
import os
import sys
import glob
import pandas as pd


def main():
    if len(sys.argv) < 3:
        print("Usage: python merge_results.py <results_dir> <participants_txt> [output_csv]")
        sys.exit(1)

    results_dir = sys.argv[1]
    participants_txt = sys.argv[2]
    out_csv = sys.argv[3] if len(sys.argv) > 3 else "mediapipe_summary_combined.csv"

    with open(participants_txt, encoding="utf-8") as f:
        expected = [line.strip() for line in f if line.strip()]

    csv_files = glob.glob(os.path.join(results_dir, "mediapipe_summary_*.csv"))
    csv_files = [c for c in csv_files if not os.path.basename(c).startswith("mediapipe_summary_combined")]

    frames = []
    found_ids = set()
    for c in csv_files:
        try:
            df = pd.read_csv(c)
            frames.append(df)
            found_ids.update(df["ParticipantID"].astype(str).unique())
        except Exception as e:
            print(f"Warning: could not read {c}: {e}")

    if not frames:
        print("No per-participant CSVs found yet - has the array job finished?")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(by=["ParticipantID", "TrialIndex"])
    combined.to_csv(out_csv, index=False)

    missing = [w for w in expected if w not in found_ids]

    print(f"Combined {len(frames)} per-participant CSVs ({len(combined)} rows) -> {out_csv}")
    print(f"Participants expected: {len(expected)} | found: {len(found_ids)} | missing: {len(missing)}")
    if missing:
        print("Missing participant IDs (check their array task logs):")
        for m in missing:
            print(f"  {m}")


if __name__ == "__main__":
    main()
