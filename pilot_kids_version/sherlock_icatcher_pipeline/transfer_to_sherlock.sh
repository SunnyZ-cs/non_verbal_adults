#!/bin/bash
# transfer_to_sherlock.sh
#
# Run this ON YOUR MAC (not on Sherlock) from a Terminal. It rsyncs your
# JSON file, videos folder, and this whole pipeline folder up to your
# Sherlock GROUP_HOME (or $SCRATCH if your account has no group home).
#
# You'll be prompted for your Sherlock password + Duo push for each rsync
# below (that's expected - this is the part that has to happen on your own
# machine, since it needs your live 2FA approval).
#
# Usage:
#   bash transfer_to_sherlock.sh <your_sunet_id>
#
# Example:
#   bash transfer_to_sherlock.sh jsmith

set -e

SUNET_ID="$1"
if [ -z "$SUNET_ID" ]; then
  echo "Usage: bash transfer_to_sherlock.sh <your_sunet_id>"
  exit 1
fi

REMOTE="${SUNET_ID}@dtn.sherlock.stanford.edu"
REMOTE_DIR='$GROUP_HOME/icatcher_pipeline'   # evaluated on the remote side

DESKTOP="$HOME/Desktop"

echo "=== 1/3: creating remote project directory ==="
ssh "${SUNET_ID}@login.sherlock.stanford.edu" "mkdir -p ${REMOTE_DIR}"

echo "=== 2/3: transferring videos folder (this is the big one - 2.1GB) ==="
rsync -avP "$DESKTOP/videos folder/" "${REMOTE}:${REMOTE_DIR}/videos folder/"

echo "=== 3/3: transferring JSON + pipeline scripts ==="
rsync -avP "$DESKTOP/Whose-fault-is-it-_all-responses-identifiable.json" "${REMOTE}:${REMOTE_DIR}/"
rsync -avP "$(dirname "$0")/" "${REMOTE}:${REMOTE_DIR}/" \
  --exclude videos --exclude "*.csv"

echo ""
echo "Done. Your data + scripts are now in \$GROUP_HOME/icatcher_pipeline on Sherlock."
echo "Next: ssh ${SUNET_ID}@login.sherlock.stanford.edu and follow README.md from there."
