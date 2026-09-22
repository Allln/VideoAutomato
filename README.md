# VidMaker

VidMaker is a local Python tool for creating simple Full HD YouTube videos
from still images, text, optional Windows voiceover, and optional background
music. It does not generate video footage.

## What it produces

- Resolution: `1920x1080`
- Frame rate: `30 FPS`
- Video: H.264 MP4
- Audio: AAC
- Scene timing: manually configured in YAML
- Scene timing: fixed seconds or automatic from narration
- Narration: optional Windows SAPI voice
- Background music: optional FFmpeg mix

## Installation

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

FFmpeg must also be installed and available on `PATH`.

## Daily project structure

Create one directory per video under `projects/`:

```text
projects/0/
├── project.yaml
├── README.txt
└── images/
    ├── 01_intro.png
    ├── 02_main-idea.png
    └── 03_conclusion.png
```

The YAML file controls the video. Each scene defines:

- `title`: text heading
- `body`: text shown on screen
- `image`: project-relative image path
- `duration`: scene length in seconds, or `auto` to use narration length
- `voiceover`: narration for that scene

The project in [projects/0/](C:/Users/kaucj/PycharmProjects/VidMakerAutomato/projects/0/)
is the first prepared daily example.

## Background music

Reusable music belongs in [src/assets/music/](C:/Users/kaucj/PycharmProjects/VidMakerAutomato/src/assets/music/).
The current track is [1.mp3](C:/Users/kaucj/PycharmProjects/VidMakerAutomato/src/assets/music/1.mp3);
licensing information is stored in [ref.txt](C:/Users/kaucj/PycharmProjects/VidMakerAutomato/src/assets/music/ref.txt).

Reference shared music from a project YAML file like this:

```yaml
audio:
  tts:
    enabled: true
    provider: windows_sapi
    voice: null
    rate: 0
    volume: 100
  music:
    path: ../../src/assets/music/1.mp3
    volume: 0.12
  pause_between_scenes: 1.0
  auto_duration_padding: 0.5
```

Keep music volume low enough that narration remains clear. A value between
`0.08` and `0.15` is a useful starting range.
`pause_between_scenes` adds silence after each scene's narration and extends
the scene image by the same amount, preventing the next narration from
starting immediately or cutting into the previous word.
With `duration: auto`, the renderer synthesizes the narration first, measures
the WAV duration, and makes the scene long enough for that narration plus
`auto_duration_padding` and the transition pause.

## Generate YAML with another LM

Use [prompt.md](C:/Users/kaucj/PycharmProjects/VidMakerAutomato/prompt.md).
Replace only its source-material placeholder, then ask another LM to return
YAML only. Save the result as the project's `project.yaml`.

Review the generated YAML manually, especially:

- factual claims
- image filenames
- scene durations
- narration wording
- music path

## Validate and render

Run commands from the repository root:

```powershell
$env:PYTHONPATH = "src"

python -m vidmaker validate projects\0\project.yaml

python -m vidmaker render projects\0\project.yaml `
  --output output\project-0.mp4 `
  --work-dir work\project-0
```

To preview one scene without encoding a video:

```powershell
python -m vidmaker preview projects\0\project.yaml `
  --scene 1 `
  --output work\project-0\preview_scene_1.png
```

## Generated files and cleanup

- Keep project YAML files, source images, music, and attribution files.
- `output/` contains final MP4 files.
- `work/` contains frames, manifests, and generated voiceovers.
- It is safe to delete a project's `work/` directory after checking its MP4.
- Do not delete `src/vidmaker/`, project YAML files, source images, or music.

## CLI commands

```text
validate   Check YAML, files, FFmpeg, and voiceover availability
preview    Render one scene to a PNG
render     Render scene frames and encode the final MP4
```
