"""
process_icatcher_full.py

UNCROPPED variant of process_icatcher_sherlock.py: converts each webm to mp4
WITHOUT the -ss 13.82 crop, so iCatcher+ annotates the FULL recording
(pre-bullseye lag + 3s bullseye + 10.82s animation [part1 5.44 + anticipatory
freeze 2.5 + part2 2.88] + 8s outcome freeze).

Only produces per-frame annotation txts (in icatcher_output_full/) - no
summary CSV needed; the anticipatory-window analysis consumes the raw txts.

Usage (one participant, called by the SLURM array):
    python process_icatcher_full.py "videos folder" --uuid <response_uuid> --gpu_id 0
"""

import os
import sys
import glob
import re
import argparse
import subprocess
import shutil
import tempfile


def parse_video_filename(filename):
    pattern = r"videoStream_[a-f0-9\-]+_(\d+)-start-record-plugin-multiframe_([a-f0-9\-]+)_[0-9]+_[0-9]+\.(webm|mp4)"
    match = re.match(pattern, filename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("videos_dir")
    parser.add_argument("--uuid", required=True)
    parser.add_argument("--gpu_id", default=0, type=int)
    parser.add_argument("--output_dir", default="icatcher_output_full")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix=f"icatcher_full_tmp_{os.getpid()}_", dir=args.videos_dir)

    webms = [w for w in glob.glob(os.path.join(args.videos_dir, "*.webm"))
             if not os.path.basename(w).startswith("consent-")]
    webms = [w for w in webms if parse_video_filename(os.path.basename(w))[1] == args.uuid]

    if not webms:
        print(f"No videos for uuid {args.uuid}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(0)

    env = os.environ.copy()
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "TORCH_NUM_THREADS"):
        env[v] = "1"

    try:
        for webm in webms:
            base = os.path.splitext(os.path.basename(webm))[0]
            out_txt = os.path.join(args.output_dir, f"{base}.txt")
            if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0:
                print(f"Already done: {base}")
                continue

            mp4_path = os.path.join(temp_dir, base + ".mp4")
            # NO -ss crop: full video. mpeg4 encoder (libx264 unavailable on Sherlock).
            cmd = ["ffmpeg", "-y", "-i", webm, "-an", "-c:v", "mpeg4", "-q:v", "3",
                   "-pix_fmt", "yuv420p", mp4_path]
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if r.returncode != 0:
                print(f"ffmpeg failed for {base}:\n{r.stdout[-1500:]}")
                continue

            print(f"Running iCatcher+ (full video) on {base}...")
            cmd = ["icatcher", mp4_path, "--output_annotation", args.output_dir,
                   "--overwrite", "--gpu_id", str(args.gpu_id), "--fd_model", "opencv_dnn"]
            r = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode != 0:
                print(f"icatcher failed for {base} (exit {r.returncode})")
            elif os.path.exists(out_txt):
                print(f"Done: {base}")
            else:
                print(f"Missing expected output: {out_txt}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
