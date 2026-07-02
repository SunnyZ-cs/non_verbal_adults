#!/usr/bin/env python3
"""
process_videos_mediapipe_sherlock.py

Sherlock-array-friendly version of pilot_adults_version/process_videos_mediapipe.py.

The MediaPipe gaze-estimation logic itself (run_mediapipe_gaze: Face Mesh
iris landmarks, dynamic per-clip calibration, left/right/center classification)
is UNCHANGED from the original - this only restructures how the script is
invoked and how it handles I/O, so it can run as one array task per
participant on Sherlock instead of looping over every participant serially
on one machine.

What changed vs. the original process_videos_mediapipe.py:
  1. Takes a single participant's already-split videos/test_order CSVs
     (produced by make_participant_list.py) instead of the full combined
     export. This lets a SLURM job array run every participant in parallel,
     and means no array task ever has to parse the full (possibly
     hundreds-of-MB) combined videos CSV - just its own tiny slice of it.
  2. The webm->mp4 temp directory is unique per process (per PID), so
     multiple array tasks running at once never collide on temp files.
  3. libx264 swapped for the built-in `mpeg4` ffmpeg encoder. Sherlock's
     ffmpeg module has no libx264 (no --enable-gpl in that build) - this
     is the exact same issue already found and fixed in the sibling
     iCatcher+/kids pipeline, applied here proactively.
  4. Each invocation writes its own results/mediapipe_summary_<workerid>.csv
     instead of always overwriting the same mediapipe_summary_results.csv.
     merge_results.py combines them afterward.
  5. Skips re-running MediaPipe for a trial if its annotation .txt already
     exists (re-derives the frame counts from the existing file instead) -
     makes a re-submitted/retried array task resume instead of redoing work.
  6. Trial-timing constant (--crop_start) is now a CLI flag instead of a
     bare literal in the ffmpeg command, in case future versions of the
     study change clip length.

Usage (single participant, what the SLURM array calls):
    python process_videos_mediapipe_sherlock.py <participant_videos.csv> <participant_test_order.csv> \\
        --output_dir mediapipe_output --out results/mediapipe_summary_<workerid>.csv
"""

import os
import sys
import base64
import subprocess
import shutil
import argparse
import tempfile
import pandas as pd

try:
    import mediapipe as mp
except ImportError:
    print("Error: MediaPipe is not installed. Please run: pip install mediapipe")
    sys.exit(1)

try:
    import cv2
except ImportError:
    print("Error: OpenCV is not installed. Please run: pip install opencv-python-headless")
    sys.exit(1)

import numpy as np


def run_mediapipe_gaze(video_path, output_txt_path, sensitivity_offset=0.012):
    """
    Executes gaze tracking using MediaPipe Face Mesh iris landmarks on a video clip.
    Saves frame-by-frame annotations to output_txt_path.

    Unchanged from the original pilot script other than formatting.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  Error: Could not open video file '{video_path}'")
        return 0, 0, 0, 0

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 1. First pass to calculate baseline mean_ratio for this specific clip
    ratios = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            ratio_right = (landmarks[468].x - landmarks[33].x) / (landmarks[133].x - landmarks[33].x)
            ratio_left = (landmarks[473].x - landmarks[362].x) / (landmarks[263].x - landmarks[362].x)
            avg_ratio = (ratio_right + ratio_left) / 2.0
            ratios.append(avg_ratio)
    cap.release()

    if not ratios:
        print(f"  Warning: No faces detected in '{video_path}'")
        face_mesh.close()
        return 0, 0, 0, 300

    mean_ratio = np.mean(ratios)
    print(f"  Baseline calibrated: mean_ratio = {mean_ratio:.4f}, sensitivity_offset = {sensitivity_offset:.4f}")

    # 2. Second pass to annotate and count
    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    left_count = 0
    right_count = 0
    center_count = 0
    noface_count = 0
    out_lines = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            ratio_right = (landmarks[468].x - landmarks[33].x) / (landmarks[133].x - landmarks[33].x)
            ratio_left = (landmarks[473].x - landmarks[362].x) / (landmarks[263].x - landmarks[362].x)
            avg_ratio = (ratio_right + ratio_left) / 2.0

            if avg_ratio < mean_ratio - sensitivity_offset:
                gaze = "right"
                right_count += 1
            elif avg_ratio > mean_ratio + sensitivity_offset:
                gaze = "left"
                left_count += 1
            else:
                gaze = "center"
                center_count += 1

            out_lines.append(f"{frame_idx},{gaze},{avg_ratio:.4f}\n")
        else:
            noface_count += 1
            out_lines.append(f"{frame_idx},noface,-1.0000\n")

    cap.release()
    face_mesh.close()

    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    return left_count, right_count, center_count, noface_count


def count_from_annotation(txt_path):
    """Re-derive gaze counts from an already-written annotation file, so a
    re-run doesn't need to redo the actual MediaPipe inference."""
    left = right = center = noface = 0
    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            gaze = parts[1]
            if gaze == "left":
                left += 1
            elif gaze == "right":
                right += 1
            elif gaze == "center":
                center += 1
            elif gaze == "noface":
                noface += 1
    return left, right, center, noface


def decode_and_crop_video(base64_data, temp_dir, tag, crop_start):
    """Decode a base64 webm blob, ffmpeg-crop it to the freeze-frame window,
    return the resulting mp4 path, or None on failure."""
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]
    video_bytes = base64.b64decode(base64_data)

    webm_path = os.path.join(temp_dir, f"raw_{tag}.webm")
    with open(webm_path, "wb") as f:
        f.write(video_bytes)

    mp4_path = os.path.join(temp_dir, f"crop_{tag}.mp4")
    # NOTE 1: libx264 is not available in Sherlock's system ffmpeg module
    # (no --enable-gpl in that build), so we use ffmpeg's built-in mpeg4
    # encoder instead, which needs no external library. Same fix as the
    # sibling iCatcher+ pipeline.
    #
    # NOTE 2: -vsync vfr is essential here, not optional. These webcam
    # recordings (from browser MediaRecorder, via Proliferate/jsPsych) have
    # bogus/variable frame-rate container metadata (observed r_frame_rate
    # of 1000/1 on real pilot data). Without -vsync vfr, ffmpeg's default
    # CFR behavior duplicates frames to match that bogus declared rate -
    # confirmed on real pilot data this turns a ~300-frame, ~15fps clip
    # into a ~20,000-frame output that is >95% duplicate frames. That's
    # not just wasted compute (each duplicate frame still costs a full
    # MediaPipe FaceMesh inference pass) - at scale it risks blowing past
    # the sbatch --time limit. -vsync vfr passes through frames as
    # actually decoded, with no duplication.
    cmd = [
        "ffmpeg", "-y", "-ss", str(crop_start), "-i", webm_path,
        "-an", "-c:v", "mpeg4", "-q:v", "3", "-pix_fmt", "yuv420p", "-vsync", "vfr",
        mp4_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(f"  Error converting {tag} (exit {result.returncode}):\n{result.stdout[-2000:]}")
        return None
    return mp4_path


def main():
    parser = argparse.ArgumentParser(description="MediaPipe adult gaze estimation (Sherlock-array-ready).")
    parser.add_argument("videos_csv", help="Path to this participant's videos CSV (workerid, proliferate.condition, base64, mime_type, trial_idx, error)")
    parser.add_argument("test_order_csv", nargs="?", default=None, help="Path to this participant's test-order CSV (workerid, proliferate.condition, test_order, error)")
    parser.add_argument("--output_dir", default="mediapipe_output", help="Where per-trial annotation .txt files go (shared across participants is fine; filenames are unique).")
    parser.add_argument("--out", default=None, help="Path to write this participant's summary CSV. Defaults to results/mediapipe_summary_<workerid>.csv")
    parser.add_argument("-s", "--sensitivity", type=float, default=0.012, help="Gaze sensitivity offset (default: 0.012, matches the pilot script).")
    parser.add_argument("--crop_start", type=float, default=21.76, help="ffmpeg -ss seek point in seconds, marking the start of the ~20s freeze-frame window gaze is scored over (default 21.76, matches this study's clip timing).")
    args = parser.parse_args()

    if not os.path.isfile(args.videos_csv):
        print(f"Error: {args.videos_csv} is not a valid file.")
        sys.exit(1)

    videos_df = pd.read_csv(args.videos_csv)
    if videos_df.empty:
        print(f"No video rows found in {args.videos_csv}. Nothing to do.")
        sys.exit(0)

    pid = str(videos_df.iloc[0]["workerid"])

    test_order = []
    if args.test_order_csv and os.path.exists(args.test_order_csv):
        to_df = pd.read_csv(args.test_order_csv)
        test_order = [str(x).strip() for x in to_df["test_order"].tolist() if pd.notna(x)]
    else:
        print(f"Warning: no test-order CSV found for participant {pid}. Conditions will show as 'unknown'.")

    os.makedirs(args.output_dir, exist_ok=True)

    out_path = args.out
    if out_path is None:
        os.makedirs("results", exist_ok=True)
        out_path = os.path.join("results", f"mediapipe_summary_{pid}.csv")
    else:
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    # Unique per-process temp dir so parallel array tasks never collide.
    temp_dir = tempfile.mkdtemp(prefix=f"mediapipe_tmp_{os.getpid()}_")

    summary_results = []
    try:
        for _, row in videos_df.iterrows():
            trial_idx = int(row["trial_idx"])
            base64_data = row.get("base64")
            if not isinstance(base64_data, str) or not base64_data:
                print(f"  No video data for trial {trial_idx}, skipping.")
                continue

            condition = "unknown"
            try:
                condition = test_order[trial_idx - 1]
            except (IndexError, TypeError):
                pass

            output_txt = os.path.join(args.output_dir, f"videoStream_adult_{pid}_{trial_idx}_{condition}.txt")

            if os.path.exists(output_txt) and os.path.getsize(output_txt) > 0:
                print(f"Annotation already exists for participant '{pid}' trial {trial_idx}, reusing it.")
                left, right, center, noface = count_from_annotation(output_txt)
            else:
                print(f"Processing participant '{pid}' trial {trial_idx} (condition: {condition})...")
                mp4_path = decode_and_crop_video(base64_data, temp_dir, f"{pid}_t{trial_idx}", args.crop_start)
                if mp4_path is None:
                    continue
                left, right, center, noface = run_mediapipe_gaze(mp4_path, output_txt, args.sensitivity)

            total = left + right + center
            left_pct = (left / total * 100) if total > 0 else 0
            right_pct = (right / total * 100) if total > 0 else 0
            print(f"  Left={left} ({left_pct:.1f}%), Right={right} ({right_pct:.1f}%), Center={center}, NoFace={noface}")

            summary_results.append({
                "ParticipantID": pid,
                "TrialIndex": trial_idx,
                "TrialType": condition,
                "Left Looking Frames": left,
                "Right Looking Frames": right,
                "Center Looking Frames": center,
                "NoFace Frames": noface,
                "Left Looking %": round(left_pct, 2),
                "Right Looking %": round(right_pct, 2),
                "Annotation File": output_txt,
            })
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    if not summary_results:
        print("No trials were processed.")
        sys.exit(0)

    summary_df = pd.DataFrame(summary_results).sort_values(by=["ParticipantID", "TrialIndex"])
    print("\n--- Summary Gaze Results ---")
    print(summary_df.to_string(index=False))

    summary_df.to_csv(out_path, index=False)
    print(f"\nSaved summary to {out_path}")


if __name__ == "__main__":
    main()
