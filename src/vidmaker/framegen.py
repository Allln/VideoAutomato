from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

from .models import Project, Scene


@dataclass(frozen=True)
class FrameArtifact:
    scene: Scene
    path: Path
    duration: float


def render_scene_frame(project: Project, scene: Scene, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    canvas = Image.new(
        "RGBA",
        (project.video.width, project.video.height),
        ImageColor.getrgb(project.video.background_color),
    )
    with Image.open(scene.image) as source_image:
        source = source_image.convert("RGBA")
        full_size = canvas.size
        background = ImageOps.fit(source, full_size, method=Image.Resampling.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(radius=18))
        canvas.alpha_composite(background)

        prepared = ImageOps.contain(source, full_size, method=Image.Resampling.LANCZOS)
        image_x = (canvas.width - prepared.width) // 2
        image_y = (canvas.height - prepared.height) // 2
        canvas.alpha_composite(prepared, (image_x, image_y))

    canvas.convert("RGB").save(destination)
    return destination


def render_scene_frames(
    project: Project,
    destination_dir: Path,
    *,
    durations: tuple[float, ...],
) -> tuple[FrameArtifact, ...]:
    artifacts: list[FrameArtifact] = []
    destination_dir.mkdir(parents=True, exist_ok=True)
    for index, scene in enumerate(project.scenes, start=1):
        frame_path = destination_dir / f"{index:03d}_{scene.id}.png"
        render_scene_frame(project, scene, frame_path)
        artifacts.append(FrameArtifact(scene=scene, path=frame_path, duration=durations[index - 1]))
    return tuple(artifacts)


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names: Iterable[str]
    if bold:
        font_names = ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf")
    else:
        font_names = ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf")
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, *, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left
