import os
import sys
import glob
import subprocess
import pandas as pd

def run_icatcher(video_path, output_dir="icatcher_output"):
    """
    Runs iCatcher+ on a given video file.
    Assumes icatcher is installed in the current python environment
    (e.g., via `pip install git+https://github.com/icatcherplus/icatcher_plus.git`)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Running iCatcher+ on {video_path}...")
    
    # Standard iCatcher+ CLI command: icatcher <video_path> --output_dir <dir>
    cmd = [
        "icatcher", 
        video_path, 
        "--output_dir", output_dir
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("iCatcher+ processing complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error running iCatcher on {video_path}: {e}")
        return None
        
    # The output file is usually named <video_filename>.txt or .csv inside the output_dir
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    expected_output_txt = os.path.join(output_dir, f"{base_name}.txt")
    
    if os.path.exists(expected_output_txt):
        return expected_output_txt
    else:
        print(f"Could not find expected output file: {expected_output_txt}")
        return None

def analyze_gaze(icatcher_output_file):
    """
    Parses the iCatcher output to compute the total right-looking 
    and left-looking frames.
    """
    if not icatcher_output_file:
        return 0, 0
        
    # Read the space-separated or comma-separated iCatcher output
    # iCatcher output typically has columns: frame, prediction, confidence, etc.
    # We will try comma first, then whitespace
    try:
        df = pd.read_csv(icatcher_output_file)
        if 'prediction' not in df.columns and 'label' not in df.columns:
            # Fallback to whitespace separation
            df = pd.read_csv(icatcher_output_file, delim_whitespace=True)
    except Exception as e:
        print(f"Failed to read {icatcher_output_file}: {e}")
        return 0, 0

    # Determine which column holds the gaze prediction ('prediction' or 'label')
    pred_col = 'prediction' if 'prediction' in df.columns else 'label' if 'label' in df.columns else None
    
    if not pred_col:
        print(f"Could not find a prediction column in {icatcher_output_file}. Columns found: {df.columns}")
        return 0, 0

    # iCatcher predictions are typically strings: "left", "right", "away"
    # Convert to lowercase to be safe
    df[pred_col] = df[pred_col].astype(str).str.lower()
    
    left_frames = (df[pred_col] == 'left').sum()
    right_frames = (df[pred_col] == 'right').sum()
    away_frames = (df[pred_col] == 'away').sum()
    
    return left_frames, right_frames, away_frames

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_icatcher.py <path_to_video_or_directory>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    video_files = []
    
    if os.path.isdir(input_path):
        video_files.extend(glob.glob(os.path.join(input_path, "*.webm")))
        video_files.extend(glob.glob(os.path.join(input_path, "*.mp4")))
    else:
        video_files.append(input_path)
        
    if not video_files:
        print(f"No video files found at {input_path}")
        sys.exit(1)
        
    results = []
    
    for video in video_files:
        output_txt = run_icatcher(video)
        left_frames, right_frames, away_frames = analyze_gaze(output_txt)
        
        results.append({
            "Video": os.path.basename(video),
            "Left Looking Frames": left_frames,
            "Right Looking Frames": right_frames,
            "Away/Other Frames": away_frames
        })
        
    # Save a summary CSV
    summary_df = pd.DataFrame(results)
    print("\n--- Summary Results ---")
    print(summary_df.to_string(index=False))
    
    summary_csv = "icatcher_summary_results.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"\nSaved detailed summary to {summary_csv}")

if __name__ == "__main__":
    main()
