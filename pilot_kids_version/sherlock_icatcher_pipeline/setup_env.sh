#!/bin/bash
# setup_env.sh
#
# Run this ON SHERLOCK, inside a run's directory (i.e. after
# transfer_to_sherlock.sh, do `cd $GROUP_HOME/icatcher_pipeline/<run_name>`
# first). It builds the Python environment needed to run iCatcher+ on a GPU.
#
# You only need to do this ONCE PER SHERLOCK ACCOUNT, not once per batch of
# data - the venv and the downloaded iCatcher+ model live in a shared
# location ($GROUP_HOME/icatcher_pipeline/_shared) and every run's directory
# reuses them. Re-running this script later is safe (it skips work that's
# already done) in case a dependency needs updating.
#
# Sherlock's own docs explicitly recommend AGAINST using conda/Anaconda
# (https://www.sherlock.stanford.edu/docs/software/using/anaconda/) because
# it tends to fill up $HOME and ship non-optimized binaries. We use a plain
# Python venv + Sherlock's module system instead, per their recommendation.
#
# Run this from an interactive GPU node so the PyTorch/iCatcher install can
# actually detect a GPU and you can sanity check it before submitting a full
# array job:
#
#   $ sh_dev -g 1            # grab a lightweight interactive GPU instance
#   $ bash setup_env.sh
#
# If `sh_dev` isn't available, use: salloc -p gpu --gpus 1 -t 1:00:00

set -e

if [ ! -f ./config.sh ]; then
  echo "ERROR: run this from inside a run directory that has config.sh in it"
  echo "(i.e. cd \$GROUP_HOME/icatcher_pipeline/<run_name> first)."
  exit 1
fi
source ./config.sh

# NOTE: SHERLOCK_BASE_DIR is intentionally stored as a literal, unexpanded
# string in config.sh (e.g. containing "$GROUP_HOME" as literal characters,
# not a live reference) so the same config.sh works whether it's read on
# your Mac (which has no $GROUP_HOME) or on Sherlock. That means a plain
# "${SHERLOCK_BASE_DIR}/_shared" substitution here would NOT expand
# $GROUP_HOME - bash only expands variables once per token and does not
# re-scan an already-substituted value for further $ references. Confirmed
# by direct testing (on the sibling mediapipe pipeline): it silently
# creates a literal directory called "$GROUP_HOME" instead of resolving
# it. `eval echo` forces the needed second expansion pass, on this
# Sherlock-native shell where $GROUP_HOME really is set.
SHARED_DIR="$(eval echo "${SHERLOCK_BASE_DIR}")/_shared"
mkdir -p "$SHARED_DIR"
echo "Shared environment dir (reused across all runs): $SHARED_DIR"

echo "=== Checking available Python modules (pick the newest 3.9+ you see if this needs updating) ==="
ml spider python || true

# Adjust this version if `ml spider python` above shows a newer one you'd
# rather use for a fresh setup. Once a venv is built with a given Python
# version, keep loading that same version for consistency.
PY_MODULE="python/3.9.0"
echo "Loading module: $PY_MODULE"
ml load "$PY_MODULE"
ml load system ffmpeg

VENV_DIR="$SHARED_DIR/venv"
if [ -d "$VENV_DIR" ]; then
  echo "Venv already exists at $VENV_DIR - skipping creation, will just verify it below."
else
  echo "Creating venv at $VENV_DIR ..."
  # NOTE: use python3 explicitly here, not python - Sherlock's python module
  # only provides a `python3` binary, and falling through to the system
  # default `python` (very old, no venv/f-string support) is a common trap.
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip -q

# PyPI's default torch wheel bundles its own CUDA runtime, so this works
# without needing a system CUDA module for inference.
pip install -q torch torchvision

# pandas>=2.3 dropped prebuilt wheels for Python 3.9 (EOL upstream), which
# forces pip to compile from source - and that fails on Sherlock's older
# system compiler toolchain. Pin below 2.3 to stay on a wheel.
pip install -q icatcher "pandas<2.3"

echo "=== Checking for ffmpeg ==="
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found on PATH even after 'ml load system ffmpeg'."
  echo "Run 'ml spider ffmpeg' yourself and load the right one, or email srcc-support@stanford.edu."
fi
ffmpeg -version | head -1

# Sherlock's ffmpeg build does NOT include libx264 (no --enable-gpl), so
# process_icatcher_sherlock.py uses the built-in `mpeg4` encoder instead -
# that's already baked into the script, nothing to configure here. If you
# ever see "Unknown encoder 'libx264'" it means someone reverted that fix.

# Shared, writable location for the iCatcher+ model weights so every run
# (and every array task within a run) reuses the same download instead of
# racing to download it separately.
export ICATCHER_DATA_DIR="$SHARED_DIR/icatcher_models"
mkdir -p "$ICATCHER_DATA_DIR"

echo ""
echo "=== Sanity check: confirm a GPU is visible ==="
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"

echo ""
echo "=== Triggering the iCatcher+ model download (only needs to happen once ever) ==="
if [ -d "$ICATCHER_DATA_DIR" ] && [ "$(ls -A "$ICATCHER_DATA_DIR" 2>/dev/null)" ]; then
  echo "Model cache already has files in it - skipping. (Delete $ICATCHER_DATA_DIR to force a re-download.)"
else
  SAMPLE_VIDEO=$(find "videos folder" -iname "*.webm" ! -iname "consent-*" 2>/dev/null | head -1)
  if [ -n "$SAMPLE_VIDEO" ]; then
    echo "Using $SAMPLE_VIDEO to trigger the download..."
    icatcher "$SAMPLE_VIDEO" --output_annotation /tmp/icatcher_setup_test --gpu_id 0 --fd_model opencv_dnn || \
      echo "(non-fatal if this errors on a raw .webm - the real pipeline converts to .mp4 first via ffmpeg; the model download itself is what matters here)"
  else
    echo "No sample video found in 'videos folder' yet - the model will download automatically on the first real array task instead."
  fi
fi

echo ""
echo "Setup complete."
echo "Shared dir:          $SHARED_DIR"
echo "Venv:                $VENV_DIR"
echo "ICATCHER_DATA_DIR:   $ICATCHER_DATA_DIR"
echo ""
echo "Next: python make_participant_list.py, then submit the array job (see README.md)."
