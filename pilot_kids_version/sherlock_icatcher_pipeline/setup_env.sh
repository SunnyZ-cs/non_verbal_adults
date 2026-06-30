#!/bin/bash
# setup_env.sh
#
# ONE-TIME environment setup on Sherlock. Run this yourself after SSHing in
# (this script does NOT run from your laptop - copy/paste it on Sherlock,
# or run it after rsyncing this whole folder over - see README.md).
#
# Sherlock's own docs explicitly recommend AGAINST using conda/Anaconda
# (https://www.sherlock.stanford.edu/docs/software/using/anaconda/) because
# it tends to fill up $HOME and ship non-optimized binaries. We use a plain
# Python venv + Sherlock's module system instead, per their recommendation.
#
# Run this from an interactive GPU node so the PyTorch/iCatcher install can
# actually detect a GPU and you can sanity check it before submitting the
# full array job:
#
#   $ sh_dev -g 1            # grab a lightweight interactive GPU instance
#   $ bash setup_env.sh
#
# If `sh_dev` isn't available, use: salloc -p gpu --gpus 1 -t 1:00:00

set -e

echo "=== Checking available Python modules (pick the newest 3.9+ you see) ==="
ml spider python || true

# Adjust this version if `ml spider python` above shows a newer one.
PY_MODULE="python/3.9.0"
echo "Loading module: $PY_MODULE"
ml load "$PY_MODULE"

PROJECT_DIR="$GROUP_HOME/icatcher_pipeline"
if [ -z "$GROUP_HOME" ]; then
  PROJECT_DIR="$SCRATCH/icatcher_pipeline"
fi
mkdir -p "$PROJECT_DIR"
echo "Using project dir: $PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/venv"
python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip

# PyPI's default torch wheel bundles its own CUDA runtime, so this works
# without needing a system CUDA module for inference. If `nvidia-smi` shows
# a CUDA version much older than what pip installs, see
# https://pytorch.org/get-started/locally/ and pin a matching --index-url.
pip install torch torchvision

pip install icatcher pandas

echo "=== Checking for ffmpeg ==="
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found on PATH, trying module..."
  ml spider ffmpeg || true
  ml load system ffmpeg || echo "WARNING: could not auto-load an ffmpeg module. Run 'ml spider ffmpeg' yourself and load the right one, or email srcc-support@stanford.edu."
fi
ffmpeg -version | head -1 || echo "WARNING: ffmpeg still not found - process_icatcher_sherlock.py needs it for webm->mp4 conversion."

# Shared, writable location for the iCatcher model weights so all 73 array
# tasks reuse the same download instead of 73 racing downloads.
export ICATCHER_DATA_DIR="$PROJECT_DIR/icatcher_models"
mkdir -p "$ICATCHER_DATA_DIR"

echo ""
echo "=== Sanity check: confirm a GPU is visible ==="
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"

echo ""
echo "=== Triggering the iCatcher+ model download (only needs to happen once) ==="
echo "This needs at least one real video. Point it at any single non-consent"
echo "video in your videos folder, e.g.:"
echo "  icatcher \"\$PROJECT_DIR/videos/<some_video>.mp4\" --output_annotation /tmp/icatcher_test --gpu_id 0 --fd_model opencv_dnn"
echo ""
echo "Setup complete."
echo "Project dir:        $PROJECT_DIR"
echo "Venv:                $VENV_DIR  (activate with: source $VENV_DIR/bin/activate)"
echo "ICATCHER_DATA_DIR:   $ICATCHER_DATA_DIR"
echo ""
echo "Add these two lines to your ~/.bashrc so every future job/session picks them up:"
echo "  export ICATCHER_DATA_DIR=$ICATCHER_DATA_DIR"
echo "  # then activate the venv manually in each job script with:"
echo "  # source $VENV_DIR/bin/activate"
