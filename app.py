import os
import base64
import random
import string
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from elevenlabs import generate, set_api_key
import whisper
from pexels_api import API as PexelsAPI
import tempfile

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load API keys from .env
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
DID_API_KEY = os.getenv("DID_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")  # (if needed for advanced config)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")      # (if using OpenAI GPT)

# Set ElevenLabs API key for the library
set_api_key(ELEVENLABS_API_KEY)

# Initialize Pexels API client
pexels = PexelsAPI(PEXELS_API_KEY)

# Load the Whisper model (using the open-source model)
whisper_model = whisper.load_model("base")

# Helper: Generate a random string for filenames
def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ---------------------------------------
# Endpoint: Home (renders a basic UI)
# ---------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------------------------------
# Endpoint: Generate AI voiceover using ElevenLabs
# ---------------------------------------
@app.route('/generate_voiceover', methods=['POST'])
def generate_voiceover_route():
    data = request.get_json()
    text = data.get("text", "")
    voice = data.get("voice", "Bella")  # default voice; adjust per ElevenLabs docs
    if not text:
        return jsonify({"error": "Text is required"}), 400

    # Generate voiceover using ElevenLabs API
    try:
        audio_url = generate(text, voice=voice)  # This returns the URL for the audio file
        return jsonify({"audio_url": audio_url})
    except Exception as e:
        return jsonify({"error": f"Failed to generate voiceover: {str(e)}"}), 500

# ---------------------------------------
# Endpoint: Generate AI avatar video using D-ID REST API
# ---------------------------------------
@app.route('/generate_avatar', methods=['POST'])
def generate_avatar():
    data = request.get_json()
    image_url = data.get("image_url")
    script = data.get("script", "Hello, this is your AI avatar speaking.")
    if not image_url:
        return jsonify({"error": "Image URL is required"}), 400

    url = "https://api.d-id.com/talks"
    headers = {"Authorization": f"Bearer {DID_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "source_url": image_url,
        "script": {"type": "text", "input": script},
        "output_format": "mp4"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        video_url = response.json().get("output_url")
        if not video_url:
            return jsonify({"error": "No output URL found in response"}), 500
        return jsonify({"video_url": video_url})
    else:
        return jsonify({"error": "Avatar generation failed", "details": response.text}), 400

# ---------------------------------------
# Endpoint: Generate subtitles using Whisper
# ---------------------------------------
@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    # Expect a base64-encoded audio file in the request
    data = request.get_json()
    audio_b64 = data.get("audio_b64")
    if not audio_b64:
        return jsonify({"error": "Audio (base64) is required"}), 400

    try:
        audio_data = base64.b64decode(audio_b64)
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"{generate_random_string()}.mp3")
        with open(temp_audio_path, "wb") as f:
            f.write(audio_data)

        # Use Whisper to transcribe the audio
        result = whisper_model.transcribe(temp_audio_path)
        subtitles = result.get("text", "")
        os.remove(temp_audio_path)
        return jsonify({"subtitles": subtitles})
    except Exception as e:
        return jsonify({"error": f"Failed to generate subtitles: {str(e)}"}), 500

# ---------------------------------------
# Endpoint: Fetch stock footage (example using Pexels)
# ---------------------------------------
@app.route('/get_stock_video', methods=['GET'])
def get_stock_video():
    query = request.args.get("query", "nature")
    page = int(request.args.get("page", 1))
    # Search for videos (assuming the pexels_api client supports it)
    response = pexels.search_videos(query, page=page, results_per_page=1)
    videos = response.get("videos", [])
    if videos:
        video_url = videos[0].get("video_files", [{}])[0].get("link")
        return jsonify({"video_url": video_url})
    else:
        return jsonify({"error": "No videos found"}), 404

# ---------------------------------------
# Endpoint: Create final video by merging components (voiceover, subtitles, stock footage)
# ---------------------------------------
@app.route('/create_final_video', methods=['POST'])
def create_final_video():
    data = request.get_json()
    stock_video_url = data.get("stock_video_url")
    audio_url = data.get("audio_url")
    # For subtitles, you could use the /generate_subtitles endpoint separately
    subtitles_text = data.get("subtitles", "No subtitles provided.")

    if not stock_video_url or not audio_url:
        return jsonify({"error": "Stock video URL and audio URL are required."}), 400

    try:
        # Download stock video and audio file (this is a simplified example)
        video_response = requests.get(stock_video_url)
        audio_response = requests.get(audio_url)

        temp_video_path = os.path.join(tempfile.gettempdir(), f"{generate_random_string()}.mp4")
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"{generate_random_string()}.mp3")
        with open(temp_video_path, "wb") as f:
            f.write(video_response.content)
        with open(temp_audio_path, "wb") as f:
            f.write(audio_response.content)

        # Load video and audio clips with MoviePy
        video_clip = VideoFileClip(temp_video_path)
        audio_clip = VideoFileClip(temp_audio_path).audio  # or use AudioFileClip if separate

        # Create a simple TextClip for subtitles (displayed at the bottom)
        subtitle_clip = TextClip(subtitles_text[:100], fontsize=24, color="white", bg_color="black")\
                            .set_position(("center", "bottom")).set_duration(video_clip.duration)

        # Set the audio to the video clip
        final_clip = video_clip.set_audio(audio_clip)
        # Overlay subtitles
        final_video = CompositeVideoClip([final_clip, subtitle_clip])
        final_output_path = os.path.join(tempfile.gettempdir(), f"final_video_{generate_random_string()}.mp4")
        final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac")

        # (Optionally, upload final video somewhere and return URL)
        return jsonify({"final_video_path": final_output_path})
    except Exception as e:
        return jsonify({"error": f"Failed to create final video: {str(e)}"}), 500

# ---------------------------------------
# Endpoint: OpenAI GPT interaction (if needed)
# ---------------------------------------
@app.route('/gpt', methods=['POST'])
def gpt_interaction():
    data = request.get_json()
    prompt = data.get("prompt", "Hello")
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        return jsonify({"response": response.choices[0].text.strip()})
    except Exception as e:
        return jsonify({"error": f"Failed to interact with GPT: {str(e)}"}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
