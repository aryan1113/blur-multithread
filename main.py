
from pathlib import Path
import argparse
from blur_pipeline.config import ProcessingConfig
from blur_pipeline.pipeline import VideoBlurPipeline

import cv2
import os
import math

def print_video_metadata(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = count / fps if fps else 0
        print(f"Source Video Metadata:")
        print(f"  Resolution: {w}x{h}")
        print(f"  FPS: {fps}")
        print(f"  Total Frames: {count}")
        print(f"  Duration: {duration:.2f} seconds ({math.floor(duration//60):02}:{math.floor(duration%60):02})")
        # File size and bitrate
        try:
            file_size = os.path.getsize(video_path)
            print(f"  File Size: {file_size/1024/1024:.2f} MB")
            if duration > 0:
                bitrate = (file_size * 8) / duration / 1000  # kbps
                print(f"  Approx Bitrate: {bitrate:.0f} kbps")
        except Exception:
            pass
    else:
        print("Could not read video.")
    cap.release()

def main() -> None:
    parser = argparse.ArgumentParser(description="Blur video pipeline")
    parser.add_argument("--skip-sample", action="store_true", help="Skip creating the sample video")
    parser.add_argument("--debug", action="store_true", help="Print video metadata for debugging")
    parser.add_argument("--cfr-fps", type=float, default=30, help="Convert input video to CFR at this FPS (default: 30)")
    args = parser.parse_args()

    source_path = "../Tuesday.mp4"
    cfr_path = "../Tuesday_cfr.mp4"

    # Convert to CFR if not already
    import subprocess
    import os
    if not os.path.exists(cfr_path):
        print(f"Converting {source_path} to CFR at {args.cfr_fps} FPS ...")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", source_path,
            "-vsync", "cfr",
            "-r", str(args.cfr_fps),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            cfr_path
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("FFmpeg CFR conversion failed:")
            print(result.stderr)
            exit(1)
        print(f"CFR video created: {cfr_path}")
    else:
        print(f"CFR video already exists: {cfr_path}")

    if args.debug:
        print_video_metadata(cfr_path)

    config = ProcessingConfig(
        source_video=Path(cfr_path),
        output_video=Path("results/blurred_output.mp4"),
        sample_frames=5,
    )
    VideoBlurPipeline(config).run(skip_sample=args.skip_sample)

if __name__ == "__main__":
    main()

