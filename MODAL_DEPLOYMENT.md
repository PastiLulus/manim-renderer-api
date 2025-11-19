# Modal.com Integration Guide

This project now uses [Modal.com](https://modal.com) for serverless Manim rendering. This solves production deployment issues by running Manim compilation in Modal's containerized infrastructure with all dependencies pre-installed.

## Why Modal?

- **No Local Dependencies**: No need to install LaTeX, FFmpeg, or Manim on your server
- **Scalable**: Automatically scales to handle multiple rendering jobs
- **Fast**: Dedicated resources for each rendering job
- **Reliable**: Pre-built containers with all dependencies
- **Cost-Effective**: Pay only for compute time used

## Prerequisites

1. **Modal Account**: Sign up at [modal.com](https://modal.com)
2. **Modal Tokens**: Get your authentication tokens from [Modal Settings](https://modal.com/settings/tokens)
   - `MODAL_TOKEN_ID` (starts with `ak-`)
   - `MODAL_TOKEN_SECRET` (starts with `as-`)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `modal==0.64.117` along with other dependencies.

### 2. Authenticate with Modal

#### Option A: Using Environment Variables (Recommended for Production)

Add to your `.env` file:

```env
MODAL_TOKEN_ID=ak-xxxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxx
```

#### Option B: Using Modal CLI (For Development)

```bash
modal token set --token-id <your-token-id> --token-secret <your-token-secret>
```

Or use the interactive setup:

```bash
modal setup
```

**Note**: Environment variables take precedence over CLI authentication.

### 3. Deploy Modal App

Deploy the Modal function to Modal's cloud:

```bash
modal deploy api/modal_manim.py
```

This will:
- Build the container image with all Manim dependencies
- Deploy the `compile_manim_animation` function
- Make it available for remote calls

### 4. Configure Environment Variables

Update your `.env` file:

```env
# Enable Modal rendering (set to false to use local rendering)
USE_MODAL=true

# Modal Authentication (required when USE_MODAL=true)
MODAL_TOKEN_ID=ak-xxxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxx

# Storage configuration (required)
USE_LOCAL_STORAGE=false
S3_ENDPOINT=https://sgp1.digitaloceanspaces.com
S3_REGION=sgp1
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET=your-bucket-name
```

### 5. Start Your API Server

```bash
python run.py
```

Or with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8080 run:app
```

## How It Works

1. **Client Request**: Your API receives a Manim rendering request
2. **Modal Invocation**: The API calls `compile_manim_animation.remote()` on Modal
3. **Serverless Rendering**: Modal spins up a container with all dependencies and renders the animation
4. **Video Return**: Modal returns the compiled video as bytes
5. **Storage Upload**: Your API uploads the video to S3/local storage
6. **Response**: Client receives the video URL

## Architecture

```
┌─────────────┐      HTTP Request       ┌──────────────┐
│   Client    │ ──────────────────────> │  Flask API   │
└─────────────┘                         └──────────────┘
                                              │
                                              │ modal.remote()
                                              ▼
                                        ┌──────────────┐
                                        │ Modal.com    │
                                        │ (Serverless) │
                                        └──────────────┘
                                              │
                                              │ Video bytes
                                              ▼
                                        ┌──────────────┐
                                        │ S3 Storage   │
                                        └──────────────┘
                                              │
                                              │ Video URL
                                              ▼
                                        ┌──────────────┐
                                        │   Client     │
                                        └──────────────┘
```

## Testing

### Test the Modal Function Directly

```bash
python api/modal_manim.py
```

This will run a test animation and verify Modal is working correctly.

### Test via API

```bash
curl -X POST http://localhost:8080/v1/video/rendering \
  -H "Content-Type: application/json" \
  -d '{
    "code": "class TestScene(Scene):\n    def construct(self):\n        circle = Circle()\n        self.play(Create(circle))",
    "file_class": "TestScene"
  }'
```

### Test with Streaming Progress

```bash
curl -X POST http://localhost:8080/v1/video/rendering \
  -H "Content-Type: application/json" \
  -d '{
    "code": "class TestScene(Scene):\n    def construct(self):\n        circle = Circle()\n        self.play(Create(circle))",
    "file_class": "TestScene",
    "stream": true
  }'
```

## Fallback to Local Rendering

If Modal is unavailable or you set `USE_MODAL=false`, the API will automatically fall back to local rendering using subprocess. This requires:

- Manim installed locally
- LaTeX installed
- FFmpeg installed

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MODAL` | `true` | Enable Modal rendering |
| `MODAL_TOKEN_ID` | - | Modal authentication token ID (starts with `ak-`) |
| `MODAL_TOKEN_SECRET` | - | Modal authentication token secret (starts with `as-`) |
| `USE_LOCAL_STORAGE` | `false` | Use local file storage instead of S3 |

### Modal Function Parameters

The [`compile_manim_animation`](api/modal_manim.py:54) function accepts:

- `python_code` (str): Complete Manim scene code
- `class_name` (str): Name of the Scene class to render
- `rendering_engine` (str): "cairo" or "opengl" (default: "cairo")
- `quality` (str): "low_quality", "medium_quality", or "high_quality" (default: "medium_quality")

### Modal Container Configuration

The Modal container includes:

- Python 3.11
- Manim 0.18.0 (matches project version)
- LaTeX (full installation)
- FFmpeg
- manim-physics
- All required dependencies

Resource allocation:
- CPU: 2.0 cores
- Memory: 4GB
- Timeout: 5 minutes
- Retries: 2 attempts

## Monitoring

### Check Modal Logs

```bash
modal app logs manim-renderer-api
```

### View Modal Dashboard

Visit [modal.com/apps](https://modal.com/apps) to see:
- Function invocations
- Execution time
- Resource usage
- Costs

### API Logs

The API logs will show:
- `[MODAL]` prefix for Modal-related operations
- `[INFO]` when Modal is enabled/disabled
- `[WARNING]` if Modal import fails

## Troubleshooting

### Modal Import Fails

**Symptom**: `[WARNING] Modal import failed`

**Solution**:
1. Verify Modal is installed: `pip install modal`
2. Check authentication: `modal token set`
3. Verify deployment: `modal deploy api/modal_manim.py`

### Rendering Times Out

**Symptom**: "Compilation timed out"

**Solution**:
- Simplify your animation
- Increase timeout in [`modal_manim.py`](api/modal_manim.py:49) (line 49: `timeout=300`)
- Use lower quality setting

### Video Not Found

**Symptom**: "Video file not found"

**Solution**:
- Check that the class name matches exactly
- Verify the code syntax is correct
- Check Modal logs for errors

### S3 Upload Fails

**Symptom**: "Failed to upload to S3"

**Solution**:
- Verify S3 credentials in `.env`
- Check bucket permissions
- Ensure bucket exists

## Cost Optimization

Modal charges based on:
- CPU time used
- Memory allocated
- Function invocations

To optimize costs:

1. **Use Lower Quality**: Set `quality="low_quality"` for testing
2. **Cache Results**: Cache rendered videos to avoid re-rendering
3. **Set Appropriate Timeouts**: Don't over-allocate time
4. **Monitor Usage**: Check Modal dashboard regularly

## Security

- Modal functions run in isolated containers
- API secrets are not exposed to Modal
- Video bytes are transmitted securely
- S3 uploads use authenticated requests

## Support

- **Modal Issues**: [modal.com/docs](https://modal.com/docs)
- **Manim Issues**: [docs.manim.community](https://docs.manim.community)
- **API Issues**: Check Flask logs and error messages

## Advanced Usage

### Custom Quality Settings

Modify [`modal_manim.py`](api/modal_manim.py:185) line 185 to accept quality parameter from API:

```python
quality = request.json.get("quality", "medium_quality")
result = compile_manim_animation.remote(
    python_code=modified_code,
    class_name=file_class,
    rendering_engine=rendering_engine or "cairo",
    quality=quality
)
```

### Multiple Modal Apps

You can deploy multiple versions:

```bash
# Production
modal deploy api/modal_manim.py

# Staging
modal deploy api/modal_manim.py --env staging
```

### Health Check

The Modal app includes a health check function:

```python
from api.modal_manim import health_check
result = health_check.remote()
print(result)
```

## Migration Guide

### From Local Rendering

1. Deploy Modal app
2. Set `USE_MODAL=true`
3. Test with simple animation
4. Monitor logs for issues
5. Gradually migrate production traffic

### Rollback Plan

If issues occur:
1. Set `USE_MODAL=false` in `.env`
2. Restart API server
3. System falls back to local rendering
4. Investigate Modal issues offline

## Performance Comparison

| Metric | Local | Modal |
|--------|-------|-------|
| Setup Time | Hours (install deps) | Minutes (deploy) |
| Cold Start | 0ms | ~2-5s |
| Warm Start | 0ms | ~500ms |
| Rendering | Depends on hardware | Consistent (2 CPU, 4GB) |
| Scalability | Limited by hardware | Auto-scales |
| Maintenance | High (OS updates, deps) | Low (managed) |

## Updates and Maintenance

### Updating Manim Version

1. Update in [`modal_manim.py`](api/modal_manim.py:33) line 33
2. Redeploy: `modal deploy api/modal_manim.py`
3. Test thoroughly

### Updating Modal

```bash
pip install --upgrade modal
modal deploy api/modal_manim.py
```

## Conclusion

Modal integration provides a robust, scalable solution for Manim rendering without the complexity of managing dependencies and infrastructure. The automatic fallback ensures your API remains operational even if Modal is unavailable.