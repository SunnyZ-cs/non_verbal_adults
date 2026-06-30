#!/bin/bash
#
# run_icatcher_array.sbatch
#
# SLURM job array: ONE participant per array task, all running in parallel
# on Sherlock's public `gpu` partition. Task i reads line i+1 of
# participants.txt to know which response UUID to process.
#
# Before submitting:
#   1. Run setup_env.sh once (creates the venv + downloads the model).
#   2. Run: python make_participant_list.py <json_path> participants.txt
#   3. Edit PROJECT_DIR / VIDEOS_DIR / JSON_PATH below to match where you
#      rsynced your data (see README.md).
#
# Submit with (0-72 for 73 participants - make_participant_list.py prints
# the exact range to use):
#   sbatch --array=0-72 run_icatcher_array.sbatch
#
# Monitor with:
#   squeue -u $USER
# Logs land in slurm_logs/icatcher_<jobid>_<arrayindex>.out

#SBATCH --job-name=icatcher
#SBATCH -p gpu
#SBATCH -G 1
#SBATCH -c 4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=slurm_logs/icatcher_%A_%a.out
#SBATCH --error=slurm_logs/icatcher_%A_%a.err

set -e

# ---- EDIT THESE THREE LINES ----
PROJECT_DIR="$GROUP_HOME/icatcher_pipeline"
VIDEOS_DIR="$PROJECT_DIR/videos folder"
JSON_PATH="$PROJECT_DIR/Whose-fault-is-it-_all-responses-identifiable.json"
# ---------------------------------

mkdir -p "$PROJECT_DIR/slurm_logs" "$PROJECT_DIR/results"
cd "$PROJECT_DIR"

ml load python/3.9.0
source "$PROJECT_DIR/venv/bin/activate"
export ICATCHER_DATA_DIR="$PROJECT_DIR/icatcher_models"

PARTICIPANTS_FILE="$PROJECT_DIR/participants.txt"
UUID=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$PARTICIPANTS_FILE")

if [ -z "$UUID" ]; then
  echo "No UUID found for array index $SLURM_ARRAY_TASK_ID in $PARTICIPANTS_FILE - exiting."
  exit 1
fi

echo "Array task $SLURM_ARRAY_TASK_ID -> participant $UUID"
nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader || true

python "$PROJECT_DIR/process_icatcher_sherlock.py" \
  "$VIDEOS_DIR" \
  "$JSON_PATH" \
  --uuid "$UUID" \
  --gpu_id 0 \
  --output_dir "$PROJECT_DIR/icatcher_output" \
  --out "$PROJECT_DIR/results/icatcher_summary_${UUID}.csv"

echo "Done: $UUID"
