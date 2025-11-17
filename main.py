# import cv2

# # Check iGPU Support
# print(f"OpenCL Available: {cv2.ocl.haveOpenCL()}")

# # Check Video Metadata
# video_path = 'Tuesday.mp4'
# cap = cv2.VideoCapture(video_path)

# if cap.isOpened():
#     w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#     print(f"Resolution: {w}x{h}")
#     print(f"FPS: {fps}")
#     print(f"Total Frames: {count}")
# else:
#     print("Could not read video.")

# cap.release()

import cv2
import random
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from tqdm import tqdm

def main():
    video_path = Path('../Tuesday.mp4')
    final_output_path = Path('blurred_output.mp4')
    sample_frames = 500

    sample_video_path = final_output_path.with_name(
        f"{final_output_path.stem}_sample_video{final_output_path.suffix}"
    )
    sample_final_path = final_output_path.with_name(
        f"{final_output_path.stem}_sample{final_output_path.suffix}"
    )
    full_video_path = final_output_path.with_name(
        f"{final_output_path.stem}_video_only{final_output_path.suffix}"
    )

    k_size = get_blur_strength(str(video_path))
    print(f"Selected Blur Kernel Size: {k_size}")

    print(f"Creating sample ({sample_frames} frames) ...")
    process_video(
        str(video_path),
        str(sample_video_path),
        k_size,
        max_frames=sample_frames,
        description="Sample",
    )
    mux_audio(str(video_path), str(sample_video_path), str(sample_final_path))
    print(f"Sample saved to {sample_final_path}")

    response = input("Type YES to process the entire video: ").strip().upper()
    if response != "YES":
        print("Aborted full processing.")
        return

    process_video(
        str(video_path),
        str(full_video_path),
        k_size,
        max_frames=None,
        description="Full Video",
    )
    mux_audio(str(video_path), str(full_video_path), str(final_output_path))
    print(f"Full output saved to {final_output_path}")

def get_blur_strength(path):
    cap = cv2.VideoCapture(path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Jump to random frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, random.randint(0, total_frames - 1))
    ret, frame = cap.read()
    cap.release()

    if not ret: sys.exit("Error reading video file.")

    # Load to iGPU memory
    cv2.ocl.setUseOpenCL(True)
    umat_frame = cv2.UMat(frame)
    
    window = "Preview (Adjust Slider, Press SPACE to Start)"
    cv2.namedWindow(window)
    val = [0]

    def on_track(v):
        val[0] = v
        k = max(1, 2 * v + 1) # Ensure kernel is odd
        # Box Blur
        preview = cv2.blur(umat_frame, (k, k))
        cv2.imshow(window, preview)

    cv2.createTrackbar("Strength", window, 0, 50, on_track)
    on_track(0)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 32: # Space
            break
        if key == 27: # Esc
            sys.exit("Cancelled.")
            
    cv2.destroyAllWindows()
    return max(1, 2 * val[0] + 1)

# def process_video(input_path, output_path, k_size):
#     cap = cv2.VideoCapture(input_path)
#     w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
#     out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
#     cv2.ocl.setUseOpenCL(True)
    
#     print("Processing started... (Press Ctrl+C to stop)")
    
#     count = 0
#     while True:
#         ret, frame = cap.read()
#         if not ret: break
        
#         # Apply Blur on iGPU
#         umat = cv2.UMat(frame)
#         blurred = cv2.blur(umat, (k_size, k_size))
        
#         # .get() pulls texture back to CPU for saving
#         out.write(blurred.get())
        
#         count += 1
#         if count % 1000 == 0:
#             print(f"Progress: {count}/{total} ({count/total:.1%})")

#     cap.release()
#     out.release()
#     print("Done.")

def process_video(
    input_path: str,
    output_path: str,
    k_size: int,
    max_frames: Optional[int],
    description: str,
) -> None:
    cap = cv2.VideoCapture(input_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0 or not cap.isOpened():
        cap.release()
        raise RuntimeError("Unable to read video metadata.")

    frames_to_process = min(total_frames, max_frames) if max_frames else total_frames

    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    cv2.ocl.setUseOpenCL(True)

    pbar = tqdm(total=frames_to_process, desc=description, unit="frame")
    processed = 0

    while processed < frames_to_process:
        ret, frame = cap.read()
        if not ret:
            break

        umat = cv2.UMat(frame)
        blurred = cv2.blur(umat, (k_size, k_size))
        out.write(blurred.get())

        processed += 1
        pbar.update(1)

    pbar.close()
    cap.release()
    out.release()
    print(f"{description} complete ({processed} frames).")


def mux_audio(source_video, processed_video, output_video):
    """
    OpenCV drops audio tracks. Use ffmpeg (if available) to remux the
    original audio into the blurred video. If ffmpeg is missing, fall back
    to returning the processed video without audio but notify the user.
    """
    processed_path = Path(processed_video)
    output_path = Path(output_video)

    if not processed_path.exists():
        raise FileNotFoundError(f"Processed video not found at {processed_path}")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("Warning: ffmpeg not found in PATH. Output will not contain audio.")
        processed_path.replace(output_path)
        return

    command = [
        ffmpeg_path,
        "-y",
        "-i", str(processed_path),
        "-i", source_video,
        "-map", "0:v:0",
        "-map", "1:a?",
        "-c:v", "copy",
        "-c:a", "copy",
        str(output_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        processed_path.replace(output_path)
        raise RuntimeError(
            "ffmpeg failed to mux audio:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    processed_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()