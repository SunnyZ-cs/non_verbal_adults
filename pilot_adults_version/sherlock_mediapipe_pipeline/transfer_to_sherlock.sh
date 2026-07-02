#!/bin/bash
# transfer_to_sherlock.sh
#
# Run this ON YOUR MAC (not on Sherlock) from a Terminal. It rsyncs this
# batch's two CSVs (videos + test order) and the pipeline scripts up to
# Sherlock, into a directory named after config.sh's RUN_NAME so different
# batches of data never mix.
#
# Before running: edit config.sh (SUNET_ID, RUN_NAME, VIDEOS_CSV_FILENAME,
# TEST_ORDER_CSV_FILENAME) for this batch, and make sure both CSVs are
# sitting on your Desktop.
#
# Usage:
#   bash transfer_to_sherlock.sh

set -e
cd "$(dirname "$0")"
source ./config.sh

LOGIN_HOST="${SUNET_ID}@login.sherlock.stanford.edu"

DESKTOP="$HOME/Desktop"

if [ ! -f "$DESKTOP/$VIDEOS_CSV_FILENAME" ]; then
  echo "ERROR: $DESKTOP/$VIDEOS_CSV_FILENAME not found. Check VIDEOS_CSV_FILENAME in config.sh."
  exit 1
fi
if [ ! -f "$DESKTOP/$TEST_ORDER_CSV_FILENAME" ]; then
  echo "ERROR: $DESKTOP/$TEST_ORDER_CSV_FILENAME not found. Check TEST_ORDER_CSV_FILENAME in config.sh."
  exit 1
fi

# Connection multiplexing: authenticate (password + Duo) ONCE, then every
# ssh/rsync call below reuses that same authenticated connection instead of
# prompting for Duo again each time.
CONTROL_PATH="/tmp/sherlock-ssh-%r@%h:%p"
SSH_OPTS=(-o "ControlMaster=auto" -o "ControlPath=$CONTROL_PATH" -o "ControlPersist=15m")

echo "=== Opening one authenticated connection (approve Duo once here - everything below reuses it) ==="
ssh "${SSH_OPTS[@]}" -fN "$LOGIN_HOST"

# Resolve $GROUP_HOME (or whatever SHERLOCK_BASE_DIR references) to a
# CONCRETE path via a real remote shell command (plain ssh, not rsync).
# Modern rsync (3.x, the Homebrew version) defaults to --protect-args,
# which deliberately does NOT route its own remote-path arguments through
# a shell - so a literal "$GROUP_HOME" embedded in a path gets passed
# through unexpanded and rsync/mkdir create a directory literally called
# "$GROUP_HOME" instead of resolving it. Confirmed live on real data.
# Resolving it once via ssh (which always uses a real remote shell for
# command execution) sidesteps this regardless of local rsync version.
RESOLVED_BASE_DIR=$(ssh "${SSH_OPTS[@]}" "$LOGIN_HOST" "echo ${SHERLOCK_BASE_DIR}")
REMOTE_DIR="${RESOLVED_BASE_DIR}/${RUN_NAME}"
echo "=== Run: $RUN_NAME -> $REMOTE_DIR ==="

echo "=== 1/3: creating remote run directory ==="
ssh "${SSH_OPTS[@]}" "$LOGIN_HOST" "mkdir -p '${REMOTE_DIR}'"

echo "=== 2/3: transferring videos CSV (this is the big one - can be 100MB+) ==="
rsync -avP -e "ssh ${SSH_OPTS[*]}" "$DESKTOP/$VIDEOS_CSV_FILENAME" "${LOGIN_HOST}:${REMOTE_DIR}/videos.csv"

echo "=== 3/3: transferring test-order CSV + pipeline scripts ==="
rsync -avP -e "ssh ${SSH_OPTS[*]}" "$DESKTOP/$TEST_ORDER_CSV_FILENAME" "${LOGIN_HOST}:${REMOTE_DIR}/test_order.csv"
rsync -avP -e "ssh ${SSH_OPTS[*]}" ./ "${LOGIN_HOST}:${REMOTE_DIR}/" \
  --exclude "*.csv" --exclude "__pycache__" --exclude "*.pyc" --exclude "participants"

echo "=== closing the shared connection ==="
ssh "${SSH_OPTS[@]}" -O exit "$LOGIN_HOST" 2>/dev/null || true

echo ""
echo "Done. Your data + scripts are now in ${REMOTE_DIR} on Sherlock."
echo "Note: the CSVs were copied to Sherlock as 'videos.csv' / 'test_order.csv' (stable"
echo "names the other scripts expect) regardless of their original filenames."
echo "Next: ssh ${SUNET_ID}@login.sherlock.stanford.edu, cd into that directory,"
echo "and follow README.md's repeatable recipe."
