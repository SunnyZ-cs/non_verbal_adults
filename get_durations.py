import os
from PIL import Image

def get_gif_duration(file_path):
    try:
        with Image.open(file_path) as img:
            duration = 0
            for frame in range(img.n_frames):
                img.seek(frame)
                duration += img.info.get('duration', 0)
            return duration
    except Exception as e:
        return str(e)

fam_dir = 'pilot1/stimuli/fam'
for f in sorted(os.listdir(fam_dir)):
    if f.endswith('.gif'):
        path = os.path.join(fam_dir, f)
        print(f"{f}: {get_gif_duration(path)} ms")
