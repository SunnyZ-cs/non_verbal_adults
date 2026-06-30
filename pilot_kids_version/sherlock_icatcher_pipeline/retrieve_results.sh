#!/bin/bash
# retrieve_results.sh
#
# Run this ON YOUR MAC after the SLURM array job has finished and you've
# run merge_results.py on Sherlock. Pulls the combined CSV (and the raw
# per-participant icatcher_output annotation files, optionally) back down
# to your Desktop.
#
# Usage:
#   bash retrieve_results.sh <your_sunet_id>

set -e

SUNET_ID="$1"
if [ -z "$SUNET_ID" ]; then
  echo "Usage: bash retrieve_results.sh <your_sunet_id>"
  exit 1
fi

REMOTE_DIR='$GROUP_HOME/icatcher_pipeline'
DEST="$HOME/Desktop/icatcher_results"
mkdir -p "$DEST"

echo "=== Pulling combined summary CSV ==="
scp "${SUNET_ID}@login.sherlock.stanford.edu:${REMOTE_DIR}/icatcher_summary_combined.csv" "$DEST/"

echo "=== Pulling per-participant CSVs (results/) ==="
rsync -avP "${SUNET_ID}@login.sherlock.stanford.edu:${REMOTE_DIR}/results/" "$DEST/results/"

echo "=== Pulling SLURM logs (useful if anything failed) ==="
rsync -avP "${SUNET_ID}@login.sherlock.stanford.edu:${REMOTE_DIR}/slurm_logs/" "$DEST/slurm_logs/"

echo ""
echo "Saved to $DEST"
echo "(Skipping the raw icatcher_output/ per-frame annotation files - those"
echo " are large; pull them too with an extra rsync if you need them.)"
