#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for deployed Manim Renderer API.
Tests the API endpoint with various Manim scenes and validates S3 upload.
"""

import requests
import json
import time
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# API Configuration
API_BASE_URL = "http://tools-manimrenderer-2p0kpi-364700-157-230-247-213.traefik.me"
API_ENDPOINT = f"{API_BASE_URL}/v1/video/rendering"


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "-"*70)
    print(f"  {title}")
    print("-"*70)


def test_simple_scene():
    """Test 1: Simple circle scene (non-streaming)."""
    print_section("TEST 1: Simple Circle Scene (Non-Streaming)")
    
    payload = {
        "code": """class SimpleCircle(Scene):
    def construct(self):
        circle = Circle(radius=2, color=BLUE)
        circle.set_fill(BLUE, opacity=0.8)
        self.play(Create(circle))
        self.wait(1)""",
        "file_class": "SimpleCircle",
        "stream": False
    }
    
    print("Sending request...")
    print(f"Code: {payload['code'][:50]}...")
    
    start_time = time.time()
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Time Taken: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if "video_url" in data:
                video_url = data["video_url"]
                print(f"\n[SUCCESS] Video URL: {video_url}")
                
                # Validate S3 URL
                if "digitaloceanspaces.com" in video_url or "s3" in video_url or "amazonaws.com" in video_url:
                    print("[OK] S3 URL format validated")
                    return True, video_url
                else:
                    print("[WARNING] URL doesn't appear to be S3")
                    return True, video_url
            else:
                print("[ERROR] No video_url in response")
                return False, None
        else:
            print(f"[ERROR] Request failed: {response.text}")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out after {time.time() - start_time:.2f}s")
        return False, None
    except Exception as e:
        print(f"[ERROR] Request failed: {str(e)}")
        return False, None


def test_streaming_scene():
    """Test 2: Streaming progress updates."""
    print_section("TEST 2: Animated Scene (Streaming)")
    
    payload = {
        "code": """class AnimatedSquare(Scene):
    def construct(self):
        square = Square(side_length=3, color=GREEN)
        square.set_fill(GREEN, opacity=0.5)
        text = Text("Streaming Test", font_size=36)
        text.next_to(square, DOWN)
        
        self.play(Create(square))
        self.play(Write(text))
        self.play(square.animate.rotate(PI/4))
        self.wait(1)""",
        "file_class": "AnimatedSquare",
        "stream": True
    }
    
    print("Sending streaming request...")
    print(f"Code: {payload['code'][:50]}...")
    
    start_time = time.time()
    video_url = None
    
    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            stream=True,
            timeout=120
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print("\nStreaming progress:")
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    
                    if "animationIndex" in data and "percentage" in data:
                        anim_idx = data["animationIndex"]
                        percent = data["percentage"]
                        print(f"  Animation {anim_idx}: {percent}%")
                    
                    elif "video_url" in data:
                        video_url = data["video_url"]
                        processing_time = data.get("processingTime", "N/A")
                        elapsed = time.time() - start_time
                        print(f"\n[SUCCESS] Video generated!")
                        print(f"  Video URL: {video_url}")
                        print(f"  Processing Time: {processing_time}s")
                        print(f"  Total Time: {elapsed:.2f}s")
                    
                    elif "error" in data:
                        print(f"\n[ERROR] {data['error']}")
                        if "details" in data:
                            print(f"  Details: {data['details']}")
                        return False, None
                        
                except json.JSONDecodeError:
                    print(f"  Raw: {line.decode('utf-8')}")
        
        if video_url:
            # Validate S3 URL
            if "digitaloceanspaces.com" in video_url or "s3" in video_url or "amazonaws.com" in video_url:
                print("[OK] S3 URL format validated")
            return True, video_url
        else:
            print("[ERROR] No video URL received")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out after {time.time() - start_time:.2f}s")
        return False, None
    except Exception as e:
        print(f"[ERROR] Request failed: {str(e)}")
        return False, None


def test_complex_scene():
    """Test 3: More complex scene with multiple animations."""
    print_section("TEST 3: Complex Scene with Multiple Objects")
    
    payload = {
        "code": """class ComplexScene(Scene):
    def construct(self):
        # Create multiple objects
        circle = Circle(radius=1, color=BLUE).shift(LEFT * 2)
        square = Square(side_length=1.5, color=RED).shift(RIGHT * 2)
        triangle = Triangle(color=GREEN).shift(UP * 2)
        
        # Title
        title = Text("S3 Upload Test", font_size=48)
        title.to_edge(DOWN)
        
        # Animate
        self.play(Create(circle), Create(square), Create(triangle))
        self.play(Write(title))
        self.play(
            circle.animate.scale(1.5),
            square.animate.rotate(PI/4),
            triangle.animate.shift(DOWN * 1.5)
        )
        self.wait(1)""",
        "file_class": "ComplexScene",
        "stream": False
    }
    
    print("Sending request...")
    start_time = time.time()
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=180)
        elapsed = time.time() - start_time
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Time Taken: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            if "video_url" in data:
                video_url = data["video_url"]
                print(f"\n[SUCCESS] Video URL: {video_url}")
                return True, video_url
            else:
                print("[ERROR] No video_url in response")
                return False, None
        else:
            print(f"[ERROR] Request failed: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"[ERROR] Request failed: {str(e)}")
        return False, None


def verify_video_url(url):
    """Verify the video URL is accessible."""
    print_section(f"Verifying Video URL")
    print(f"URL: {url}")
    
    try:
        response = requests.head(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'unknown')
            content_length = response.headers.get('Content-Length', 'unknown')
            
            print(f"Content-Type: {content_type}")
            print(f"Content-Length: {content_length} bytes")
            
            if 'video' in content_type.lower() or 'mp4' in content_type.lower():
                print("[OK] Video is accessible and valid")
                return True
            else:
                print(f"[WARNING] Unexpected content type: {content_type}")
                return True
        else:
            print(f"[ERROR] Video not accessible (status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to verify URL: {str(e)}")
        return False


def main():
    """Run all tests."""
    print_header("Manim Renderer API Test Suite")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Endpoint: {API_ENDPOINT}")
    
    results = {
        "passed": 0,
        "failed": 0,
        "video_urls": []
    }
    
    # Test 1: Simple scene
    success, url = test_simple_scene()
    if success:
        results["passed"] += 1
        if url:
            results["video_urls"].append(url)
            verify_video_url(url)
    else:
        results["failed"] += 1
    
    # Test 2: Streaming
    success, url = test_streaming_scene()
    if success:
        results["passed"] += 1
        if url:
            results["video_urls"].append(url)
            verify_video_url(url)
    else:
        results["failed"] += 1
    
    # Test 3: Complex scene
    success, url = test_complex_scene()
    if success:
        results["passed"] += 1
        if url:
            results["video_urls"].append(url)
            verify_video_url(url)
    else:
        results["failed"] += 1
    
    # Summary
    print_header("Test Summary")
    print(f"Total Tests: {results['passed'] + results['failed']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    if results["video_urls"]:
        print(f"\nGenerated Videos:")
        for i, url in enumerate(results["video_urls"], 1):
            print(f"  {i}. {url}")
    
    print("\n" + "="*70 + "\n")
    
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())