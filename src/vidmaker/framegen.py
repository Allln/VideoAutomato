from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

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
    draw = ImageDraw.Draw(canvas)

    image_region = (96, 150, 980, 820)
    with Image.open(scene.image) as source_image:
        prepared = ImageOps.contain(source_image.convert("RGBA"), (image_region[2], image_region[3]))
        image_x = image_region[0] + (image_region[2] - prepared.width) // 2
        image_y = image_region[1] + (image_region[3] - prepared.height) // 2
        frame = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        frame.paste(prepared, (image_x, image_y), prepared)
        canvas.alpha_composite(frame)

    draw.rounded_rectangle((1000, 130, 1820, 900), radius=36, fill=(10, 18, 30, 215))
    draw.rounded_rectangle((72, 72, 1848, 1008), radius=42, outline=(255, 255, 255, 48), width=3)

    title_font = _load_font(54, bold=True)
    body_font = _load_font(30)
    meta_font = _load_font(24)
    accent_font = _load_font(28, bold=True)

    draw.text((1040, 170), scene.title, font=title_font, fill=(245, 248, 255))
    title_bar_bottom = 258
    draw.rounded_rectangle((1040, title_bar_bottom, 1330, title_bar_bottom + 10), radius=5, fill=(110, 177, 255, 255))

    text_top = 310
    for line in _wrap_text(draw, scene.body, body_font, max_width=730):
        draw.text((1040, text_top), line, font=body_font, fill=(224, 229, 240))
        text_top += 46

    footer_y = 940
    draw.text((96, footer_y), project.title, font=accent_font, fill=(187, 205, 243))
    duration_label = f"{scene.duration:.1f}s" if scene.duration is not None else "auto"
    draw.text((1600, footer_y), duration_label, font=meta_font, fill=(187, 205, 243))

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
