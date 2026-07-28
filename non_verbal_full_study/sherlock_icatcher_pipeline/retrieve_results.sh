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
DEST="$HOME/Desktop/icatcher_results_${RUN_NAME}"
mkdir -p "$DEST"

CONTROL_PATH="/tmp/sherlock-ssh-%r@%h:%p"
SSH_OPTS=(-o "ControlMaster=auto" -o "ControlPath=$CONTROL_PATH" -o "ControlPersist=15m")

echo "=== Opening one authenticated connection (approve Duo once here) ==="
ssh "${SSH_OPTS[@]}" -fN "$LOGIN_HOST"

# Resolve $GROUP_HOME (or whatever SHERLOCK_BASE_DIR references) to a
# CONCRETE path via a real remote shell command (plain ssh, not rsync).
# NOTE: this used to say "rsync always goes through a real remote shell,
# so it works" - that was true for the old rsync but NOT for modern rsync
# 3.x (Homebrew's version), which defaults to --protect-args and does NOT
# route its own remote-path arguments through a shell. A literal
# "$GROUP_HOME" embedded in an rsync path argument gets passed through
# unexpanded, creating/reading a path literally called "$GROUP_HOME" -
# confirmed live on the sibling mediapipe pipeline. Resolving it once via
# plain ssh (which always uses a real remote shell for command execution,
# regardless of rsync's behavior) sidesteps this for good.
RESOLVED_BASE_DIR=$(ssh "${SSH_OPTS[@]}" "$LOGIN_HOST" "echo ${SHERLOCK_BASE_DIR}")
REMOTE_DIR="${RESOLVED_BASE_DIR}/${RUN_NAME}"
echo "=== Run: $RUN_NAME -> $REMOTE_DIR ==="

echo "=== Pulling combined summary CSV ==="
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
