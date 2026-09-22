from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import wave

from .ffmpeg import detect_ffmpeg, render_video, write_concat_file
from .framegen import FrameArtifact, render_scene_frame, render_scene_frames
from .models import Project
from .tts import create_tts_provider


@dataclass(frozen=True)
class PreviewResult:
    scene_id: str
    output_path: Path


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    frames_dir: Path
    concat_path: Path
    image_only: bool


def generate_preview(project: Project, scene_index: int, destination: Path) -> PreviewResult:
    scene = project.scenes[scene_index]
    render_scene_frame(project, scene, destination)
    return PreviewResult(scene_id=scene.id, output_path=destination)


def render_project(
    project: Project,
    *,
    output: Path | None = None,
    image_only: bool = False,
    work_dir: Path | None = None,
) -> RenderResult:
    if image_only and output is not None:
        frames_dir = output
        render_root = work_dir or output
    else:
        render_root = work_dir or (project.base_dir / "build" / _slugify(project.title))
        frames_dir = render_root / "frames"
    render_root.mkdir(parents=True, exist_ok=True)
    voiceovers = _synthesize_voiceovers(project, project.scenes, render_root / "voiceovers")
    durations = _resolve_scene_durations(project, voiceovers)
    frames = render_scene_frames(project, frames_dir, durations=durations)
    concat_path = write_concat_file(frames, render_root / "frames.txt")
    _write_manifest(project, frames, render_root / "render_manifest.json")

    if image_only:
        return RenderResult(output_path=frames_dir, frames_dir=frames_dir, concat_path=concat_path, image_only=True)

    ffmpeg_status = detect_ffmpeg("ffmpeg")
    if not ffmpeg_status.available or ffmpeg_status.executable is None:
        raise RuntimeError("FFmpeg is unavailable. Run 'validate' for details or use 'render --image-only'.")

    output_path = output or project.video.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = render_video(
        project,
        frames,
        output_path,
        concat_path,
        ffmpeg_executable=ffmpeg_status.executable,
        voiceovers=voiceovers,
        music=project.audio.music,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "FFmpeg exited with an error."
        raise RuntimeError(f"FFmpeg rendering failed: {stderr}")
    return RenderResult(output_path=output_path, frames_dir=frames_dir, concat_path=concat_path, image_only=False)


def _synthesize_voiceovers(project: Project, scenes: tuple, voiceover_dir: Path) -> tuple[Path | None, ...]:
    if not project.audio.tts.enabled:
        return tuple(None for _ in frames)

    provider = create_tts_provider(project.audio.tts.provider)
    if provider is None:
        return tuple(None for _ in frames)

    if not provider.check_availability().available:
        return tuple(None for _ in frames)

    rendered: list[Path | None] = []
    for scene in scenes:
        if not scene.voiceover:
            rendered.append(None)
            continue
        output_path = voiceover_dir / f"{scene.id}.wav"
        provider.synthesize(scene.voiceover, output_path, project.audio.tts)
        rendered.append(output_path)
    return tuple(rendered)


def _resolve_scene_durations(project: Project, voiceovers: tuple[Path | None, ...]) -> tuple[float, ...]:
    durations: list[float] = []
    for index, (scene, voiceover) in enumerate(zip(project.scenes, voiceovers)):
        if scene.duration is not None:
            base_duration = scene.duration
        elif voiceover is None:
            raise RuntimeError(
                f"Scene '{scene.id}' uses duration: auto but has no generated voiceover. "
                "Add voiceover text or set a numeric duration."
            )
        else:
            base_duration = _wave_duration(voiceover) + project.audio.auto_duration_padding
        if index < len(project.scenes) - 1:
            base_duration += project.audio.pause_between_scenes
        durations.append(base_duration)
    return tuple(durations)


def _wave_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        frame_rate = audio.getframerate()
        if frame_rate <= 0:
            raise RuntimeError(f"Generated voiceover has an invalid sample rate: {path}")
        return audio.getnframes() / frame_rate


def _write_manifest(project: Project, frames: tuple[FrameArtifact, ...], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "title": project.title,
        "video": {
            "width": project.video.width,
            "height": project.video.height,
            "fps": project.video.fps,
            "background_color": project.video.background_color,
        },
        "scenes": [
            {
                "id": frame.scene.id,
                "title": frame.scene.title,
                "duration": frame.duration,
                "frame": str(frame.path),
            }
            for frame in frames
        ],
    }
    destination.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _slugify(value: str) -> str:
    parts = ["".join(ch.lower() for ch in token if ch.isalnum()) for token in value.split()]
    return "-".join(part for part in parts if part) or "vidmaker"
