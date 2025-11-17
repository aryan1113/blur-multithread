from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence


def mux_audio(
    source_video: str,
    processed_video: str,
    output_video: str,
    duration: Optional[float] = None,
    audio_offset: float = 0.0,
) -> None:
    processed_path = Path(processed_video)
    output_path = Path(output_video)

    if not processed_path.exists():
        raise FileNotFoundError(f"Processed video not found at {processed_path}")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("Warning: ffmpeg not found in PATH. Output will not contain audio.")
        processed_path.replace(output_path)
        return

    command = build_mux_command(
        processed_path=processed_path,
        source_video=source_video,
        output_path=output_path,
        duration=duration,
        ffmpeg_path=ffmpeg_path,
        audio_offset=audio_offset,
    )

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        processed_path.replace(output_path)
        raise RuntimeError(
            "ffmpeg failed to mux audio:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    processed_path.unlink(missing_ok=True)


def build_mux_command(
    *,
    processed_path: Path,
    source_video: str,
    output_path: Path,
    duration: Optional[float],
    ffmpeg_path: str,
    audio_offset: float = 0.0,
) -> List[str]:
    # Always use -ss for audio to align/seek with video sample
    audio_input: Sequence[str] = ["-ss", f"{audio_offset:.6f}", "-i", source_video]
    if duration is not None:
        audio_input += ["-t", f"{duration:.6f}"]

    return [
        ffmpeg_path,
        "-y",
        "-i",
        str(processed_path),
        *audio_input,
        "-map",
        "0:v:0",
        "-map",
        "1:a?",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-shortest",
        "-fflags",
        "+genpts",
        "-avoid_negative_ts",
        "make_zero",
        str(output_path),
    ]

