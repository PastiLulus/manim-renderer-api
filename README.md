# Manim API

Flask REST API for generating Manim animations using Modal.com for serverless rendering.

## Features

- 🚀 **Serverless Rendering**: Uses [Modal.com](https://modal.com) for scalable, containerized Manim rendering
- 📦 **No Local Dependencies**: No need to install LaTeX, FFmpeg, or Manim locally
- 🔄 **Automatic Fallback**: Falls back to local rendering if Modal is unavailable
- ☁️ **S3 Storage**: Supports S3-compatible storage for video files
- 📊 **Progress Streaming**: Real-time rendering progress updates

## Installation

```bash
git clone <repository-url>
cd manim-api
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Modal and S3 credentials
```

## Quick Setup

### 1. Install Modal and Authenticate

```bash
pip install modal
modal setup  # Follow the prompts to authenticate
```

Or set tokens directly:
```bash
modal token set --token-id YOUR_TOKEN_ID --token-secret YOUR_TOKEN_SECRET
```

Get your tokens from https://modal.com/settings/tokens

### 2. **CRITICAL: Deploy to Modal** ⚠️

**This step is REQUIRED before running the API!**

```bash
modal deploy api/modal_manim.py
```

**First deployment takes 5-10 minutes** (installs LaTeX, FFmpeg, Manim, etc.)
Subsequent deployments are instant.

You should see:
```
✓ Created objects.
├── 🔨 Created function compile_manim_animation
└── 🔨 Created function health_check
```

### 3. Start the API

```bash
python run.py
```

API runs on `http://localhost:8080`

**Note**: If Modal deployment hasn't completed, the API will return "Function has not been hydrated" errors.

See [MODAL_DEPLOYMENT.md](MODAL_DEPLOYMENT.md) for detailed setup instructions.

## Configuration

Required environment variables:

```env
# Modal Configuration (Serverless Rendering)
USE_MODAL=true  # Set to false to use local rendering
MODAL_TOKEN_ID=ak-xxxxxxxxxxxxx  # Get from https://modal.com/settings/tokens
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxx

# Storage Configuration
USE_LOCAL_STORAGE=false  # true for local storage

# S3 Configuration (required when USE_LOCAL_STORAGE=false)
S3_ENDPOINT=https://sgp1.digitaloceanspaces.com  # S3-compatible endpoint
S3_REGION=sgp1  # S3 region
S3_ACCESS_KEY_ID=your_access_key_id
S3_SECRET_ACCESS_KEY=your_secret_access_key
S3_BUCKET=your-bucket-name
S3_PUBLIC_URL_BASE=  # Optional: Custom CDN URL
S3_FORCE_PATH_STYLE=true  # true for most S3-compatible services

# Server Configuration
PORT=8080  # optional
```

See [`.env.example`](.env.example) for all configuration options.

## Usage

### Health Check

First, verify your Modal configuration is correct:

```bash
curl http://localhost:8080/v1/health
```

Response:
```json
{
  "status": "healthy",
  "modal_enabled": true,
  "modal_available": true,
  "modal_tokens": "✅ Configured",
  "modal_health": {
    "status": "healthy",
    "manim_version": "0.18.0",
    "ffmpeg_available": true
  },
  "storage": "s3"
}
```

### Generate Videos

Generate video from Manim code:

```bash
curl -X POST http://localhost:8080/v1/video/rendering \
  -H "Content-Type: application/json" \
  -d '{
    "code": "class MyScene(Scene):\n    def construct(self):\n        self.play(Create(Circle()))",
    "file_class": "MyScene"
  }'
```

With streaming progress:

```bash
curl -X POST http://127.0.0.1:8080/v1/video/rendering \
  -H "Content-Type: application/json" \
  -d '{
    "code": "class BlueCircleScene(Scene):\n    def construct(self):\n        circle = Circle(radius=2, color=BLUE)\n        circle.set_fill(BLUE, opacity=0.8)\n        self.add(circle)\n        self.play(Create(circle))\n        self.wait(2)",
    "file_name": "blue_circle_scene.py",
    "file_class": "BlueCircleScene",
    "stream": true
  }'
```

Response:
```json
{"animationIndex": 0, "percentage": 0}
{"animationIndex": 0, "percentage": 2}
{"animationIndex": 0, "percentage": 18}
{"animationIndex": 0, "percentage": 37}
{"animationIndex": 0, "percentage": 67}
{"animationIndex": 0, "percentage": 98}
{ "video_url": "https://sgp1.digitaloceanspaces.com/your-bucket/video-1a4fe592-2232-4167-b4d2-15d4fc249c6d.mp4", "processingTime": 4.466716766357422 }
```

Parameters:
- `code`: Manim scene code (required)
- `file_class`: Scene class name (required)
- `rendering_engine`: "cairo", "opengl" (optional)
- `stream`: true/false for progress streaming (optional)

## Testing

Run the test script to verify Modal integration:

```bash
# Test the API with sample Manim scenes
python test_api.py
```

The test script will:
- Test simple circle scene (non-streaming)
- Test animated scene with streaming progress
- Test complex scene with multiple objects
- Verify video URLs are accessible

## Docker

```bash
docker build -t manim-api .
docker run -p 8080:8080 \
  -e USE_MODAL=true \
  -e MODAL_TOKEN_ID=your_modal_token_id \
  -e MODAL_TOKEN_SECRET=your_modal_token_secret \
  -e S3_ENDPOINT=https://sgp1.digitaloceanspaces.com \
  -e S3_REGION=sgp1 \
  -e S3_ACCESS_KEY_ID=your_access_key \
  -e S3_SECRET_ACCESS_KEY=your_secret_key \
  -e S3_BUCKET=your-bucket \
  manim-api
```

## Deployment

### Modal Deployment

Before running the API, deploy the Modal function:

```bash
# Deploy to Modal
modal deploy api/modal_manim.py
```

First deployment takes 5-10 minutes to build the container (installs LaTeX, FFmpeg, etc.). Subsequent deployments are instant.

### Local Development

For local testing without Modal:

```bash
# Disable Modal in .env
USE_MODAL=false

# Make sure Manim is installed locally
pip install manim

# Start the API
python run.py
```

## Storage Configuration

The API supports both local storage and S3-compatible storage:

### Local Storage
Set `USE_LOCAL_STORAGE=true` to store videos in the local filesystem under `api/public/`.

### S3-Compatible Storage
Set `USE_LOCAL_STORAGE=false` and configure S3 environment variables. Supports:
- AWS S3
- DigitalOcean Spaces
- Any S3-compatible storage service

See [`.env.example`](.env.example) for detailed configuration options.

## Troubleshooting

### Modal Issues

**"Function has not been hydrated"**
- The Modal app hasn't been deployed yet
- Run: `modal deploy api/modal_manim.py`

**Modal import fails**
- Install Modal: `pip install modal`
- Authenticate: `modal token set --token-id YOUR_ID --token-secret YOUR_SECRET`

**Slow first deployment**
- Expected - building container with LaTeX/FFmpeg (~5-10 min)
- Subsequent deployments are instant (uses cached image)

### Video Rendering Issues

**"Video file not found"**
- Check that `file_class` matches your Scene class name exactly
- Verify your Manim code syntax is correct

**Timeout errors**
- Complex animations may need more time
- Consider using `quality="low_quality"` for testing

For more help, see [`MODAL_DEPLOYMENT.md`](MODAL_DEPLOYMENT.md)
