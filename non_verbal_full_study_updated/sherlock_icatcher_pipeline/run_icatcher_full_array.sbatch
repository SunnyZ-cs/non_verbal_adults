#!/bin/bash
# Full-video (uncropped) iCatcher pass over the batch3 participants.
# Submit from inside $GROUP_HOME/icatcher_pipeline/batch3:
#   sbatch --array=0-28 run_icatcher_full_array.sbatch

#SBATCH --job-name=icatcher_full
#SBATCH -p gpu
#SBATCH -G 1
#SBATCH -c 4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=slurm_logs/icatcher_full_%A_%a.out
#SBATCH --error=slurm_logs/icatcher_full_%A_%a.err

set -e
source ./config.sh
RUN_DIR="$(pwd)"
SHARED_DIR="$(eval echo "${SHERLOCK_BASE_DIR}")/_shared"

mkdir -p "$RUN_DIR/slurm_logs" "$RUN_DIR/icatcher_output_full"

ml load python/3.9.0
ml load system ffmpeg
source "$SHARED_DIR/venv/bin/activate"
export ICATCHER_DATA_DIR="$SHARED_DIR/icatcher_models"

UUID=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$RUN_DIR/participants.txt")
[ -z "$UUID" ] && { echo "No UUID for index $SLURM_ARRAY_TASK_ID"; exit 1; }

echo "Full-video pass | task $SLURM_ARRAY_TASK_ID -> $UUID"
python "$RUN_DIR/process_icatcher_full.py" "$RUN_DIR/videos folder" \
  --uuid "$UUID" --gpu_id 0 --output_dir "$RUN_DIR/icatcher_output_full"
echo "Done: $UUID"
