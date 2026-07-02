"""
make_participant_list.py

Splits the combined videos CSV + test-order CSV (as downloaded from the
Proliferate dashboard) into one small CSV pair per participant, plus a
participants.txt index for the SLURM array.

Doing this ONCE up front (rather than having every array task filter the
full combined CSV itself) means each of the (possibly 200+) array tasks
only ever reads its own small file, instead of every task separately
re-parsing the full multi-hundred-MB videos CSV.

Usage:
    python make_participant_list.py <videos_csv> <test_order_csv> [participants_dir] [participants_txt]
"""
import sys
import os
import pandas as pd


def main():
    if len(sys.argv) < 3:
        print("Usage: python make_participant_list.py <videos_csv> <test_order_csv> [participants_dir] [participants_txt]")
        sys.exit(1)

    videos_csv = sys.argv[1]
    test_order_csv = sys.argv[2]
    participants_dir = sys.argv[3] if len(sys.argv) > 3 else "participants"
    participants_txt = sys.argv[4] if len(sys.argv) > 4 else "participants.txt"

    os.makedirs(participants_dir, exist_ok=True)

    videos_df = pd.read_csv(videos_csv)
    test_order_df = pd.read_csv(test_order_csv)

    videos_df["workerid"] = videos_df["workerid"].astype(str)
    test_order_df["workerid"] = test_order_df["workerid"].astype(str)

    worker_ids = sorted(set(videos_df["workerid"]) | set(test_order_df["workerid"]))

    missing_videos = []
    missing_test_order = []
    valid_ids = []

    for wid in worker_ids:
        v_rows = videos_df[videos_df["workerid"] == wid]
        t_rows = test_order_df[test_order_df["workerid"] == wid]

        if v_rows.empty:
            missing_videos.append(wid)
            continue

        if t_rows.empty:
            missing_test_order.append(wid)

        v_rows.to_csv(os.path.join(participants_dir, f"{wid}_videos.csv"), index=False)
        t_rows.to_csv(os.path.join(participants_dir, f"{wid}_test_order.csv"), index=False)
        valid_ids.append(wid)

    with open(participants_txt, "w", encoding="utf-8") as f:
        for wid in valid_ids:
            f.write(wid + "\n")

    print(f"Wrote {len(valid_ids)} participant CSV pairs to {participants_dir}/")
    print(f"Wrote {len(valid_ids)} participant IDs to {participants_txt}")
    print(f"Use this for the SLURM array range: --array=0-{len(valid_ids) - 1}")
    if missing_videos:
        print(f"WARNING: {len(missing_videos)} workerid(s) had test_order rows but no video rows (skipped entirely): {missing_videos}")
    if missing_test_order:
        print(f"WARNING: {len(missing_test_order)} workerid(s) had video rows but no test_order rows (condition will show as 'unknown'): {missing_test_order}")


if __name__ == "__main__":
    main()
