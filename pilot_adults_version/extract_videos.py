#!/usr/bin/env python3
import os
import sys
import json
import base64

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_videos.py <proliferate_responses.json> [output_dir]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "videos_extracted"

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    # Load responses (handle both JSON arrays and JSON Lines format)
    responses = []
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print("Error: Input file is empty.")
                sys.exit(1)
            
            if content.startswith('['):
                responses = json.loads(content)
            elif content.startswith('{'):
                responses = [json.loads(content)]
            else:
                for i, line in enumerate(content.split('\n'), 1):
                    if line.strip():
                        try:
                            responses.append(json.loads(line))
                        except Exception as line_err:
                            print(f"Warning: Failed to parse line {i} as JSON. Skipping. ({line_err})")
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    print(f"Loaded {len(responses)} response(s) from '{input_path}'.")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    extracted_count = 0

    for i, resp in enumerate(responses):
        # Extract participant identifier
        pid = resp.get("participant_id")
        if not pid:
            # Fallback to prolific pid or generate fallback index
            pid = resp.get("results", {}).get("participant_id") or f"participant_{i+1}"
            
        test_order = resp.get("test_order") or resp.get("results", {}).get("test_order")
        videos = resp.get("videos") or resp.get("results", {}).get("videos") or []

        if not videos:
            print(f"No webcam videos found for participant '{pid}'. Skipping.")
            continue

        print(f"Processing participant '{pid}' (test order: {test_order})...")

        for video in videos:
            trial_idx = video.get("trial_idx")
            mime_type = video.get("mime_type", "video/webm")
            base64_data = video.get("base64")

            if not base64_data:
                print(f"  Warning: Empty base64 payload for video index {trial_idx}.")
                continue

            # Determine file extension based on mime type
            ext = ".webm"
            if "mp4" in mime_type.lower():
                ext = ".mp4"

            # Resolve trial condition from test_order
            condition = "unknown"
            if test_order and isinstance(test_order, list):
                try:
                    # trial_idx is 1-indexed
                    condition = test_order[trial_idx - 1]
                except IndexError:
                    pass

            # Strip data URL prefix if present (e.g. "data:video/webm;base64,")
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]

            # Decode base64 bytes
            try:
                video_bytes = base64.b64decode(base64_data)
            except Exception as decode_err:
                print(f"  Error decoding base64 data for trial {trial_idx}: {decode_err}")
                continue

            # Construct clean output filename
            # Naming schema matches videoStream_adult_[ParticipantID]_[TrialIdx]_[Condition].webm
            filename = f"videoStream_adult_{pid}_{trial_idx}_{condition}{ext}"
            filepath = os.path.join(output_dir, filename)

            try:
                with open(filepath, 'wb') as out_f:
                    out_f.write(video_bytes)
                print(f"  Successfully wrote: {filepath} ({len(video_bytes)} bytes)")
                extracted_count += 1
            except Exception as write_err:
                print(f"  Error writing file '{filepath}': {write_err}")

    print(f"\nDone! Extracted {extracted_count} video file(s) into '{output_dir}/'.")

if __name__ == "__main__":
    main()
