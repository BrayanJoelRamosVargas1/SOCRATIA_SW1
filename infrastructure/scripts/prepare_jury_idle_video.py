"""Prepare bounded native alpha loops on the server, never on the student's PC.
Run inside the backend image with imageio-ffmpeg installed; preserve asset notices.
"""
import json
import subprocess
from pathlib import Path
import imageio_ffmpeg
import numpy as np
from PIL import Image

ff = imageio_ffmpeg.get_ffmpeg_exe()
root = Path("/public/vendor/dh-live")
width, height = 288, 432
rows = []
for folder in ["assets", "assets2", "daniel-fictional"]:
    target = root / folder
    common = [ff, "-hide_banner", "-loglevel", "error", "-threads", "1"]
    decoder = subprocess.Popen(common + ["-ss", "0.6", "-i", str(target / "listening.mp4"),
        "-t", "6", "-vf", f"scale={width}:{height},fps=12", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    encoder = subprocess.Popen(common + ["-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", "12", "-i", "-",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-threads", "1", "-b:v", "0", "-crf", "35", "-deadline", "realtime", "-cpu-used", "8", "-an", str(target / "listening-lite.webm")], stdin=subprocess.PIPE)
    first = True
    try:
        while True:
            raw = decoder.stdout.read(width * height * 3)
            if not raw:
                break
            if len(raw) != width * height * 3:
                raise RuntimeError("Incomplete video frame")
            rgb = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3).copy()
            values = rgb.astype(np.float32)
            r, g, b = values[:,:,0], values[:,:,1], values[:,:,2]
            green = (g > 65) & (g > r*1.3) & (g > b*1.2)
            alpha = np.where(green, 0, 255).astype(np.uint8)
            rgba = np.dstack([rgb, alpha])
            if first:
                Image.fromarray(rgba).save(target / "portrait.webp", lossless=True)
                first = False
            encoder.stdin.write(rgba.tobytes())
    finally:
        decoder.stdout.close()
        encoder.stdin.close()
        if decoder.wait(timeout=30) or encoder.wait(timeout=30):
            raise RuntimeError("Video conversion failed")
    rows.append({"folder":folder,"mp4":(target/"listening.mp4").stat().st_size,
        "webm":(target/"listening-lite.webm").stat().st_size,"poster":(target/"portrait.webp").stat().st_size})
print(json.dumps(rows), flush=True)
