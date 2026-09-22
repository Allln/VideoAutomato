from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal

from .ffmpeg import FFmpegStatus, detect_ffmpeg
from .models import Project
from .tts import ProviderStatus, resolve_tts_provider

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    message: str


@dataclass(frozen=True)
class ValidationReport:
    findings: tuple[Finding, ...]

    @property
    def has_errors(self) -> bool:
        return any(finding.severity == "error" for finding in self.findings)

    def format_lines(self) -> list[str]:
        prefixes = {"error": "ERROR", "warning": "WARN", "info": "INFO"}
        return [f"[{prefixes[finding.severity]}] {finding.message}" for finding in self.findings]


def validate_project(
    project: Project,
    *,
    ffmpeg_detector: Callable[[str], FFmpegStatus] = detect_ffmpeg,
    provider_resolver: Callable[[str], ProviderStatus] = resolve_tts_provider,
) -> ValidationReport:
    findings: list[Finding] = []

    findings.extend(_validate_scene_assets(project))

    ffmpeg_status = ffmpeg_detector("ffmpeg")
    if ffmpeg_status.available:
        findings.append(Finding("info", f"FFmpeg available at {ffmpeg_status.executable}."))
    else:
        findings.append(
            Finding(
                "warning",
                f"FFmpeg unavailable: {ffmpeg_status.detail}. Video encoding is disabled, but 'render --image-only' still works.",
            )
        )

    if project.audio.music is not None and not project.audio.music.path.is_file():
        findings.append(Finding("error", f"Music file not found: {project.audio.music.path}"))

    needs_tts = project.audio.tts.enabled and any(scene.voiceover for scene in project.scenes)
    if needs_tts:
        provider_status = provider_resolver(project.audio.tts.provider)
        if provider_status.available:
            findings.append(Finding("info", provider_status.detail))
        else:
            findings.append(
                Finding(
                    "warning",
                    f"TTS provider '{project.audio.tts.provider}' unavailable: {provider_status.detail}. Narration will be skipped.",
                )
            )

    if not any(scene.voiceover for scene in project.scenes):
        findings.append(Finding("info", "No scene voiceovers configured."))
    if project.audio.music is None:
        findings.append(Finding("info", "No background music configured."))

    return ValidationReport(findings=tuple(findings))


def _validate_scene_assets(project: Project) -> Iterable[Finding]:
    for scene in project.scenes:
        if not scene.image.is_file():
            yield Finding("error", f"Scene '{scene.id}' image not found: {scene.image}")
        if scene.duration is not None and scene.duration <= 0:
            yield Finding("error", f"Scene '{scene.id}' duration must be positive.")
        if scene.duration is None and not scene.voiceover:
            yield Finding("error", f"Scene '{scene.id}' uses duration: auto but has no voiceover.")
    if not project.scenes:
        yield Finding("error", "At least one scene is required.")
