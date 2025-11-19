#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for S3 upload functionality.
Renders a simple Manim video and uploads it to S3, then prints the resulting URL.
"""

import os
import sys
import tempfile
import shutil
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
load_dotenv()

# Add api directory to path to import the upload function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from routes.video_rendering import upload_to_s3


def create_manim_video():
    """Create a simple Manim video for testing."""
    print("\nRendering Manim test video...")
    
    # Create a temporary directory for the scene file
    temp_dir = tempfile.mkdtemp()
    scene_file = os.path.join(temp_dir, "test_scene.py")
    
    # Simple Manim scene code
    scene_code = """from manim import *

class TestScene(Scene):
    def construct(self):
        # Create a blue circle
        circle = Circle(radius=1.5, color=BLUE)
        circle.set_fill(BLUE, opacity=0.8)
        
        # Create text
        text = Text("S3 Upload Test", font_size=48)
        text.next_to(circle, DOWN)
        
        # Animate
        self.play(Create(circle))
        self.play(Write(text))
        self.wait(1)
"""
    
    # Write scene file
    with open(scene_file, 'w') as f:
        f.write(scene_code)
    
    print(f"[OK] Created scene file: {scene_file}")
    
    # Render the video
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    import subprocess
    
    command = [
        sys.executable,  # Use current Python interpreter
        "-m", "manim",
        scene_file,
        "TestScene",
        "--format=mp4",
        "--media_dir", output_dir,
        "--custom_folders",
        "-ql",  # Low quality for faster rendering
    ]
    
    print(f"[OK] Running: {' '.join(command)}")
    print("  (This may take 10-20 seconds...)")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        print("[OK] Manim rendering completed")
        
        # Find the output video file
        video_paths = [
            os.path.join(output_dir, "videos", "TestScene", "480p15", "TestScene.mp4"),
            os.path.join(output_dir, "TestScene.mp4"),
        ]
        
        for video_path in video_paths:
            if os.path.exists(video_path):
                # Copy to a known location
                test_video_path = "test_video.mp4"
                shutil.copy2(video_path, test_video_path)
                file_size = os.path.getsize(test_video_path)
                print(f"[OK] Video saved: {test_video_path} ({file_size:,} bytes)")
                
                # Clean up temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                return test_video_path
        
        raise FileNotFoundError("Could not find rendered video file")
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Manim rendering failed:")
        print(f"  STDOUT: {e.stdout}")
        print(f"  STDERR: {e.stderr}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as e:
        print(f"[ERROR] Error during video creation: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def test_s3_upload():
    """Test S3 upload and return the URL."""
    print("\n" + "="*60)
    print("S3 UPLOAD TEST")
    print("="*60 + "\n")
    
    # Check required environment variables
    required_vars = [
        'S3_ACCESS_KEY_ID',
        'S3_SECRET_ACCESS_KEY',
        'S3_BUCKET'
    ]
    
    print("Checking environment variables...")
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"[X] {var}: NOT SET")
        else:
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var:
                masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                print(f"[OK] {var}: {masked_value}")
            else:
                print(f"[OK] {var}: {value}")
    
    # Print optional variables
    optional_vars = ['S3_ENDPOINT', 'S3_REGION', 'S3_PUBLIC_URL_BASE', 'S3_FORCE_PATH_STYLE']
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var}: {value}")
    
    if missing_vars:
        print(f"\n[ERROR] Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        return None
    
    print("\n" + "-"*60)
    
    # Create test file
    print("\nStep 1: Creating Manim video")
    print("-"*60)
    test_file = create_manim_video()
    
    try:
        # Generate a unique filename for the test
        import uuid
        video_storage_name = f"test-video-{str(uuid.uuid4())}"
        
        print("\nStep 2: Uploading to S3")
        print("-"*60)
        print(f"Uploading as: {video_storage_name}.mp4")
        print("Please wait...")
        
        # Upload to S3
        video_url = upload_to_s3(test_file, video_storage_name)
        
        print("\n" + "="*60)
        print("[SUCCESS]")
        print("="*60)
        print(f"\nVideo URL: {video_url}")
        print("\nYou can test the URL in your browser or with:")
        print(f"curl -I {video_url}")
        print("\n" + "="*60 + "\n")
        
        return video_url
        
    except Exception as e:
        print("\n" + "="*60)
        print("[FAILED] UPLOAD FAILED")
        print("="*60)
        print(f"\nError: {str(e)}")
        print("\nPlease check:")
        print("1. S3 credentials are correct")
        print("2. Bucket exists and is accessible")
        print("3. Network connection is working")
        print("4. Bucket has proper permissions for public uploads")
        print("\n" + "="*60 + "\n")
        return None
        
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"[OK] Cleaned up local test file: {test_file}\n")


if __name__ == "__main__":
    result = test_s3_upload()
    sys.exit(0 if result else 1)