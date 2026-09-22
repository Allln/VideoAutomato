from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from .framegen import FrameArtifact
from .models import MusicSettings, Project


@dataclass(frozen=True)
class FFmpegStatus:
    available: bool
    executable: str | None
    detail: str


def detect_ffmpeg(executable: str) -> FFmpegStatus:
    resolved = shutil.which(executable)
    if resolved is None:
        return FFmpegStatus(False, None, f"'{executable}' was not found on PATH.")
    return FFmpegStatus(True, resolved, "OK")


def write_concat_file(frames: tuple[FrameArtifact, ...], destination: Path) -> Path:
    lines: list[str] = []
    for frame in frames:
        escaped = str(frame.path).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
        lines.append(f"duration {frame.duration:.3f}")
    if frames:
        escaped = str(frames[-1].path).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def render_video(
    project: Project,
    frames: tuple[FrameArtifact, ...],
    output_path: Path,
    concat_path: Path,
    *,
    ffmpeg_executable: str,
    voiceovers: tuple[Path | None, ...],
    music: MusicSettings | None,
) -> subprocess.CompletedProcess[str]:
    filter_complex, input_args, audio_map = _build_audio_pipeline(frames, voiceovers, music)

    command = [
        ffmpeg_executable,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        *input_args,
        "-vf",
        f"fps={project.video.fps},format=yuv420p",
    ]
    if filter_complex:
        command.extend(["-filter_complex", filter_complex, "-map", "0:v:0", "-map", audio_map])
    else:
        command.extend(["-map", "0:v:0"])
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(output_path)])
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _build_audio_pipeline(
    frames: tuple[FrameArtifact, ...],
    voiceovers: tuple[Path | None, ...],
    music: MusicSettings | None,
) -> tuple[str | None, list[str], str]:
    input_args: list[str] = []
    filter_parts: list[str] = []
    concat_refs: list[str] = []
    audio_input_indexes: list[int | None] = []
    next_input_index = 1

    for voiceover in voiceovers:
        if voiceover is None:
            audio_input_indexes.append(None)
            continue
        input_args.extend(["-i", str(voiceover)])
        audio_input_indexes.append(next_input_index)
        next_input_index += 1

    music_input_index: int | None = None
    if music is not None:
        input_args.extend(["-stream_loop", "-1", "-i", str(music.path)])
        music_input_index = next_input_index

    total_duration = sum(frame.duration for frame in frames)
    for index, frame in enumerate(frames):
        label = f"a{index}"
        source_index = audio_input_indexes[index]
        if source_index is None:
            filter_parts.append(f"anullsrc=r=24000:cl=stereo,atrim=0:{frame.duration:.3f}[{label}]")
        else:
            filter_parts.append(
                f"[{source_index}:a]aformat=sample_fmts=fltp:sample_rates=24000:channel_layouts=stereo,"
                f"apad=pad_dur={frame.duration:.3f},atrim=0:{frame.duration:.3f}[{label}]"
            )
        concat_refs.append(f"[{label}]")

    if not any(audio_input_indexes) and music_input_index is None:
        return None, input_args, ""

    filter_parts.append(f"{''.join(concat_refs)}concat=n={len(frames)}:v=0:a=1[narr]")

    if music_input_index is not None:
        volume = music.volume
        filter_parts.append(
            f"[{music_input_index}:a]aformat=sample_fmts=fltp:sample_rates=24000:channel_layouts=stereo,"
            f"atrim=0:{total_duration:.3f},volume={volume:.3f}[music]"
        )
        filter_parts.append("[narr][music]amix=inputs=2:duration=first:dropout_transition=0[aout]")
        return ";".join(filter_parts), input_args, "[aout]"

    return ";".join(filter_parts), input_args, "[narr]"
