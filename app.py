import os
import base64
import random
import string
import requests
import tempfile
import psutil  # For memory monitoring
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from elevenlabs import generate, set_api_key
import whisper
from pexels_api import API as PexelsAPI

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
MAX_MEMORY_USAGE = 450  # MB (Render free tier has 512MB)
TEMPFILE_DIR = tempfile.gettempdir()

# Load API keys
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
DID_API_KEY = os.getenv("DID_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
set_api_key(ELEVENLABS_API_KEY)  # ElevenLabs

# Initialize services with memory checks
try:
    # Load tiny Whisper model (~1GB RAM)
    whisper_model = whisper.load_model("tiny")
    print("Successfully loaded Whisper tiny model")
except Exception as e:
    print(f"Error loading Whisper model: {str(e)}")
    whisper_model = None

pexels = PexelsAPI(PEXELS_API_KEY) if PEXELS_API_KEY else None

# Helper functions
def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def check_memory():
    mem = psutil.virtual_memory()
    used_mb = mem.used / (1024 ** 2)
    if used_mb > MAX_MEMORY_USAGE:
        raise MemoryError(f"Memory limit exceeded ({used_mb:.1f}MB/{MAX_MEMORY_USAGE}MB)")

# ----------------------------
# Routes
# ----------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_voiceover', methods=['POST'])
def generate_voiceover_route():
    try:
        check_memory()
        data = request.get_json()
        text = data.get("text", "")
        voice = data.get("voice", "Bella")
        
        if not text:
            return jsonify({"error": "Text is required"}), 400

        audio = generate(text=text, voice=voice)
        return jsonify({"audio_url": audio})
    except MemoryError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Voice generation failed: {str(e)}"}), 500

@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    try:
        check_memory()
        data = request.get_json()
        audio_b64 = data.get("audio_b64")
        
        if not audio_b64:
            return jsonify({"error": "Audio (base64) is required"}), 400

        audio_data = base64.b64decode(audio_b64)
        temp_path = os.path.join(TEMPFILE_DIR, f"{generate_random_string()}.mp3")
        
        with open(temp_path, "wb") as f:
            f.write(audio_data)

        if not whisper_model:
            return jsonify({"error": "Whisper model not loaded"}), 500

        result = whisper_model.transcribe(temp_path)
        os.remove(temp_path)
        return jsonify({"subtitles": result.get("text", "")})
    except MemoryError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Subtitle generation failed: {str(e)}"}), 500

# (Keep other routes similar with memory checks and cleanup)

# ----------------------------
# Video Processing (Most Memory-Intensive)
# ----------------------------

@app.route('/create_final_video', methods=['POST'])
def create_final_video():
    try:
        check_memory()
        data = request.get_json()
        stock_video_url = data.get("stock_video_url")
        audio_url = data.get("audio_url")
        
        if not stock_video_url or not audio_url:
            return jsonify({"error": "Both URLs are required"}), 400

        # Download with streaming to avoid large memory usage
        with requests.get(stock_video_url, stream=True) as vid_resp, \
             requests.get(audio_url, stream=True) as aud_resp:

            vid_path = os.path.join(TEMPFILE_DIR, f"{generate_random_string()}.mp4")
            aud_path = os.path.join(TEMPFILE_DIR, f"{generate_random_string()}.mp3")

            with open(vid_path, "wb") as vf, open(aud_path, "wb") as af:
                for chunk in vid_resp.iter_content(chunk_size=8192):
                    vf.write(chunk)
                for chunk in aud_resp.iter_content(chunk_size=8192):
                    af.write(chunk)

        # Process with cleanup
        try:
            video_clip = VideoFileClip(vid_path)
            audio_clip = VideoFileClip(aud_path).audio
            final_clip = video_clip.set_audio(audio_clip)
            
            output_path = os.path.join(TEMPFILE_DIR, f"final_{generate_random_string()}.mp4")
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            return jsonify({"video_url": output_path})
        finally:
            # Cleanup temp files
            if os.path.exists(vid_path): os.remove(vid_path)
            if os.path.exists(aud_path): os.remove(aud_path)
            video_clip.close()
            final_clip.close()
            
    except MemoryError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Video processing failed: {str(e)}"}), 500

# ----------------------------
# Server Configuration
# ----------------------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
