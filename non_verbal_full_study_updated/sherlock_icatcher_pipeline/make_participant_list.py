"""
make_participant_list.py

Generates participants.txt: one response UUID per line, sorted, derived
from the responses JSON. This file is the index for the SLURM job array -
array task N reads line N to know which participant to process.

Usage:
    python make_participant_list.py <json_path> [output_path]
"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python make_participant_list.py <json_path> [output_path]")
        sys.exit(1)

    json_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "participants.txt"

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    uuids = sorted({item.get("response", {}).get("uuid") for item in data if item.get("response", {}).get("uuid")})

    with open(out_path, "w", encoding="utf-8") as f:
        for u in uuids:
            f.write(u + "\n")

    print(f"Wrote {len(uuids)} participant UUIDs to {out_path}")
    print(f"Use this for the SLURM array range: --array=0-{len(uuids) - 1}")


if __name__ == "__main__":
    main()
