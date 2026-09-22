from __future__ import annotations

from pathlib import Path

from PIL import Image

from vidmaker.cli import main
from vidmaker.config import load_project_config
from vidmaker.ffmpeg import FFmpegStatus
from vidmaker.framegen import render_scene_frame
from vidmaker.models import Project
from vidmaker.tts import ProviderStatus
from vidmaker.validation import validate_project


def _create_project_yaml(tmp_path: Path, *, include_voiceover: bool = True) -> Path:
    image_path = tmp_path / "slide.png"
    Image.new("RGB", (640, 360), color=(10, 30, 80)).save(image_path)
    voiceover_block = "\n    voiceover: Narration for the scene\n" if include_voiceover else "\n"
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        (
            "title: Test Project\n"
            "video:\n"
            "  width: 1920\n"
            "  height: 1080\n"
            "  fps: 24\n"
            "  output: output/test.mp4\n"
            "  background_color: \"#08111F\"\n"
            "audio:\n"
            "  tts:\n"
            "    enabled: true\n"
            "    provider: windows_sapi\n"
            "scenes:\n"
            "  - id: intro\n"
            "    title: Intro Scene\n"
            "    body: A short explanation for testing.\n"
            f"    image: {image_path.name}\n"
            "    duration: 3\n"
            f"{voiceover_block}"
        ),
        encoding="utf-8",
    )
    return config_path


def test_load_project_config_resolves_relative_paths(tmp_path: Path) -> None:
    config_path = _create_project_yaml(tmp_path)

    project = load_project_config(config_path)

    assert isinstance(project, Project)
    assert project.video.width == 1920
    assert project.scenes[0].image == (tmp_path / "slide.png").resolve()


def test_validate_project_warns_when_optional_tools_unavailable(tmp_path: Path) -> None:
    config_path = _create_project_yaml(tmp_path)
    project = load_project_config(config_path)

    report = validate_project(
        project,
        ffmpeg_detector=lambda _: FFmpegStatus(False, None, "not installed"),
        provider_resolver=lambda _: ProviderStatus(False, "not available"),
    )

    assert not report.has_errors
    messages = "\n".join(report.format_lines())
    assert "FFmpeg unavailable" in messages
    assert "Narration will be skipped" in messages


def test_render_scene_frame_outputs_1920x1080_image(tmp_path: Path) -> None:
    config_path = _create_project_yaml(tmp_path, include_voiceover=False)
    project = load_project_config(config_path)

    output = tmp_path / "preview.png"
    render_scene_frame(project, project.scenes[0], output)

    with Image.open(output) as rendered:
        assert rendered.size == (1920, 1080)


def test_cli_render_image_only_exports_frames(tmp_path: Path) -> None:
    config_path = _create_project_yaml(tmp_path, include_voiceover=False)
    output_dir = tmp_path / "frames_out"
    work_dir = tmp_path / "work"

    exit_code = main(
        [
            "render",
            str(config_path),
            "--image-only",
            "--output",
            str(output_dir),
            "--work-dir",
            str(work_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "001_intro.png").is_file()
    assert (work_dir / "frames.txt").is_file()
