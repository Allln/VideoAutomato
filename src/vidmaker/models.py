from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoSettings:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    output: Path = Path("output.mp4")
    background_color: str = "#08111F"


@dataclass(frozen=True)
class TTSSettings:
    enabled: bool = False
    provider: str = "windows_sapi"
    voice: str | None = None
    rate: int = 0
    volume: int = 100


@dataclass(frozen=True)
class MusicSettings:
    path: Path
    volume: float = 0.2


@dataclass(frozen=True)
class AudioSettings:
    tts: TTSSettings
    music: MusicSettings | None = None
    pause_between_scenes: float = 0.0
    auto_duration_padding: float = 0.5


@dataclass(frozen=True)
class Scene:
    id: str
    title: str
    body: str
    image: Path
    duration: float | None
    voiceover: str | None = None


@dataclass(frozen=True)
class Project:
    title: str
    base_dir: Path
    video: VideoSettings
    audio: AudioSettings
    scenes: tuple[Scene, ...]
