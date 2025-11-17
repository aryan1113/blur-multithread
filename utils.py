# to create a shorter version of the video for testing

import subprocess

source = "../Tuesday.mp4"
output = "../mini_tuesday.mp4"
duration = 600  # seconds (10 minutes)

ffmpeg_cmd = [
    "ffmpeg", "-y", "-i", source,
    "-t", str(duration),
    "-c:v", "copy",  # copy video stream without re-encoding
    "-c:a", "copy",  # copy audio stream without re-encoding
    output
]

result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if result.returncode == 0:
    print(f"Created {output} with first 10 minutes of video and audio.")
else:
    print("Error during FFmpeg processing:")
    print(result.stderr)