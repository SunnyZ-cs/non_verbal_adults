#!/bin/bash
#
# run_icatcher_array.sbatch
#
# SLURM job array: ONE participant per array task, all running in parallel
# on Sherlock's public `gpu` partition. Task i reads line i+1 of
# participants.txt to know which response UUID to process.
#
# Before submitting:
#   1. Run setup_env.sh once per Sherlock account (builds the shared venv +
#      downloads the iCatcher+ model - skip if already done for a prior run).
#   2. Run: python make_participant_list.py data.json participants.txt
#      It prints the exact --array=0-N range to use below.
#
# Submit from INSIDE this run's directory (so config.sh is found):
#   cd $GROUP_HOME/icatcher_pipeline/<run_name>
#   sbatch --array=0-N run_icatcher_array.sbatch
#
# At bigger scale (e.g. 200+ participants), be a good cluster citizen and
# cap how many array tasks run at once with the %-throttle syntax, e.g.:
#   sbatch --array=0-199%20 run_icatcher_array.sbatch
# (this queues all 200 tasks but never runs more than 20 GPUs at a time -
# faster to get scheduled, and less likely to hit any per-user GPU/job caps).
#
# Monitor with:
#   squeue -u $USER -r
# Logs land in slurm_logs/icatcher_<jobid>_<arrayindex>.out / .err

#SBATCH --job-name=icatcher
#SBATCH -p gpu
#SBATCH -G 1
#SBATCH -c 4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=slurm_logs/icatcher_%A_%a.out
#SBATCH --error=slurm_logs/icatcher_%A_%a.err

set -e

if [ ! -f ./config.sh ]; then
  echo "ERROR: submit this from inside a run directory that has config.sh in it"
  echo "(i.e. cd \$GROUP_HOME/icatcher_pipeline/<run_name> first, then sbatch)."
  exit 1
fi
source ./config.sh

RUN_DIR="$(pwd)"
SHARED_DIR="${SHERLOCK_BASE_DIR}/_shared"
VIDEOS_DIR="$RUN_DIR/videos folder"
JSON_PATH="$RUN_DIR/data.json"

mkdir -p "$RUN_DIR/slurm_logs" "$RUN_DIR/results"

ml load python/3.9.0
ml load system ffmpeg
source "$SHARED_DIR/venv/bin/activate"
export ICATCHER_DATA_DIR="$SHARED_DIR/icatcher_models"

PARTICIPANTS_FILE="$RUN_DIR/participants.txt"
UUID=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$PARTICIPANTS_FILE")

if [ -z "$UUID" ]; then
  echo "No UUID found for array index $SLURM_ARRAY_TASK_ID in $PARTICIPANTS_FILE - exiting."
  exit 1
fi

echo "Run: $RUN_NAME | Array task $SLURM_ARRAY_TASK_ID -> participant $UUID"
nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader || true

python "$RUN_DIR/process_icatcher_sherlock.py" \
  "$VIDEOS_DIR" \
  "$JSON_PATH" \
  --uuid "$UUID" \
  --gpu_id 0 \
  --output_dir "$RUN_DIR/icatcher_output" \
  --out "$RUN_DIR/results/icatcher_summary_${UUID}.csv"

echo "Done: $UUID"
