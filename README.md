# Manim API

Flask REST API for generating Manim animations.

## Installation

```bash
git clone <repository-url>
cd manim-api
pip install -r requirements.txt
cp .env.example .env
python run.py
```

API runs on `http://localhost:8080`

## Configuration

Required environment variables:

```env
USE_LOCAL_STORAGE=false  # true for local storage
AZURE_STORAGE_CONNECTION_STRING=your_string  # required when USE_LOCAL_STORAGE=false
PORT=8080  # optional
```

## Usage

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
{ "video_url": "https://manimapi.blob.core.windows.net/manimcontainer/video-1a4fe592-2232-4167-b4d2-15d4fc249c6d.mp4", "processingTime": 4.466716766357422 }
```

Parameters:
- `code`: Manim scene code (required)
- `file_class`: Scene class name (required)
- `rendering_engine`: "cairo", "opengl" (optional)
- `stream`: true/false for progress streaming (optional)

## Docker

```bash
docker build -t manim-api .
docker run -p 8080:8080 -e AZURE_STORAGE_CONNECTION_STRING=your_string manim-api
```
