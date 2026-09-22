from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from .models import AudioSettings, MusicSettings, Project, Scene, TTSSettings, VideoSettings

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class ConfigError(ValueError):
    messages: tuple[str, ...]

    def __str__(self) -> str:
        return "\n".join(self.messages)


def load_project_config(path: Path) -> Project:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ConfigError(("Top-level YAML document must be a mapping.",))
    return parse_project_config(raw, base_dir=path.parent)


def parse_project_config(raw: Mapping[str, Any], *, base_dir: Path) -> Project:
    errors: list[str] = []

    title = _require_str(raw, "title", errors)
    video_raw = _require_mapping(raw, "video", errors)
    audio_raw = _optional_mapping(raw, "audio", errors) or {}
    scenes_raw = raw.get("scenes")

    video = VideoSettings(
        width=_require_positive_int(video_raw, "width", errors, default=1920),
        height=_require_positive_int(video_raw, "height", errors, default=1080),
        fps=_require_positive_int(video_raw, "fps", errors, default=30),
        output=_resolve_path(_require_str(video_raw, "output", errors, default="output.mp4"), base_dir),
        background_color=_require_color(video_raw, "background_color", errors, default="#08111F"),
    )

    tts_raw = _optional_mapping(audio_raw, "tts", errors) or {}
    music_raw = _optional_mapping(audio_raw, "music", errors)
    tts = TTSSettings(
        enabled=_require_bool(tts_raw, "enabled", errors, default=False),
        provider=_require_str(tts_raw, "provider", errors, default="windows_sapi"),
        voice=_optional_str(tts_raw, "voice", errors),
        rate=_require_int(tts_raw, "rate", errors, default=0),
        volume=_require_ranged_int(tts_raw, "volume", errors, minimum=0, maximum=100, default=100),
    )
    music = None
    if music_raw is not None:
        music = MusicSettings(
            path=_resolve_path(_require_str(music_raw, "path", errors), base_dir),
            volume=_require_float(music_raw, "volume", errors, minimum=0.0, maximum=1.0, default=0.2),
        )
    pause_between_scenes = _require_float(
        audio_raw,
        "pause_between_scenes",
        errors,
        minimum=0.0,
        maximum=10.0,
        default=0.0,
    )
    auto_duration_padding = _require_float(
        audio_raw,
        "auto_duration_padding",
        errors,
        minimum=0.0,
        maximum=10.0,
        default=0.5,
    )

    scenes: list[Scene] = []
    if not isinstance(scenes_raw, list) or not scenes_raw:
        errors.append("'scenes' must be a non-empty list.")
    else:
        seen_ids: set[str] = set()
        for index, item in enumerate(scenes_raw):
            if not isinstance(item, Mapping):
                errors.append(f"Scene #{index + 1} must be a mapping.")
                continue
            scene_id = _require_str(item, "id", errors, prefix=f"Scene #{index + 1}: ")
            title_text = _require_str(item, "title", errors, prefix=f"Scene #{index + 1}: ")
            body = _require_str(item, "body", errors, prefix=f"Scene #{index + 1}: ")
            image = _require_str(item, "image", errors, prefix=f"Scene #{index + 1}: ")
            duration = _parse_scene_duration(item, errors, prefix=f"Scene #{index + 1}: ")
            voiceover = _optional_str(item, "voiceover", errors, prefix=f"Scene #{index + 1}: ")
            if scene_id and scene_id in seen_ids:
                errors.append(f"Scene #{index + 1}: duplicate id '{scene_id}'.")
            if scene_id:
                seen_ids.add(scene_id)
            if scene_id and title_text and body and image:
                scenes.append(
                    Scene(
                        id=scene_id,
                        title=title_text,
                        body=body,
                        image=_resolve_path(image, base_dir),
                        duration=duration,
                        voiceover=voiceover,
                    )
                )

    if errors:
        raise ConfigError(tuple(errors))

    return Project(
        title=title,
        base_dir=base_dir,
        video=video,
        audio=AudioSettings(
            tts=tts,
            music=music,
            pause_between_scenes=pause_between_scenes,
            auto_duration_padding=auto_duration_padding,
        ),
        scenes=tuple(scenes),
    )


def _require_mapping(raw: Mapping[str, Any], key: str, errors: list[str]) -> Mapping[str, Any]:
    value = raw.get(key)
    if isinstance(value, Mapping):
        return value
    errors.append(f"'{key}' must be a mapping.")
    return {}


def _optional_mapping(raw: Mapping[str, Any], key: str, errors: list[str]) -> Mapping[str, Any] | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    errors.append(f"'{key}' must be a mapping when provided.")
    return None


def _require_str(
    raw: Mapping[str, Any],
    key: str,
    errors: list[str],
    *,
    default: str | None = None,
    prefix: str = "",
) -> str:
    value = raw.get(key, default)
    if isinstance(value, str) and value.strip():
        return value.strip()
    errors.append(f"{prefix}'{key}' must be a non-empty string.")
    return default or ""


def _optional_str(raw: Mapping[str, Any], key: str, errors: list[str], *, prefix: str = "") -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    errors.append(f"{prefix}'{key}' must be a non-empty string when provided.")
    return None


def _require_bool(raw: Mapping[str, Any], key: str, errors: list[str], *, default: bool) -> bool:
    value = raw.get(key, default)
    if isinstance(value, bool):
        return value
    errors.append(f"'{key}' must be a boolean.")
    return default


def _require_int(raw: Mapping[str, Any], key: str, errors: list[str], *, default: int) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"'{key}' must be an integer.")
        return default
    return value


def _require_positive_int(raw: Mapping[str, Any], key: str, errors: list[str], *, default: int) -> int:
    value = _require_int(raw, key, errors, default=default)
    if value <= 0:
        errors.append(f"'{key}' must be greater than zero.")
        return default
    return value


def _require_ranged_int(
    raw: Mapping[str, Any],
    key: str,
    errors: list[str],
    *,
    minimum: int,
    maximum: int,
    default: int,
) -> int:
    value = _require_int(raw, key, errors, default=default)
    if value < minimum or value > maximum:
        errors.append(f"'{key}' must be between {minimum} and {maximum}.")
        return default
    return value


def _require_float(
    raw: Mapping[str, Any],
    key: str,
    errors: list[str],
    *,
    minimum: float,
    maximum: float | None = None,
    default: float | None = None,
    prefix: str = "",
) -> float:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{prefix}'{key}' must be a number.")
        return default if default is not None else minimum
    float_value = float(value)
    if float_value < minimum:
        errors.append(f"{prefix}'{key}' must be at least {minimum}.")
        return default if default is not None else minimum
    if maximum is not None and float_value > maximum:
        errors.append(f"{prefix}'{key}' must be at most {maximum}.")
        return default if default is not None else maximum
    return float_value


def _require_color(raw: Mapping[str, Any], key: str, errors: list[str], *, default: str) -> str:
    value = raw.get(key, default)
    if isinstance(value, str) and _HEX_COLOR.match(value):
        return value
    errors.append(f"'{key}' must be a hex RGB color like #08111F.")
    return default


def _parse_scene_duration(raw: Mapping[str, Any], errors: list[str], *, prefix: str) -> float | None:
    value = raw.get("duration")
    if isinstance(value, str) and value.strip().lower() == "auto":
        return None
    return _require_float(raw, "duration", errors, minimum=0.1, prefix=prefix)


def _resolve_path(value: str, base_dir: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()
