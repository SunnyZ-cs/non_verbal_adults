#!/bin/bash
# retrieve_results.sh
#
# Run this ON YOUR MAC after the SLURM array job has finished and you've run
# merge_results.py on Sherlock. Pulls the combined CSV, per-participant
# CSVs, and SLURM logs back down to your Desktop, into a folder named after
# this batch's RUN_NAME so results from different batches never overwrite
# each other.
#
# Usage:
#   bash retrieve_results.sh

set -e
cd "$(dirname "$0")"
source ./config.sh

LOGIN_HOST="${SUNET_ID}@login.sherlock.stanford.edu"
REMOTE_DIR="${SHERLOCK_BASE_DIR}/${RUN_NAME}"
DEST="$HOME/Desktop/icatcher_results_${RUN_NAME}"
mkdir -p "$DEST"

CONTROL_PATH="/tmp/sherlock-ssh-%r@%h:%p"
SSH_OPTS=(-o "ControlMaster=auto" -o "ControlPath=$CONTROL_PATH" -o "ControlPersist=15m")

echo "=== Run: $RUN_NAME ==="
echo "=== Opening one authenticated connection (approve Duo once here) ==="
ssh "${SSH_OPTS[@]}" -fN "$LOGIN_HOST"

echo "=== Pulling combined summary CSV ==="
# NOTE: use rsync, not scp, for remote paths built from env vars like
# $GROUP_HOME. Modern macOS ships an OpenSSH scp that defaults to the SFTP
# protocol, which does NOT invoke a remote shell - so it can't expand
# $GROUP_HOME server-side and fails with a literal "no such file" error.
# rsync (like ssh) always goes through a real remote shell, so it works.
rsync -avP -e "ssh ${SSH_OPTS[*]}" "${LOGIN_HOST}:${REMOTE_DIR}/icatcher_summary_combined.csv" "$DEST/"

echo "=== Pulling per-participant CSVs (results/) ==="
rsync -avP -e "ssh ${SSH_OPTS[*]}" "${LOGIN_HOST}:${REMOTE_DIR}/results/" "$DEST/results/"

echo "=== Pulling SLURM logs (useful if anything failed) ==="
rsync -avP -e "ssh ${SSH_OPTS[*]}" "${LOGIN_HOST}:${REMOTE_DIR}/slurm_logs/" "$DEST/slurm_logs/"

echo "=== closing the shared connection ==="
ssh "${SSH_OPTS[@]}" -O exit "$LOGIN_HOST" 2>/dev/null || true

echo ""
echo "Saved to $DEST"
echo "(Skipping the raw icatcher_output/ per-frame annotation files - those"
echo " are large; pull them too with an extra rsync if you need them:"
echo "   rsync -avP ${LOGIN_HOST}:${REMOTE_DIR}/icatcher_output/ $DEST/icatcher_output/ )"
