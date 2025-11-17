from pathlib import Path

from blur_pipeline.audio import build_mux_command


def test_build_mux_command_without_duration(tmp_path):
    """Command should keep sync-related flags when copying full audio stream."""
    processed = tmp_path / "processed.mp4"
    processed.touch()
    output = tmp_path / "out.mp4"

    cmd = build_mux_command(
        processed_path=processed,
        source_video="input.mp4",
        output_path=output,
        duration=None,
        ffmpeg_path="/usr/local/bin/ffmpeg",
    )

    # Ensure command includes key synchronization flags
    assert "-shortest" in cmd
    assert "+genpts" in cmd
    assert "make_zero" in cmd
    assert str(output) == cmd[-1]


def test_build_mux_command_with_duration(tmp_path):
    """Command should trim audio input to processed duration."""
    processed = tmp_path / "processed.mp4"
    processed.touch()
    output = tmp_path / "out.mp4"

    duration = 12.345678
    cmd = build_mux_command(
        processed_path=processed,
        source_video="input.mp4",
        output_path=output,
        duration=duration,
        ffmpeg_path="/usr/local/bin/ffmpeg",
    )

    assert "-t" in cmd
    t_index = cmd.index("-t") + 1
    assert cmd[t_index].startswith("12.345678")

