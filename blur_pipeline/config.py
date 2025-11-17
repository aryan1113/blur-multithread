from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OutputPaths:
    full_video_only: Path
    sample_video_only: Path
    sample_final: Path


@dataclass
class ProcessingConfig:
    source_video: Path
    output_video: Path
    sample_frames: int = 500

    def derived_paths(self) -> OutputPaths:
        self.output_video.parent.mkdir(parents=True, exist_ok=True)
        return OutputPaths(
            full_video_only=self.output_video.with_name(
                f"{self.output_video.stem}_video_only{self.output_video.suffix}"
            ),
            sample_video_only=self.output_video.with_name(
                f"{self.output_video.stem}_sample_video{self.output_video.suffix}"
            ),
            sample_final=self.output_video.with_name(
                f"{self.output_video.stem}_sample{self.output_video.suffix}"
            ),
        )


@dataclass
class ProcessedVideo:
    path: Path
    frame_count: int
    fps: float

    @property
    def duration(self) -> Optional[float]:
        if self.fps <= 0:
            return None
        return self.frame_count / self.fps

