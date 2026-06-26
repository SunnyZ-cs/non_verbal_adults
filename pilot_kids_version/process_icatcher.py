import os
import sys
import glob
import re
import json
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
    
    # Standard iCatcher+ CLI command
    cmd = [
        "icatcher", 
        video_path, 
        "--output_annotation", output_dir,
        "--overwrite",
        "--gpu_id", "-1"
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

def analyze_gaze(icatcher_output_file, freeze_duration=20.0, anim_duration=18.76, bullseye_duration=3.0):
    """
    Parses the iCatcher output to compute the total right-looking 
    and left-looking frames for ONLY the final freeze frame portion.
    """
    if not icatcher_output_file:
        return 0, 0, 0
        
    try:
        if os.path.exists(icatcher_output_file) and os.path.getsize(icatcher_output_file) == 0:
            return 0, 0, 0
            
        # Raw output file from iCatcher has no header: frame_number, prediction, confidence
        df = pd.read_csv(icatcher_output_file, header=None)
        if len(df.columns) >= 2:
            pred_series = df[1].astype(str).str.strip().str.lower()
        else:
            print(f"Unexpected column count in {icatcher_output_file}: {df.columns}")
            return 0, 0, 0
    except Exception as e:
        print(f"Failed to read {icatcher_output_file}: {e}")
        return 0, 0, 0

    # Calculate how many frames represent the last 20 seconds.
    # The total video is bullseye_duration + anim_duration + freeze_duration (3 + 18.76 + 20 = 41.76 sec).
    # We only want the frames from the freeze_duration part.
    total_duration = bullseye_duration + anim_duration + freeze_duration
    fraction_to_keep = freeze_duration / total_duration
    
    total_frames = len(pred_series)
    frames_to_keep = int(total_frames * fraction_to_keep)
    
    # Slice the series to only include the last 'frames_to_keep'
    if frames_to_keep > 0:
        pred_series = pred_series.tail(frames_to_keep)
    
    left_frames = (pred_series == 'left').sum()
    right_frames = (pred_series == 'right').sum()
    away_frames = (pred_series == 'away').sum()
    
    return left_frames, right_frames, away_frames

def load_test_orders(json_path):
    """
    Loads test orders from the Lookit response JSON.
    Returns a dictionary: response_uuid -> test_order_list
    """
    test_orders = {}
    try:
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            resp = item.get('response', {})
            uuid = resp.get('uuid')
            if not uuid:
                continue
            exp_data = item.get('exp_data', [])
            for trial in exp_data:
                if 'test_order' in trial:
                    test_orders[uuid] = trial['test_order']
                    break
    except Exception as e:
        print(f"Error loading JSON data from {json_path}: {e}")
    return test_orders

def parse_video_filename(filename):
    """
    Parses video filename to extract response_uuid and frame_index.
    Example: videoStream_51062dc4-40ae-45d6-883c-8e5487a899ce_13-start-record-plugin-multiframe_0ac5cef0-b0b1-4f7b-ac9e-6bd79fbc4699_1782433060795_945.webm
    """
    # Regex to capture:
    # 1. frame_index (e.g. 13)
    # 2. response_uuid (e.g. 0ac5cef0-b0b1-4f7b-ac9e-6bd79fbc4699)
    pattern = r"videoStream_[a-f0-9\-]+_(\d+)-start-record-plugin-multiframe_([a-f0-9\-]+)_[0-9]+_[0-9]+\.(webm|mp4)"
    match = re.match(pattern, filename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None

def prepare_videos(videos_dir):
    """
    Finds all non-consent webm and mp4 videos.
    Converts webm videos to mp4 without audio if needed.
    Returns list of dicts: {'orig_name': ..., 'path': ..., 'is_temp': ...}
    """
    temp_dir = os.path.join(videos_dir, "temp_mp4")
    all_webms = glob.glob(os.path.join(videos_dir, "*.webm"))
    all_mp4s = glob.glob(os.path.join(videos_dir, "*.mp4"))
    
    prepared = []
    
    # Check if there are any webms to convert
    webms_to_convert = [w for w in all_webms if not os.path.basename(w).startswith("consent-")]
    
    if webms_to_convert:
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
    # Process webms (convert to mp4)
    for webm in webms_to_convert:
        base_name = os.path.basename(webm)
        mp4_name = os.path.splitext(base_name)[0] + ".mp4"
        mp4_path = os.path.join(temp_dir, mp4_name)
        
        # Convert webm to mp4 using ffmpeg
        if not os.path.exists(mp4_path):
            print(f"Converting {base_name} to MP4 format for compatibility...")
            cmd = [
                "ffmpeg", "-y", "-i", webm,
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                mp4_path
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as e:
                print(f"Error converting {base_name}: {e}")
                continue
                
        prepared.append({
            "orig_name": base_name,
            "path": mp4_path,
            "is_temp": True
        })
        
    # Process existing mp4s (non-consent)
    for mp4 in all_mp4s:
        base_name = os.path.basename(mp4)
        if base_name.startswith("consent-"):
            continue
        if "temp_mp4" in mp4:
            continue
        prepared.append({
            "orig_name": base_name,
            "path": mp4,
            "is_temp": False
        })
        
    return prepared, temp_dir

def main():
    if len(sys.argv) < 3:
        print("Usage: python process_icatcher.py <path_to_videos_directory> <path_to_response_json>")
        sys.exit(1)
        
    videos_dir = sys.argv[1]
    json_path = sys.argv[2]
    
    if not os.path.isdir(videos_dir):
        print(f"Error: {videos_dir} is not a valid directory.")
        sys.exit(1)
        
    if not os.path.isfile(json_path):
        print(f"Error: {json_path} is not a valid file.")
        sys.exit(1)
        
    # Load test orders from JSON
    test_orders = load_test_orders(json_path)
    print(f"Loaded trial configurations for {len(test_orders)} responses from JSON.")
    
    # Prepare videos (converts webm to mp4 if needed)
    prepared, temp_dir = prepare_videos(videos_dir)
    print(f"Found {len(prepared)} experimental trial videos to process.")
    
    results = []
    
    try:
        for item in prepared:
            video_path = item["path"]
            orig_name = item["orig_name"]
            
            frame_idx, resp_uuid = parse_video_filename(orig_name)
            if not resp_uuid or frame_idx is None:
                print(f"Skipping non-conforming video: {orig_name}")
                continue
                
            order = test_orders.get(resp_uuid)
            if not order or len(order) < 2:
                print(f"Warning: No test order found in JSON for response UUID {resp_uuid}. Setting condition to 'unknown'.")
                condition = "unknown"
            else:
                if frame_idx == 9:
                    condition = order[0]
                elif frame_idx == 13:
                    condition = order[1]
                else:
                    condition = f"frame_{frame_idx}"
                    
            output_txt = run_icatcher(video_path)
            if output_txt:
                left_frames, right_frames, away_frames = analyze_gaze(output_txt)
            else:
                left_frames, right_frames, away_frames = 0, 0, 0
                
            results.append({
                "Response UUID": resp_uuid,
                "Frame Index": frame_idx,
                "Condition": condition,
                "Left Looking Frames": left_frames,
                "Right Looking Frames": right_frames,
                "Away/Other Frames": away_frames,
                "Video Filename": orig_name
            })
    finally:
        # Cleanup temp MP4 folder if it exists
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            print("Cleaned up temporary MP4 files.")
        
    if not results:
        print("No matching video files were processed.")
        sys.exit(0)
        
    summary_df = pd.DataFrame(results)
    
    # Sort results by UUID and Frame Index for neatness
    summary_df = summary_df.sort_values(by=["Response UUID", "Frame Index"])
    
    print("\n--- Summary Results ---")
    print(summary_df.to_string(index=False))
    
    summary_csv = "icatcher_summary_results.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"\nSaved detailed summary to {summary_csv}")

if __name__ == "__main__":
    main()
