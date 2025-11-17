from pathlib import Path

from blur_pipeline.config import ProcessedVideo, ProcessingConfig


def test_derived_paths_create_directories(tmp_path):
    """derived_paths should create the output directory and expected filenames."""
    source = tmp_path / "source.mp4"
    output = tmp_path / "results" / "blurred_output.mp4"
    config = ProcessingConfig(source_video=source, output_video=output, sample_frames=250)

    paths = config.derived_paths()

    assert output.parent.exists()
    assert paths.full_video_only.name == "blurred_output_video_only.mp4"
    assert paths.sample_video_only.name == "blurred_output_sample_video.mp4"
    assert paths.sample_final.name == "blurred_output_sample.mp4"


def test_processed_video_duration():
    """ProcessedVideo.duration returns seconds when fps>0, otherwise None."""
    video = ProcessedVideo(path=Path("video.mp4"), frame_count=300, fps=30.0)
    assert video.duration == 10.0

    no_fps = ProcessedVideo(path=Path("video.mp4"), frame_count=300, fps=0.0)
    assert no_fps.duration is None

