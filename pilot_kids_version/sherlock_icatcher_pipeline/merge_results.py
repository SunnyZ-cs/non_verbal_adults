"""
merge_results.py

Combines the per-participant CSVs produced by the SLURM array
(results/icatcher_summary_<uuid>.csv, one per participant) into a single
combined CSV for the whole study, and reports any participants whose
output is missing (failed job, still queued, etc.).

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
    out_csv = sys.argv[3] if len(sys.argv) > 3 else "icatcher_summary_combined.csv"

    with open(participants_txt, encoding="utf-8") as f:
        expected = [line.strip() for line in f if line.strip()]

    csv_files = glob.glob(os.path.join(results_dir, "icatcher_summary_*.csv"))
    csv_files = [c for c in csv_files if not os.path.basename(c).startswith("icatcher_summary_all")]

    frames = []
    found_uuids = set()
    for c in csv_files:
        try:
            df = pd.read_csv(c)
            frames.append(df)
            found_uuids.update(df["Response UUID"].astype(str).unique())
        except Exception as e:
            print(f"Warning: could not read {c}: {e}")

    if not frames:
        print("No per-participant CSVs found yet — has the array job finished?")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(by=["Response UUID", "Frame Index"])
    combined.to_csv(out_csv, index=False)

    missing = [u for u in expected if u not in found_uuids]

    print(f"Combined {len(frames)} per-participant CSVs ({len(combined)} rows) -> {out_csv}")
    print(f"Participants expected: {len(expected)} | found: {len(found_uuids)} | missing: {len(missing)}")
    if missing:
        print("Missing participant UUIDs (check their array task logs):")
        for m in missing:
            print(f"  {m}")


if __name__ == "__main__":
    main()
