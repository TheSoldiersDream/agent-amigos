# MV Motion Pipeline: ComfyUI Setup

The Music Video generator now produces **continuous motion** using a **local ComfyUI workflow** (AnimateDiff / Deforum / similar). The backend submits a workflow JSON to ComfyUI, waits for completion, downloads the rendered MP4, interpolates (optional), then assembles a final **1080p H.264 MP4** with the uploaded audio.

## 1) Start ComfyUI locally

- Run ComfyUI on the same machine as Agent Amigos.
- Default URL expected by the backend is:
  - `http://127.0.0.1:8188`

If yours differs, set `COMFYUI_URL` in `.env`.

## 2) Create / export a workflow that outputs an MP4

In ComfyUI:

1. Build (or import) an **AnimateDiff / Deforum** workflow that generates a short animated clip.
2. Ensure the workflow ends with a node that produces a **video file** output (MP4 preferred).
3. Use **Workflow → Save (API Format)** (or export JSON) to save it as a `.json` file.

Set its path in `.env`:

- `COMFYUI_WORKFLOW_PATH=C:\\...\\animatediff_text2video.json`

## 3) Add placeholders (recommended)

This repo’s ComfyUI client is workflow-agnostic. It works best if you embed placeholders in your workflow JSON.

Supported placeholders:

- `{{PROMPT}}`
- `{{NEG_PROMPT}}`
- `{{WIDTH}}`, `{{HEIGHT}}`
- `{{FRAMES}}`, `{{FPS}}`
- `{{SEED}}`
- `{{STEPS}}`, `{{CFG}}`
- `{{SAMPLER}}`, `{{SCHEDULER}}`

You can put these placeholders in fields like:

- text prompt strings
- seed
- width/height
- frame count / fps

The backend will replace placeholders per scene automatically.

## 4) Interpolation

The pipeline supports interpolation to 24–30fps.

- Default: `MV_INTERPOLATION_ENGINE=ffmpeg-minterpolate`

  - This uses optical-flow interpolation built into ffmpeg.

- Preferred (if you have it): RIFE
  - Set `MV_INTERPOLATION_ENGINE=rife`
  - Set `RIFE_EXE=C:\\path\\to\\rife.exe`

## 5) Notes

- Long songs can take a long time because we generate many short animated clips.
- To speed up, increase `MV_BASE_FPS` only if your workflow/model can handle it.
- The MV job stages shown in the GUI:
  - `analyzing → planning → animating → interpolating → assembling → done`
