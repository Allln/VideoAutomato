Put this video's numbered images in the images folder.

Expected files for the starter project:

01_seven_problems.png
02_clay_institute.png

Edit project.yaml, validate it, and render from the repository root:

  $env:PYTHONPATH = "src"
  python -m vidmaker validate projects\2026-09-22-millennium-prize-problems\project.yaml
  python -m vidmaker render projects\2026-09-22-millennium-prize-problems\project.yaml --work-dir work\2026-09-22-millennium-prize-problems
