#!/bin/bash
#
# run_mediapipe_array.sbatch
#
# SLURM job array: ONE participant per array task, on Sherlock's general
# CPU partition (`normal`) - deliberately NOT the `gpu` partition.
#
# Why CPU, unlike the sibling iCatcher+/kids pipeline: iCatcher+ is a
# PyTorch model with real CUDA acceleration. This script uses MediaPipe's
# Python "solutions" Face Mesh API, which runs its (small) TFLite model on
# CPU only - there is no GPU delegate available for this API on headless
# Linux. Requesting a GPU here would just queue longer on the scarcer `gpu`
# partition for zero speed benefit. Each task's actual workload (2 short
# ~20s clips through a lightweight face-mesh model) runs in well under a
# minute of CPU time, so the bottleneck is scheduling delay, not compute -
# `normal` schedules faster than `gpu` for that reason too.
#
# Before submitting:
#   1. Run setup_env.sh once per Sherlock account (builds the shared venv -
#      skip if already done for a prior run).
#   2. Run: python make_participant_list.py videos.csv test_order.csv
#      It prints the exact --array=0-N range to use below.
#
# Submit from INSIDE this run's directory (so config.sh is found):
#   cd $GROUP_HOME/mediapipe_pipeline/<run_name>
#   sbatch --array=0-N run_mediapipe_array.sbatch
#
# At bigger scale (e.g. 200+ participants), throttle concurrency so you're
# not flooding the shared `normal` partition with hundreds of tiny jobs at
# once - it still schedules faster this way and is a better cluster
# citizen:
#   sbatch --array=0-199%40 run_mediapipe_array.sbatch
#
# Monitor with:
#   squeue -u $USER -r
# Logs land in slurm_logs/mediapipe_<jobid>_<arrayindex>.out / .err

#SBATCH --job-name=mediapipe
#SBATCH -p normal
#SBATCH -c 2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=slurm_logs/mediapipe_%A_%a.out
#SBATCH --error=slurm_logs/mediapipe_%A_%a.err

set -e

if [ ! -f ./config.sh ]; then
  echo "ERROR: submit this from inside a run directory that has config.sh in it"
  echo "(i.e. cd \$GROUP_HOME/mediapipe_pipeline/<run_name> first, then sbatch)."
  exit 1
fi
source ./config.sh

RUN_DIR="$(pwd)"
# eval forces a second expansion pass so $GROUP_HOME (stored as a literal,
# unexpanded string in config.sh - see setup_env.sh for why) actually
# resolves here. A plain substitution would silently create/reference a
# literal directory called "$GROUP_HOME" instead - confirmed by testing.
SHARED_DIR="$(eval echo "${SHERLOCK_BASE_DIR}")/_shared"
PARTICIPANTS_DIR="$RUN_DIR/participants"

mkdir -p "$RUN_DIR/slurm_logs" "$RUN_DIR/results"

# mesa provides libGL.so.1, which opencv-python-headless still dynamically
# links against despite being the "headless" variant - confirmed live.
# Load it before python/3.9.0 to avoid a (harmless but noisy) libffi
# version-conflict warning between the two modules.
ml load system mesa
ml load python/3.9.0
ml load system ffmpeg
source "$SHARED_DIR/venv/bin/activate"

PARTICIPANTS_FILE="$RUN_DIR/participants.txt"
WORKERID=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$PARTICIPANTS_FILE")

if [ -z "$WORKERID" ]; then
  echo "No workerid found for array index $SLURM_ARRAY_TASK_ID in $PARTICIPANTS_FILE - exiting."
  exit 1
fi

echo "Run: $RUN_NAME | Array task $SLURM_ARRAY_TASK_ID -> participant $WORKERID"

python "$RUN_DIR/process_videos_mediapipe_sherlock.py" \
  "$PARTICIPANTS_DIR/${WORKERID}_videos.csv" \
  "$PARTICIPANTS_DIR/${WORKERID}_test_order.csv" \
  --output_dir "$RUN_DIR/mediapipe_output" \
  --out "$RUN_DIR/results/mediapipe_summary_${WORKERID}.csv"

echo "Done: $WORKERID"
