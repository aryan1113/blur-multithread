from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Optional

import cv2
from tqdm import tqdm

from .config import ProcessedVideo
import itertools

def blur_frame(frame_arr, k):
    import cv2
    umat = cv2.UMat(frame_arr)
    blurred = cv2.blur(umat, (k, k))
    return blurred.get()


def get_blur_strength(path: str) -> int:
    cap = cv2.VideoCapture(path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames <= 0:
        cap.release()
        sys.exit("Error reading video file.")

    cap.set(cv2.CAP_PROP_POS_FRAMES, random.randint(0, total_frames - 1))
    ret, frame = cap.read()
    cap.release()

    if not ret:
        sys.exit("Error reading video file.")

    cv2.ocl.setUseOpenCL(True)
    umat_frame = cv2.UMat(frame)

    window = "Preview (Adjust Slider, Press SPACE to Start)"
    cv2.namedWindow(window)
    val = [0]

    def on_track(v: int) -> None:
        val[0] = v
        k = max(1, 2 * v + 1)
        preview = cv2.blur(umat_frame, (k, k))
        cv2.imshow(window, preview)

    cv2.createTrackbar("Strength", window, 0, 50, on_track)
    on_track(0)

    while True:
        key = cv2.waitKey(1) & 0xFF
        # Space to confirm, Esc to exit
        if key == 32:
            break
        if key == 27:
            sys.exit("Cancelled.")

    cv2.destroyAllWindows()
    return max(1, 2 * val[0] + 1)


def process_video(
    input_path: str,
    output_path: str,
    k_size: int,
    max_frames: Optional[int],
    description: str,
    start_frame: int = 0,
) -> ProcessedVideo:
    import time
    from concurrent.futures import ProcessPoolExecutor
    import numpy as np

    t_start = time.perf_counter()
    cap = cv2.VideoCapture(input_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0 or not cap.isOpened():
        cap.release()
        raise RuntimeError("Unable to read video metadata.")

    # Seek to start_frame
    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frames_left = total_frames - start_frame
    frames_to_process = min(frames_left, max_frames) if max_frames else frames_left

    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    cv2.ocl.setUseOpenCL(True)

    # hyperparam
    batch_size = 32
    pbar = tqdm(total=frames_to_process, desc=description, unit="frame")
    processed = 0

    t_read = 0
    t_blur = 0
    t_write = 0


    with ProcessPoolExecutor() as executor:
        while processed < frames_to_process:
            t0 = time.perf_counter()
            frames = []
            for _ in range(min(batch_size, frames_to_process - processed)):
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            t1 = time.perf_counter()
            t_read += t1 - t0
            if not frames:
                break

            t2 = time.perf_counter()
            # Use itertools.repeat to pass k_size to each call
            blurred_frames = list(executor.map(blur_frame, frames, itertools.repeat(k_size)))
            t3 = time.perf_counter()
            t_blur += t3 - t2

            t4 = time.perf_counter()
            for bf in blurred_frames:
                out.write(bf)
            t5 = time.perf_counter()
            t_write += t5 - t4

            processed += len(frames)
            pbar.update(len(frames))

    pbar.close()
    cap.release()
    out.release()
    t_end = time.perf_counter()
    print(f"{description} complete ({processed} frames). Total: {t_end-t_start:.2f}s | Read: {t_read:.2f}s | Blur: {t_blur:.2f}s | Write: {t_write:.2f}s")
    return ProcessedVideo(path=Path(output_path), frame_count=processed, fps=fps)

