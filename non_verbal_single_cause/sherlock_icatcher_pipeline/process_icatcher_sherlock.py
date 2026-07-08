"""
process_icatcher_sherlock.py

GPU/Sherlock-array-friendly version of process_icatcher.py.

What changed vs. the original pilot_kids_version/process_icatcher.py:
  1. --gpu_id is now a CLI flag (default 0 = first GPU on the node) instead of
     being hardcoded to -1 (CPU only). This is the main reason the original
     script was never going to use a GPU even if you ran it on one.
  2. Added --uuid so a single invocation can process just ONE participant's
     videos. This lets a SLURM job array run all 73 participants in parallel
     (one array task = one participant) instead of looping serially.
  3. The webm->mp4 conversion temp folder is now unique per run (per PID),
     so multiple array tasks running at once against the same videos folder
     don't delete each other's in-progress files.
  4. Each invocation writes its own summary CSV (named after the uuid, or
     "all" if no --uuid given) instead of always overwriting
     icatcher_summary_results.csv. merge_results.py combines them afterward.
  5. Default worker count dropped from 3 to 1. On a shared GPU, running
     multiple icatcher subprocesses at once per task isn't worth the
     complexity for 2 videos/participant; sequential is safer and simpler.

Usage (single participant, what the SLURM array calls):
    python process_icatcher_sherlock.py <videos_dir> <json_path> \
        --uuid <response_uuid> --gpu_id 0 --out results/icatcher_<uuid>.csv

Usage (everything in one go, no array - matches original behavior but on GPU):
    python process_icatcher_sherlock.py <videos_dir> <json_path> --gpu_id 0
"""

import os
import sys
import glob
import re
import json
import argparse
import subprocess
import shutil
import tempfile
import concurrent.futures
import pandas as pd


def run_icatcher(video_path, output_dir, gpu_id):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"Running iCatcher+ on {os.path.basename(video_path)} (gpu_id={gpu_id})...")

    cmd = [
        "icatcher",
        video_path,
        "--output_annotation", output_dir,
        "--overwrite",
        "--gpu_id", str(gpu_id),
        "--fd_model", "opencv_dnn",
    ]

    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["VECLIB_MAXIMUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    env["TORCH_NUM_THREADS"] = "1"

    try:
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"iCatcher+ complete: {os.path.basename(video_path)}")
    except subprocess.CalledProcessError as e:
        print(f"Error running iCatcher on {os.path.basename(video_path)}: {e}")
        return None

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    expected_output_txt = os.path.join(output_dir, f"{base_name}.txt")

    if os.path.exists(expected_output_txt):
        return expected_output_txt
    else:
        print(f"Could not find expected output file: {expected_output_txt}")
        return None


def analyze_gaze(icatcher_output_file, freeze_duration=20.0, anim_duration=18.76, bullseye_duration=3.0):
    if not icatcher_output_file:
        return 0, 0, 0

    try:
        if os.path.exists(icatcher_output_file) and os.path.getsize(icatcher_output_file) == 0:
            return 0, 0, 0

        df = pd.read_csv(icatcher_output_file, header=None)
        if len(df.columns) >= 2:
            pred_series = df[1].astype(str).str.strip().str.lower()
        else:
            print(f"Unexpected column count in {icatcher_output_file}: {df.columns}")
            return 0, 0, 0
    except Exception as e:
        print(f"Failed to read {icatcher_output_file}: {e}")
        return 0, 0, 0

    if len(pred_series) > 650:
        total_duration = bullseye_duration + anim_duration + freeze_duration
        fraction_to_keep = freeze_duration / total_duration
        frames_to_keep = int(len(pred_series) * fraction_to_keep)
        if frames_to_keep > 0:
            pred_series = pred_series.tail(frames_to_keep)

    left_frames = (pred_series == 'left').sum()
    right_frames = (pred_series == 'right').sum()
    away_frames = (pred_series == 'away').sum()

    return left_frames, right_frames, away_frames


def load_test_orders(json_path):
    metadata = {}
    try:
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            resp = item.get('response', {})
            uuid = resp.get('uuid')
            if not uuid:
                continue

            child = item.get('child', {})
            age_rounded = child.get('age_rounded')
            try:
                age_days = int(age_rounded) if age_rounded else None
                age_years = round(float(age_rounded) / 365.25, 2) if age_rounded else None
            except ValueError:
                age_days = None
                age_years = None

            test_order = None
            exp_data = item.get('exp_data', [])
            for trial in exp_data:
                if 'test_order' in trial:
                    test_order = trial['test_order']
                    break

            metadata[uuid] = {
                'test_order': test_order,
                'age_days': age_days,
                'age_years': age_years,
            }
    except Exception as e:
        print(f"Error loading JSON data from {json_path}: {e}")
    return metadata


def parse_video_filename(filename):
    pattern = r"videoStream_[a-f0-9\-]+_(\d+)-start-record-plugin-multiframe_([a-f0-9\-]+)_[0-9]+_[0-9]+\.(webm|mp4)"
    match = re.match(pattern, filename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None


def prepare_videos(videos_dir, target_uuid=None):
    """
    Finds non-consent webm/mp4 videos (optionally filtered to one participant
    uuid), converts webm -> mp4 (cropped to the last 20s), and returns the
    prepared list plus a temp dir unique to this process for cleanup.
    """
    # Unique per-process temp dir so parallel array tasks never collide.
    temp_dir = tempfile.mkdtemp(prefix=f"icatcher_tmp_{os.getpid()}_", dir=videos_dir)

    all_webms = glob.glob(os.path.join(videos_dir, "*.webm"))
    all_mp4s = glob.glob(os.path.join(videos_dir, "*.mp4"))

    prepared = []
    webms_to_convert = [w for w in all_webms if not os.path.basename(w).startswith("consent-")]

    if target_uuid:
        def matches(path):
            _, uuid = parse_video_filename(os.path.basename(path))
            return uuid == target_uuid
        webms_to_convert = [w for w in webms_to_convert if matches(w)]
        all_mp4s = [m for m in all_mp4s if matches(m)]

    for webm in webms_to_convert:
        base_name = os.path.basename(webm)
        mp4_name = os.path.splitext(base_name)[0] + ".mp4"
        mp4_path = os.path.join(temp_dir, mp4_name)

        if not os.path.exists(mp4_path):
            print(f"Converting and cropping {base_name}...")
            # NOTE: libx264 is not available in Sherlock's system ffmpeg module
            # (no --enable-gpl in that build), so we use ffmpeg's built-in
            # mpeg4 encoder instead, which needs no external library.
            cmd = [
                "ffmpeg", "-y", "-ss", "21.76", "-i", webm,
                "-an", "-c:v", "mpeg4", "-q:v", "3", "-pix_fmt", "yuv420p",
                mp4_path,
            ]
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if result.returncode != 0:
                    print(f"Error converting {base_name} (exit {result.returncode}):\n{result.stdout[-2000:]}")
                    continue
            except Exception as e:
                print(f"Error converting {base_name}: {e}")
                continue

        prepared.append({"orig_name": base_name, "path": mp4_path, "is_temp": True})

    for mp4 in all_mp4s:
        base_name = os.path.basename(mp4)
        if base_name.startswith("consent-"):
            continue
        if "icatcher_tmp_" in mp4:
            continue
        prepared.append({"orig_name": base_name, "path": mp4, "is_temp": False})

    return prepared, temp_dir


def process_single_video(item, test_orders, output_dir, gpu_id, durations=None):
    video_path = item["path"]
    orig_name = item["orig_name"]

    frame_idx, resp_uuid = parse_video_filename(orig_name)
    if not resp_uuid or frame_idx is None:
        print(f"Skipping non-conforming video: {orig_name}")
        return None

    meta = test_orders.get(resp_uuid, {})
    order = meta.get('test_order')
    age_days = meta.get('age_days')
    age_years = meta.get('age_years')

    if not order or len(order) < 2:
        print(f"Warning: No test order found in JSON for response UUID {resp_uuid}. Setting condition to 'unknown'.")
        condition = "unknown"
    else:
        if frame_idx == 9:
            condition = order[0]
        elif frame_idx == 13:
            condition = order[1]
        else:
            condition = f"frame_{frame_idx}"

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    expected_output_txt = os.path.join(output_dir, f"{base_name}.txt")

    if os.path.exists(expected_output_txt) and os.path.getsize(expected_output_txt) > 0:
        print(f"Gaze prediction file already exists for {orig_name}, skipping execution.")
        output_txt = expected_output_txt
    else:
        output_txt = run_icatcher(video_path, output_dir, gpu_id)

    if output_txt:
        durations = durations or {}
        left_frames, right_frames, away_frames = analyze_gaze(output_txt, **durations)
    else:
        left_frames, right_frames, away_frames = 0, 0, 0

    return {
        "Response UUID": resp_uuid,
        "Age (Days)": age_days,
        "Age (Years)": age_years,
        "Frame Index": frame_idx,
        "Condition": condition,
        "Left Looking Frames": left_frames,
        "Right Looking Frames": right_frames,
        "Away/Other Frames": away_frames,
        "Video Filename": orig_name,
    }


def main():
    parser = argparse.ArgumentParser(description="Run iCatcher+ over study videos (Sherlock/GPU-ready).")
    parser.add_argument("videos_dir", help="Path to the videos folder")
    parser.add_argument("json_path", help="Path to the Lookit responses JSON file")
    parser.add_argument("--uuid", default=None, help="Only process this one participant (response UUID). Omit to process everyone in videos_dir.")
    parser.add_argument("--gpu_id", default=0, type=int, help="GPU device id to use (0 = first GPU allocated to this job). Use -1 for CPU.")
    parser.add_argument("--output_dir", default="icatcher_output", help="Where raw icatcher per-frame annotation files go (shared across participants is fine; filenames are unique).")
    parser.add_argument("--out", default=None, help="Path to write this run's summary CSV. Defaults to results/icatcher_summary_<uuid|all>.csv")
    parser.add_argument("--workers", default=1, type=int, help="Parallel video workers within this run (default 1; keep low on a single shared GPU).")
    parser.add_argument("--freeze_duration", default=20.0, type=float, help="Seconds of the trial's final freeze-frame window that gaze is scored over (default 20.0, matches this study's design).")
    parser.add_argument("--anim_duration", default=18.76, type=float, help="Seconds of animation preceding the freeze frame (default 18.76). Only affects how many trailing frames get kept when a video has more than 650 total frames - see analyze_gaze().")
    parser.add_argument("--bullseye_duration", default=3.0, type=float, help="Seconds of the attention-getter/bullseye at the very start of the clip (default 3.0).")
    args = parser.parse_args()

    durations = {
        "freeze_duration": args.freeze_duration,
        "anim_duration": args.anim_duration,
        "bullseye_duration": args.bullseye_duration,
    }

    videos_dir = args.videos_dir
    json_path = args.json_path

    if not os.path.isdir(videos_dir):
        print(f"Error: {videos_dir} is not a valid directory.")
        sys.exit(1)
    if not os.path.isfile(json_path):
        print(f"Error: {json_path} is not a valid file.")
        sys.exit(1)

    out_path = args.out
    if out_path is None:
        os.makedirs("results", exist_ok=True)
        out_path = os.path.join("results", f"icatcher_summary_{args.uuid or 'all'}.csv")
    else:
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    test_orders = load_test_orders(json_path)
    print(f"Loaded trial configurations for {len(test_orders)} responses from JSON.")

    prepared, temp_dir = prepare_videos(videos_dir, target_uuid=args.uuid)
    print(f"Found {len(prepared)} experimental trial videos to process.")

    if not prepared:
        print(f"No matching videos found for uuid={args.uuid!r}. Nothing to do.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(0)

    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(process_single_video, item, test_orders, args.output_dir, args.gpu_id, durations): item
                for item in prepared
            }
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    if not results:
        print("No matching video files were processed.")
        sys.exit(0)

    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values(by=["Response UUID", "Frame Index"])

    print("\n--- Summary Results ---")
    print(summary_df.to_string(index=False))

    summary_df.to_csv(out_path, index=False)
    print(f"\nSaved summary to {out_path}")


if __name__ == "__main__":
    main()
