from flask import Blueprint, jsonify, request, Response
import subprocess
import os
import re
import json
import traceback
import boto3
from botocore.exceptions import ClientError
import shutil
from typing import Union
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true"

video_rendering_bp = Blueprint("video_rendering", __name__)

def upload_to_s3(file_path: str, video_storage_file_name: str) -> str:
    """Upload file to S3-compatible storage and return public URL"""
    cloud_file_name = f"{video_storage_file_name}.mp4"
    
    # Get S3 configuration from environment
    s3_endpoint = os.getenv("S3_ENDPOINT")
    s3_region = os.getenv("S3_REGION")
    s3_access_key = os.getenv("S3_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    s3_bucket = os.getenv("S3_BUCKET")
    s3_public_url_base = os.getenv("S3_PUBLIC_URL_BASE")
    s3_force_path_style = os.getenv("S3_FORCE_PATH_STYLE", "true").lower() == "true"
    
    if not all([s3_access_key, s3_secret_key, s3_bucket]):
        raise ValueError("S3 configuration environment variables are not set")
    
    # Configure S3 client
    s3_config = {
        'aws_access_key_id': s3_access_key,
        'aws_secret_access_key': s3_secret_key,
        'region_name': s3_region
    }
    
    if s3_endpoint:
        s3_config['endpoint_url'] = s3_endpoint
    
    # Create S3 client with path-style configuration
    from botocore.config import Config
    boto_config = Config(s3={'addressing_style': 'path' if s3_force_path_style else 'virtual'})
    
    s3_client = boto3.client('s3', config=boto_config, **s3_config)
    
    # Upload file to S3
    try:
        with open(file_path, 'rb') as data:
            s3_client.upload_fileobj(
                data,
                s3_bucket,
                cloud_file_name,
                ExtraArgs={'ACL': 'public-read', 'ContentType': 'video/mp4'}
            )
    except ClientError as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")
    
    # Generate public URL
    if s3_public_url_base:
        # Use custom CDN/public URL if provided
        file_url = f"{s3_public_url_base.rstrip('/')}/{cloud_file_name}"
    elif s3_endpoint:
        # Use S3-compatible endpoint URL
        if s3_force_path_style:
            file_url = f"{s3_endpoint.rstrip('/')}/{s3_bucket}/{cloud_file_name}"
        else:
            # Virtual-hosted-style URL
            endpoint_without_protocol = s3_endpoint.replace('https://', '').replace('http://', '')
            file_url = f"https://{s3_bucket}.{endpoint_without_protocol}/{cloud_file_name}"
    else:
        # AWS S3 default URL format
        file_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{cloud_file_name}"
    
    return file_url


def move_to_public_folder(file_path: str, video_storage_file_name: str) -> str:
    api_dir = os.path.dirname(os.path.dirname(__file__))
    public_dir = os.path.join(api_dir, "public")
    os.makedirs(public_dir, exist_ok=True)
    
    destination_file = os.path.join(public_dir, f"{video_storage_file_name}.mp4")
    
    shutil.copy2(file_path, destination_file)
    
    return f"/public/{video_storage_file_name}.mp4"


@video_rendering_bp.route("/v1/video/rendering", methods=["POST"])
def render_video():

    code = request.json.get("code")
    rendering_engine = request.json.get("rendering_engine")

    if not code:
        return jsonify(error="No code provided"), 400
    
    file_class = request.json.get("file_class")

    stream = request.json.get("stream", False)

    video_storage_file_name = f"video-{str(uuid.uuid4())}"

    modified_code = f"""from manim import *
from math import *

{code}
"""

    file_name = f"scene_{os.urandom(2).hex()}.py"
    
    api_dir = os.path.dirname(os.path.dirname(__file__))
    public_dir = os.path.join(api_dir, "public")
    os.makedirs(public_dir, exist_ok=True)
    file_path = os.path.join(public_dir, file_name)

    with open(file_path, "w") as f:
        f.write(modified_code)

    def clean_error_output(error_lines):
        box_chars = {
            '\u256d': '',
            '\u256e': '',
            '\u2500': '',
            '\u2502': '',
            '╭': '',
            '╮': '',
            '│': '',
            '─': ''
        }
        
        cleaned_lines = []
        for line in error_lines:
            for char, replacement in box_chars.items():
                line = line.replace(char, replacement)
            line = line.rstrip()
            if line.strip():
                cleaned_lines.append(line)
        
        return cleaned_lines

    def render_video():
        video_file_path = None
        try:
            print("Starting video rendering")
            start_time = time.time()
            output_dir = os.path.join(public_dir, str(uuid.uuid4()))
            os.makedirs(output_dir, exist_ok=True)

            command_list = [
                "manim",
                file_path,
                file_class,
                f"--renderer=opengl" if rendering_engine == "opengl" else "",
                "--format=mp4",
                "--media_dir", output_dir,
                "--custom_folders",
                "--disable_caching"
            ]

            print(f"Executing command: {' '.join(command_list)}")

            process = subprocess.Popen(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            current_animation = -1
            current_percentage = 0
            error_output = []
            in_error = False

            while True:
                output = process.stdout.readline()
                error = process.stderr.readline()

                if output == "" and error == "" and process.poll() is not None:
                    break

                if output:
                    print("STDOUT:", output.strip())
                if error:
                    print("STDERR:", error.strip())
                    error_output.append(error.strip())
                    
                if "is not in the script" in error:
                    in_error = True
                    continue

                if "Traceback (most recent call last)" in error:
                    in_error = True
                    continue

                if in_error:
                    if error.strip() == "":
                        in_error = False
                        full_error = "\n".join(error_output)
                        cleaned_error_output = clean_error_output(error_output)
                        yield f'{{"error": {json.dumps("An error occurred")}, "details": {json.dumps(cleaned_error_output)}}}\n'
                        return
                    continue

                animation_match = re.search(r"Animation (\d+):", error)
                if animation_match:
                    new_animation = int(animation_match.group(1))
                    if new_animation != current_animation:
                        current_animation = new_animation
                        current_percentage = 0
                        yield f'{{"animationIndex": {current_animation}, "percentage": 0}}\n'

                percentage_match = re.search(r"(\d+)%", error)
                if percentage_match:
                    new_percentage = int(percentage_match.group(1))
                    if new_percentage != current_percentage:
                        current_percentage = new_percentage
                        yield f'{{"animationIndex": {current_animation}, "percentage": {current_percentage}}}\n'

            if process.returncode == 0:
                try:
                    video_file_path = os.path.join(output_dir, f"{file_class}.mp4")
                    
                    if not os.path.exists(video_file_path):
                        video_file_path = os.path.join(output_dir, "media", "videos", file_class, "1080p60", f"{file_class}.mp4")
                        
                        if not os.path.exists(video_file_path):
                            possible_paths = [
                                os.path.join(output_dir, "videos", file_class, "1080p60", f"{file_class}.mp4"),
                                os.path.join(output_dir, "media", "videos", file_class, "480p15", f"{file_class}.mp4"),
                            ]
                            
                            found = False
                            for path in possible_paths:
                                if os.path.exists(path):
                                    video_file_path = path
                                    found = True
                                    break
                            
                            if not found:
                                error_msg = f"Video file not found"
                                yield f'{{"error": {json.dumps(error_msg)}, "details": {json.dumps(error_output)}}}\n'
                                return

                    if USE_LOCAL_STORAGE:
                        video_url = move_to_public_folder(video_file_path, video_storage_file_name)
                    else:
                        video_url = upload_to_s3(video_file_path, video_storage_file_name)

                    print(f"Video URL: {video_url}")
                    if stream:
                        processing_time = time.time() - start_time
                        print(f"Processing time: {processing_time}")
                        yield f'{{ "video_url": "{video_url}", "processingTime": {processing_time} }}\n'
                    else:
                        processing_time = time.time() - start_time
                        print(f"Processing time: {processing_time}")
                        yield {
                            "message": "Video generation completed",
                            "video_url": video_url,
                            "processingTime": processing_time
                        }

                except Exception as e:
                    print(f"Error handling video file: {str(e)}")
                    error_msg = f"Error occurred"
                    yield f'{{"error": {json.dumps(error_msg)}, "details": {json.dumps(error_output)}}}\n'
                    return

            else:
                full_error = "\n".join(error_output)
                cleaned_error_output = clean_error_output(error_output)
                yield f'{{"error": {json.dumps("An error occurred")}, "details": {json.dumps(cleaned_error_output)}}}\n'

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            traceback.print_exc()
            error_msg = f"An error occurred"
            cleaned_error_output = clean_error_output(error_output)
            yield f'{{"error": {json.dumps(error_msg)}, "details": {json.dumps(cleaned_error_output)}}}\n'
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Removed temporary file: {file_path}")
                if video_file_path and os.path.exists(video_file_path):
                    os.remove(video_file_path)
                    print(f"Removed temporary video file: {video_file_path}")
            except Exception as e:
                print(f"Error during file cleanup: {e}")

    if stream:
        return Response(
            render_video(), content_type="text/event-stream", status=207
        )
    else:
        video_url = None
        error_details = []
        try:
            for result in render_video():
                if isinstance(result, dict):
                    if "video_url" in result:
                        video_url = result["video_url"]
                    elif "error" in result:
                        if "details" in result:
                            error_details = result["details"]
                        raise Exception(result["error"])
                elif isinstance(result, str):
                    try:
                        json_result = json.loads(result.strip())
                        if "error" in json_result:
                            if "details" in json_result:
                                error_details = json_result["details"]
                            raise Exception(json_result["error"])
                    except json.JSONDecodeError:
                        continue

            if video_url:
                return jsonify({
                    "message": "Video generation completed",
                    "video_url": video_url,
                }), 200
            else:
                return jsonify({
                    "message": "Video generation failed",
                    "error": "An error occurred",
                    "details": error_details
                }), 400
        except StopIteration:
            if video_url:
                return jsonify({
                    "message": "Video generation completed",
                    "video_url": video_url,
                }), 200
            else:
                return jsonify({
                    "message": "Video generation failed",
                    "error": "An error occurred",
                    "details": error_details
                }), 400
        except Exception as e:
            print(f"Error in non-streaming mode: {e}")
            return jsonify({
                "message": "Video generation failed",
                "error": "An error occurred",
                "details": error_details
            }), 400
