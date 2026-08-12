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
