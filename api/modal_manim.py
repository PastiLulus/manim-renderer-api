"""
Modal app for compiling Manim animations in a containerized environment.

This solves the production deployment issue by running Manim compilation
in Modal's serverless containers with pre-installed dependencies.
"""
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import modal

# Define the container image with all Manim dependencies
manim_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        # LaTeX dependencies for mathematical formulas
        "texlive-latex-extra",
        "texlive-fonts-extra",
        "texlive-latex-recommended",
        "texlive-science",          # Additional math packages
        "cm-super",                 # Better font rendering
        # Media processing
        "ffmpeg",                   # Video processing
        "libcairo2-dev",           # Cairo graphics library
        "libpango1.0-dev",         # Pango text rendering
        "pkg-config",              # Build configuration
        # System utilities
        "git",                     # Version control
        "curl",                    # HTTP client
    )
    .pip_install(
        "manim==0.18.0",           # Match current project version (includes compatible Pillow)
        "numpy>=1.24.0",           # Mathematical operations
        "scipy>=1.10.0",           # Scientific computing
        "matplotlib>=3.7.0",       # Additional plotting capabilities
        "manim-physics==0.4.0",    # Physics support
    )
    .env({
        "MANIM_QUALITY": "low_quality",     # Default to faster rendering
        "MANIMGL_LOG_LEVEL": "WARNING",     # Reduce log verbosity
    })
)

# Create the Modal app
app = modal.App("manim-renderer-api", image=manim_image)

@app.function(
    timeout=300,        # 5 minute timeout for complex animations
    cpu=2.0,           # Dedicated CPU cores for faster rendering
    memory=4096,       # 4GB RAM for complex scenes
    retries=2,         # Retry on failure
)
def compile_manim_animation(
    python_code: str,
    class_name: str,
    rendering_engine: str = "cairo",
    quality: str = "medium_quality"
) -> dict:
    """
    Compile a Manim animation from Python code.

    Args:
        python_code: The complete Python code containing the Manim scene
        class_name: Name of the Scene class to render
        rendering_engine: Rendering engine ("cairo" or "opengl")
        quality: Manim quality setting (low_quality, medium_quality, high_quality)

    Returns:
        dict: {
            "success": bool,
            "video_bytes": bytes (if successful),
            "error": str (if failed),
            "logs": str,
            "duration": float (seconds),
            "progress_updates": list (progress information)
        }
    """
    import time
    import re
    start_time = time.time()
    progress_updates = []

    try:
        print(f"[MODAL-MANIM] Starting compilation for {class_name}")

        # Create temporary directory for this compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write Python code to file
            python_file = temp_path / "animation.py"
            with open(python_file, "w") as f:
                f.write(python_code)

            print(f"[MODAL-MANIM] Python file written: {python_file}")

            # Determine quality flag
            quality_flag = "-ql"  # Default to low quality
            if quality == "medium_quality":
                quality_flag = "-qm"
            elif quality == "high_quality":
                quality_flag = "-qh"

            # Build command
            cmd = [
                "manim",
                str(python_file),
                class_name,
                quality_flag,
                "--format=mp4",
                "--disable_caching",
                "--media_dir", str(temp_path),
                "--custom_folders",
            ]

            # Add renderer flag if opengl
            if rendering_engine == "opengl":
                cmd.insert(4, "--renderer=opengl")

            print(f"[MODAL-MANIM] Executing: {' '.join(cmd)}")

            # Run manim command with progress tracking
            process = subprocess.Popen(
                cmd,
                cwd=temp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Track progress
            current_animation = -1
            current_percentage = 0
            stdout_lines = []
            stderr_lines = []

            while True:
                stdout_line = process.stdout.readline()
                stderr_line = process.stderr.readline()

                if stdout_line == "" and stderr_line == "" and process.poll() is not None:
                    break

                if stdout_line:
                    stdout_lines.append(stdout_line.strip())
                    print(f"[MODAL-MANIM] STDOUT: {stdout_line.strip()}")

                if stderr_line:
                    stderr_lines.append(stderr_line.strip())
                    print(f"[MODAL-MANIM] STDERR: {stderr_line.strip()}")

                    # Track animation progress
                    animation_match = re.search(r"Animation (\d+):", stderr_line)
                    if animation_match:
                        new_animation = int(animation_match.group(1))
                        if new_animation != current_animation:
                            current_animation = new_animation
                            current_percentage = 0
                            progress_updates.append({
                                "animationIndex": current_animation,
                                "percentage": 0
                            })

                    # Track percentage
                    percentage_match = re.search(r"(\d+)%", stderr_line)
                    if percentage_match:
                        new_percentage = int(percentage_match.group(1))
                        if new_percentage != current_percentage:
                            current_percentage = new_percentage
                            progress_updates.append({
                                "animationIndex": current_animation,
                                "percentage": current_percentage
                            })

            # Wait for process to complete
            process.wait()

            # Collect all output
            stdout_output = "\n".join(stdout_lines)
            stderr_output = "\n".join(stderr_lines)
            all_logs = f"STDOUT:\n{stdout_output}\n\nSTDERR:\n{stderr_output}"

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"Manim compilation failed with return code {process.returncode}",
                    "logs": all_logs,
                    "duration": time.time() - start_time,
                    "progress_updates": progress_updates
                }

            # Find the generated video file
            # Try multiple possible paths
            video_files = list(temp_path.glob(f"**/{class_name}.mp4"))
            
            if not video_files:
                # Try output.mp4 pattern
                video_files = list(temp_path.glob("**/output.mp4"))

            if not video_files:
                # List all files for debugging
                all_files = list(temp_path.rglob("*"))
                file_list = "\n".join(str(f) for f in all_files if f.is_file())

                return {
                    "success": False,
                    "error": f"Video file not found. Files created:\n{file_list}",
                    "logs": all_logs,
                    "duration": time.time() - start_time,
                    "progress_updates": progress_updates
                }

            video_file = video_files[0]
            print(f"[MODAL-MANIM] Video found: {video_file}")

            # Read video file as bytes
            with open(video_file, "rb") as f:
                video_bytes = f.read()

            duration = time.time() - start_time
            print(f"[MODAL-MANIM] Compilation completed in {duration:.2f}s")

            return {
                "success": True,
                "video_bytes": video_bytes,
                "logs": all_logs,
                "duration": duration,
                "progress_updates": progress_updates
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Compilation timed out",
            "logs": "Manim compilation exceeded timeout limit",
            "duration": time.time() - start_time,
            "progress_updates": progress_updates
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "logs": f"Exception occurred: {str(e)}\n{traceback.format_exc()}",
            "duration": time.time() - start_time,
            "progress_updates": progress_updates
        }

@app.function()
def health_check() -> dict:
    """Health check function to verify the Modal app is working."""
    try:
        # Test basic imports
        import manim
        import numpy
        import PIL

        # Check FFmpeg availability
        ffmpeg_available = False
        ffmpeg_version = "not found"
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                ffmpeg_available = True
                ffmpeg_version = result.stdout.split('\n')[0]
        except Exception:
            pass

        return {
            "status": "healthy",
            "manim_version": manim.__version__,
            "numpy_version": numpy.__version__,
            "ffmpeg_available": ffmpeg_available,
            "ffmpeg_version": ffmpeg_version,
            "timestamp": str(__import__('datetime').datetime.now())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(__import__('datetime').datetime.now())
        }

# For local testing and deployment
if __name__ == "__main__":
    # Test with a simple animation
    test_code = '''from manim import *
from math import *

class TestAnimation(Scene):
    def construct(self):
        circle = Circle()
        circle.set_fill(PINK, opacity=0.5)
        self.play(Create(circle))
        self.wait()
'''

    print("Testing Modal Manim compilation...")
    with modal.enable_output():
        result = compile_manim_animation.remote(test_code, "TestAnimation")

    if result["success"]:
        print(f"✅ Success! Video size: {len(result['video_bytes'])} bytes")
        print(f"Duration: {result['duration']:.2f}s")
        print(f"Progress updates: {len(result['progress_updates'])}")
    else:
        print(f"❌ Failed: {result['error']}")
        print(f"Logs: {result['logs']}")