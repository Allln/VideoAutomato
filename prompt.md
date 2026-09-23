# Video project YAML generation prompt

You are generating a YAML project file for a local Python slide-video renderer.

## Source material
list of images = [1.png, 2.png]
```text
SOURCE:
https://en.wikipedia.org/wiki/Birch_and_Swinnerton-Dyer_conjecture
```
directory_name = 1

## Task

Create an educational YouTube video script from the source material. Use original wording and do not claim that an unresolved problem has been solved. Keep factual claims faithful to the source.

Return only valid YAML. Do not wrap the YAML in Markdown fences. Do not add explanations before or after it.

## Required YAML structure

Use exactly this top-level structure as a yaml template and return me ready to use .yaml file to download:

```yaml
title: Title placeholder

video:
  width: 1920
  height: 1080
  fps: 30
  output: ../../output/directory_name.mp4
  background_color: "#07111F"

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

scenes:
  - id: scene-01
    title: Scene title
    body: >
      Scene text.
    image: images/1.png
    duration: auto
    voiceover: >
      Scene narration.

  - id: scene-02
    title: Scene title
    body: >
      Scene text.
    image: images/2.png
    duration: auto
    voiceover: >
      Scene narration.
```

## Rules

1. Keep `video.width` exactly `1920`.
2. Keep `video.height` exactly `1080`.
3. Keep `video.fps` exactly `30`.
4. Keep the `audio.tts` and `audio.music` sections.
5. Use `../../src/assets/music/1.mp3` for the shared background music.
6. Keep music volume between `0.08` and `0.15`.
7. Keep `pause_between_scenes` at `1.0` unless a different pause is intentionally wanted.
8. Use one scene per supplied image.
9. Image filenames must be numbered and match the project folder, for example:
   - `images/01_intro.png`
   - `images/02_main-idea.png`
   - `images/03_conclusion.png`
10. Use `duration: auto` when the scene should be timed from its generated voiceover.
11. Use a positive numeric duration only when a fixed scene length is intentional.
12. Make each `voiceover` fit comfortably inside its scene; automatic timing adds padding.
13. Use concise screen text; put fuller explanations in `voiceover`.
14. Use unique lowercase-hyphenated scene IDs.
15. Do not invent image filenames that were not supplied.
16. Do not add unsupported YAML keys.
17. Escape colons, quotation marks, and special YAML characters correctly.
18. Include an opening scene and a conclusion scene when the source supports them.
19. Prefer 4 to 10 scenes for a short explainer.
20. State uncertainty clearly and distinguish established facts from conjecture.
