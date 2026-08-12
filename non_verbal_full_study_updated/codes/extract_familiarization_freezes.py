from PIL import Image, ImageSequence
import os
import shutil

dest_dir = "../materials/"

for i in range(1, 9):
    gif_path = f"Fam_Combo_{i}.gif"
    png_path = f"Fam_Combo_{i}_freeze.png"
    print(f"Extracting last frame of {gif_path} to {png_path}...")
    
    if os.path.exists(gif_path):
        img = Image.open(gif_path)
        frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
        last_frame = frames[-1]
        
        # Ensure it's RGB
        if last_frame.mode != 'RGB':
            last_frame = last_frame.convert('RGB')
            
        last_frame.save(png_path)
        print(f"Saved {png_path}")
        
        # Copy to non_verbal_full_study/materials
        if os.path.exists(dest_dir):
            shutil.copy(png_path, os.path.join(dest_dir, png_path))
            print(f"  Copied {png_path} to {dest_dir}")
    else:
        print(f"File {gif_path} does not exist. Please run familiarization_trials.py first.")
