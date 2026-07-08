#!/bin/bash
# transfer_to_sherlock.sh
#
# Run this ON YOUR MAC (not on Sherlock) from a Terminal. It rsyncs this
# batch's JSON file, videos folder, and the pipeline scripts up to Sherlock,
# into a directory named after config.sh's RUN_NAME so different batches of
# data never mix.
#
# Before running: edit config.sh (SUNET_ID, RUN_NAME, JSON_FILENAME,
# VIDEOS_FOLDER_NAME) for this batch, and make sure both the JSON file and
# the videos folder are sitting on your Desktop.
#
# Usage:
#   bash transfer_to_sherlock.sh

set -e
cd "$(dirname "$0")"
source ./config.sh

LOGIN_HOST="${SUNET_ID}@login.sherlock.stanford.edu"
REMOTE_DIR="${SHERLOCK_BASE_DIR}/${RUN_NAME}"

DESKTOP="$HOME/Desktop"

if [ ! -f "$DESKTOP/$JSON_FILENAME" ]; then
  echo "ERROR: $DESKTOP/$JSON_FILENAME not found. Check JSON_FILENAME in config.sh."
  exit 1
fi
if [ ! -d "$DESKTOP/$VIDEOS_FOLDER_NAME" ]; then
  echo "ERROR: $DESKTOP/$VIDEOS_FOLDER_NAME not found. Check VIDEOS_FOLDER_NAME in config.sh."
  exit 1
fi

# Connection multiplexing: authenticate (password + Duo) ONCE, then every
# ssh/rsync call below reuses that same authenticated connection instead of
# prompting for Duo again each time.
CONTROL_PATH="/tmp/sherlock-ssh-%r@%h:%p"
SSH_OPTS=(-o "ControlMaster=auto" -o "ControlPath=$CONTROL_PATH" -o "ControlPersist=15m")

echo "=== Run: $RUN_NAME -> $REMOTE_DIR ==="
echo "=== Opening one authenticated connection (approve Duo once here - everything below reuses it) ==="
ssh "${SSH_OPTS[@]}" -fN "$LOGIN_HOST"

echo "=== 1/3: creating remote run directory ==="
ssh "${SSH_OPTS[@]}" "$LOGIN_HOST" "mkdir -p '${REMOTE_DIR}'"

echo "=== 2/3: transferring videos folder ('$VIDEOS_FOLDER_NAME') ==="
rsync -avP -e "ssh ${SSH_OPTS[*]}" "$DESKTOP/$VIDEOS_FOLDER_NAME/" "${LOGIN_HOST}:${REMOTE_DIR}/videos folder/"

echo "=== 3/3: transferring JSON + pipeline scripts ==="
rsync -avP -e "ssh ${SSH_OPTS[*]}" "$DESKTOP/$JSON_FILENAME" "${LOGIN_HOST}:${REMOTE_DIR}/data.json"
rsync -avP -e "ssh ${SSH_OPTS[*]}" ./ "${LOGIN_HOST}:${REMOTE_DIR}/" \
  --exclude "videos folder" --exclude "*.csv" --exclude "__pycache__" --exclude "*.pyc"

echo "=== closing the shared connection ==="
ssh "${SSH_OPTS[@]}" -O exit "$LOGIN_HOST" 2>/dev/null || true

echo ""
echo "Done. Your data + scripts are now in ${SHERLOCK_BASE_DIR}/${RUN_NAME} on Sherlock."
echo "Note: the JSON was copied to Sherlock as 'data.json' (a stable name the"
echo "other scripts expect) regardless of its original filename."
echo "Next: ssh ${SUNET_ID}@login.sherlock.stanford.edu, cd into that directory,"
echo "and follow README.md from the 'Every new batch of data' section."
