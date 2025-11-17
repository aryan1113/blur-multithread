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

def main():
    video_path = Path('Tuesday.mp4')
    final_output_path = Path('blurred_output.mp4')
    intermediate_path = final_output_path.with_name(
        f"{final_output_path.stem}_video_only{final_output_path.suffix}"
    )

    k_size = get_blur_strength(str(video_path))
    print(f"Selected Blur Kernel Size: {k_size}")

    process_video(str(video_path), str(intermediate_path), k_size)
    mux_audio(str(video_path), str(intermediate_path), str(final_output_path))

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

import threading
from queue import Queue

def process_video(input_path, output_path, k_size):
    cap = cv2.VideoCapture(input_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Queue size 1024 frames (~3GB RAM for 720p)
    read_queue = Queue(maxsize=1024)
    write_queue = Queue(maxsize=1024)
    
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    cv2.ocl.setUseOpenCL(True)

    def reader():
        while True:
            ret, frame = cap.read()
            if not ret:
                read_queue.put(None)
                break
            read_queue.put(frame)
    
    def writer():
        while True:
            frame = write_queue.get()
            if frame is None:
                break
            out.write(frame)
            write_queue.task_done()

    t_read = threading.Thread(target=reader)
    t_write = threading.Thread(target=writer)
    t_read.start()
    t_write.start()
    
    print("Optimized processing started...")
    
    while True:
        frame = read_queue.get()
        if frame is None:
            write_queue.put(None)
            break
        
        umat = cv2.UMat(frame)
        blurred = cv2.blur(umat, (k_size, k_size))
        write_queue.put(blurred.get())

    t_read.join()
    t_write.join()
    cap.release()
    out.release()
    print("Done.")


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