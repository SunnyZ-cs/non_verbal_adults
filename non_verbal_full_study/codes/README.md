# Non-Verbal Looking Time Study Animation Codes

This directory contains the Python scripts used to generate and reproduce all the counterbalanced visual stimuli (Familiarization and Test Trial GIFs/PNGs) for the unified **`non_verbal_full_study`** experiment.

All animations use the bubbly/glossy 3D visual style (with sphere highlights, gradient shading, and custom facial expressions) and feature the yellow star "authority" character carrying out star yanks using a magic wand.

---

## Script Registry

### 1. [familiarization_trials.py](familiarization_trials.py)
*   **Intention**: Generates the 8 familiarization combo sequence animations (`Fam_Combo_1.gif` to `Fam_Combo_8.gif`) by interleaving the baseline scenarios (Trash, Tower, Toy, Flower) with alternating reward and punishment outcomes.
*   **Execution**:
    ```bash
    python3 familiarization_trials.py
    ```
*   **Outputs**: Creates the `.gif` animations in this directory and copies them automatically to `../materials/`.

### 2. [extract_familiarization_freezes.py](extract_familiarization_freezes.py)
*   **Intention**: Extracts the final frame from each of the 8 familiarization combo animations and saves it as a static freeze PNG image (`Fam_Combo_1_freeze.png` to `Fam_Combo_8_freeze.png`). These are used as debrief/freeze screens in Lookit trials.
*   **Execution**: *(Run after familiarization_trials.py has completed)*
    ```bash
    python3 extract_familiarization_freezes.py
    ```
*   **Outputs**: Saves the freeze `.png` files in this directory and copies them to `../materials/`.

### 3. [generate_single_cause_test_trials.py](generate_single_cause_test_trials.py)
*   **Intention**: Generates standard and reverse mirrored test trial animations representing the **single-cause** condition. In this condition, the distal agent remains stationary, while the proximal agent directly collides with and breaks the gray cube.
*   **Execution**:
    ```bash
    python3 generate_single_cause_test_trials.py
    ```
*   **Outputs**: Exports standard/reverse animations and freeze PNGs, automatically copying them to `../materials/` under the prefix `single_cause_` (e.g. `single_cause_distal_test_final.gif`).

### 4. [generate_causal_chains_test_trials.py](generate_causal_chains_test_trials.py)
*   **Intention**: Generates standard and reverse mirrored test trial animations representing the **causal chain** condition. In this condition, the distal agent rushes violently into the proximal agent, propelling it into the gray cube to break it.
*   **Execution**:
    ```bash
    python3 generate_causal_chains_test_trials.py
    ```
*   **Outputs**: Exports standard/reverse animations and freeze PNGs, automatically copying them to `../materials/` under the prefix `chains_` (e.g. `chains_distal_test_final.gif`).

### 5. [warmup_single_character_trials.py](warmup_single_character_trials.py)  *(post lab-meeting revision)*
*   **Intention**: Generates the 3 single-character punishment warmup animations used in the revised study design (replacing the old two-character familiarization combos as the warmup phase). Reuses the exact punishment choreography (approach → steal/damage → carry back → authority swoop → wand removal → star gone) from `familiarization_trials.py`'s trash/tower/flower scenes, but with a single pink-circle character. The character is drawn **eyes-only** (no mouth/eyebrows, matching the eyes-only redesign of the test-trial characters); the star authority keeps its full expressions, exactly as in the test trials.
*   **Left/center/right labeling**: the `left`/`center`/`right` in each output filename refers to the pink circle's x-position **at the punish moment** (the instant the authority removes its star), not the prop's position. The character rests at exactly two x-positions per clip: the punish-moment position (which is also its start and end position -- `home_x` in `SCENES`) and the position beside/over the prop while committing the bad action. Each prop is kept close (70px away, on the correct side) to the character's home/punish-moment position, so it's visible right next to the character rather than across the canvas. Current assignment: **tower** scene → `left` (punish-moment x = 200, tower at x = 270), **trash** scene → `center` (punish-moment x = 400, exact canvas center, directly under the authority; bin at x = 330), **flower** scene → `right` (punish-moment x = 600, the exact mirror of `left` about the canvas centerline; flower at x = 530). Edit the `SCENES` dict (`scene_name`/`scene_x`/`home_x` per position) to change which scene maps to which position, how close the prop sits, or the punish-moment x targets.
*   **Execution**:
    ```bash
    python3 warmup_single_character_trials.py
    ```
*   **Outputs**: `warmup_punish_left.gif`, `warmup_punish_center.gif`, `warmup_punish_right.gif` (~13.4-13.9 s each, loop=1, holds last frame), automatically copied to `../materials/`.

---

## Replication Guide

To generate and sync all 32 material assets:
1. Make sure you have python `pillow` installed (`pip install Pillow`).
2. Run the four scripts in order:
    ```bash
    python3 familiarization_trials.py
    python3 extract_familiarization_freezes.py
    python3 generate_single_cause_test_trials.py
    python3 generate_causal_chains_test_trials.py
    ```
