<p align="center">
  <samp>manim-renderer-api</samp>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/manim-v0.18.0-blue?style=flat-square" alt="Manim Version">
  <img src="https://img.shields.io/badge/modal-v0.64.117-green?style=flat-square" alt="Modal Version">
  <img src="https://img.shields.io/badge/rendering-serverless-orange?style=flat-square" alt="Infrastructure">
  <img src="https://img.shields.io/badge/storage-S3%20%2F%20Local-blue?style=flat-square" alt="Storage">
  <img src="https://img.shields.io/badge/license-Apache--2.0-purple?style=flat-square" alt="License">
</p>

# manim-renderer-api

<p align="center">
  <b>manim-renderer-api is a lightweight Flask REST API that provides serverless, auto-scaling Manim video rendering via Modal.com.</b>
  <br>
  Compile mathematical animations on-demand with zero local dependencies, real-time progress streaming, and instant S3-compatible asset uploads.
</p>

---

### Hero Demo

```bash
# Request a serverless math animation render
$ curl -X POST http://localhost:8080/v1/video/rendering \
    -H "Content-Type: application/json" \
    -d '{
      "code": "class CircleScene(Scene):\n    def construct(self):\n        self.play(Create(Circle()))",
      "file_class": "CircleScene",
      "stream": true
    }'

# Streamed real-time progress response (Server-Sent Events)
── [manim-renderer-api] Render Progress ───────────────────
✓ Initializing serverless container... (1.2s)
✓ Compiling scene: CircleScene...
[Animation 0] ████████████████████ 100%
✓ Uploading compiled video to S3... (0.4s)
✓ Processing complete in 4.46s

{
  "video_url": "https://storage.s3.com/video-5a95d382.mp4",
  "processingTime": 4.46
}
───────────────────────────────────────────────────────────
```

<br>

## Why Serverless over Local Rendering?

Traditional Manim workflows require heavy system packages (LaTeX, FFmpeg, Cairo) making cloud deployments slow, expensive, and fragile.

| Metric | Local Rendering | Serverless Rendering (Modal) |
| :--- | :--- | :--- |
| **Setup Time** | ~1-2 Hours | **<1 Minute** |
| **Storage Size** | ~20GB+ (LaTeX, FFmpeg, etc.) | **0MB footprint** |
| **Concurrency** | Throttled (1-2 renders) | **Auto-scaling (Infinite)** |
| **Cost** | Dedicated hardware costs | **Pay-as-you-go (~$0.01/render)** |
| **Resiliency** | Single-point of failure | **Auto-fallback to local** |

<br>

## Minimum Viable Knowledge

✅ **Deploy Runner First**: Run `modal deploy api/modal_manim.py` once to build and deploy the container to Modal.
✅ **Seamless Fallback**: If `USE_MODAL=false` or Modal is unavailable, it automatically uses your local Manim.
✅ **Stream for Progress**: Set `"stream": true` to track rendering percentage frame-by-frame via SSE.
✅ **Flexible Storage**: Toggle `USE_LOCAL_STORAGE=true` for local outputs, or configure S3/Spaces.

<br>

## Quick Start

### 1. Installation

```bash
git clone https://github.com/PastiLulus/manim-renderer-api.git
cd manim-renderer-api
pip install -r requirements.txt
cp .env.example .env
```

### 2. Deploy to Modal & Run

```bash
# 1. Sign up/authenticate with Modal
modal setup

# 2. Deploy serverless container to the cloud
modal deploy api/modal_manim.py

# 3. Spin up the Flask API
python run.py
```

<br>

## Architecture

```text
               HTTP POST /video/rendering
  ┌────────┐ ──────────────────────────────► ┌───────────┐
  │ Client │                                 │ Flask API │
  └────────┘ ◄────────────────────────────── └───────────┘
      ▲        JSON Response (Video URL)          │
      │                                           │ compile_manim_animation.remote()
      │                                           ▼
  ┌────────┐          Video Bytes            ┌───────────┐
  │ S3 CDN │ ◄────────────────────────────── │ Modal.com │
  └────────┘                                 └───────────┘
```

<br>

## API Reference

### Health Check

```http
GET /v1/health
```

### Video Rendering

```http
POST /v1/video/rendering
Content-Type: application/json

{
  "code": "class MyScene(Scene):\n    def construct(self):\n        self.play(Create(Circle()))",
  "file_class": "MyScene",
  "rendering_engine": "cairo",
  "stream": true
}
```

---

<p align="center">
  <a href="MODAL_DEPLOYMENT.md">Deployment Guide</a> · 
  <a href="INTEGRATION_SUMMARY.md">Integration Details</a> · 
  <a href="https://github.com/PastiLulus/manim-renderer-api/issues">Report Issue</a>
</p>

<p align="center">
  <sub>Apache 2.0 License</sub>
</p>
