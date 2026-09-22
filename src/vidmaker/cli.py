from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import ConfigError, load_project_config
from .pipeline import generate_preview, render_project
from .validation import validate_project


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vidmaker", description="Create simple narrated slide-style videos from YAML.")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser("validate", help="Parse and validate a project YAML file.")
    validate_parser.add_argument("config", type=Path)
    validate_parser.set_defaults(handler=_handle_validate)

    render_parser = subparsers.add_parser("render", help="Render video output or image-only frame assets.")
    render_parser.add_argument("config", type=Path)
    render_parser.add_argument("--output", type=Path, help="Video output file, or output directory with --image-only.")
    render_parser.add_argument("--image-only", action="store_true", help="Generate scene frames and manifest without FFmpeg.")
    render_parser.add_argument("--work-dir", type=Path, help="Working directory for generated frames and temporary files.")
    render_parser.set_defaults(handler=_handle_render)

    preview_parser = subparsers.add_parser("preview", help="Render a single scene preview image.")
    preview_parser.add_argument("config", type=Path)
    preview_parser.add_argument("--scene", type=int, default=1, help="1-based scene number to preview.")
    preview_parser.add_argument("--output", type=Path, help="Destination PNG path.")
    preview_parser.set_defaults(handler=_handle_preview)

    return parser


def _handle_validate(args: argparse.Namespace) -> int:
    try:
        project = load_project_config(args.config.resolve())
    except ConfigError as error:
        for message in error.messages:
            print(f"[ERROR] {message}", file=sys.stderr)
        return 2

    report = validate_project(project)
    for line in report.format_lines():
        stream = sys.stderr if line.startswith("[ERROR]") else sys.stdout
        print(line, file=stream)
    if not report.has_errors:
        print("[OK] Project configuration is valid.")
    return 2 if report.has_errors else 0


def _handle_render(args: argparse.Namespace) -> int:
    try:
        project = load_project_config(args.config.resolve())
        result = render_project(
            project,
            output=args.output.resolve() if args.output else None,
            image_only=bool(args.image_only),
            work_dir=args.work_dir.resolve() if args.work_dir else None,
        )
    except (ConfigError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2

    if result.image_only:
        print(f"Generated image-only assets in {result.frames_dir}")
    else:
        print(f"Rendered video to {result.output_path}")
    print(f"Frame list written to {result.concat_path}")
    return 0


def _handle_preview(args: argparse.Namespace) -> int:
    try:
        project = load_project_config(args.config.resolve())
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 2

    scene_index = args.scene - 1
    if scene_index < 0 or scene_index >= len(project.scenes):
        print(f"Scene index {args.scene} is out of range.", file=sys.stderr)
        return 2

    output = args.output.resolve() if args.output else (project.base_dir / f"preview_{project.scenes[scene_index].id}.png")
    preview = generate_preview(project, scene_index, output)
    print(f"Preview for '{preview.scene_id}' written to {preview.output_path}")
    return 0
