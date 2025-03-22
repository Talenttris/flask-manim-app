import os
import base64
import random
import string
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from elevenlabs import generate_voiceover, set_api_key  # Updated import for ElevenLabs
import whisper
from pexels_api import API as PexelsAPI

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load API keys from environment variables
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

# Helper function: Generate a random string (for temporary filenames)
def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ---------------------------------------
# Home endpoint: renders a basic UI
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
    voice = data.get("voice", "Bella")  # Default voice; adjust as needed
    if not text:
        return jsonify({"error": "Text is required"}), 400

    # Generate voiceover using ElevenLabs API
    audio_url = generate_voiceover(text, voice=voice)  # Updated function call
    return jsonify({"audio_url": audio_url})

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
    headers = {
        "Authorization": f"Bearer {DID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "source_url": image_url,
        "script": {"type": "text", "input": script},
        "output_format": "mp4"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        video_url = response.json().get("output_url")
        return jsonify({"video_url": video_url})
    else:
        return jsonify({"error": "Avatar generation failed", "details": response.text}), 400

# ---------------------------------------
# Endpoint: Generate subtitles using Whisper
# ---------------------------------------
@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    data = request.get_json()
    audio_b64 = data.get("audio_b64")
    if not audio_b64:
        return jsonify({"error": "Audio (base64) is required"}), 400

    # Decode the base64 audio file and save temporarily
    audio_data = base64.b64decode(audio_b64)
    temp_audio_path = f"/tmp/{generate_random_string()}.mp3"
    with open(temp_audio_path, "wb") as f:
        f.write(audio_data)

    # Use Whisper to transcribe the audio file into subtitles
    result = whisper_model.transcribe(temp_audio_path)
    subtitles = result.get("text", "")
    os.remove(temp_audio_path)
    return jsonify({"subtitles": subtitles})

# ---------------------------------------
# Endpoint: Fetch stock video using Pexels API
# ---------------------------------------
@app.route('/get_stock_video', methods=['GET'])
def get_stock_video():
    query = request.args.get("query", "nature")
    page = int(request.args.get("page", 1))
    # Search for videos using the Pexels API client
    response = pexels.search_videos(query, page=page, results_per_page=1)
    videos = response.get("videos", [])
    if videos:
        video_url = videos[0].get("video_files", [{}])[0].get("link")
        return jsonify({"video_url": video_url})
    else:
        return jsonify({"error": "No videos found"}), 404

# ---------------------------------------
# Endpoint: Create final video by merging components (stock video, voiceover, subtitles)
# ---------------------------------------
@app.route('/create_final_video', methods=['POST'])
def create_final_video():
    data = request.get_json()
    stock_video_url = data.get("stock_video_url")
    audio_url = data.get("audio_url")
    subtitles_text = data.get("subtitles", "No subtitles provided.")

    if not stock_video_url or not audio_url:
        return jsonify({"error": "Stock video URL and audio URL are required."}), 400

    # Download stock video and audio files
    video_response = requests.get(stock_video_url)
    audio_response = requests.get(audio_url)

    temp_video_path = f"/tmp/{generate_random_string()}.mp4"
    temp_audio_path = f"/tmp/{generate_random_string()}.mp3"
    with open(temp_video_path, "wb") as f:
        f.write(video_response.content)
    with open(temp_audio_path, "wb") as f:
        f.write(audio_response.content)

    # Load the video and audio clips using MoviePy
    video_clip = VideoFileClip(temp_video_path)
    # Use AudioFileClip if audio is separate:
    from moviepy.editor import AudioFileClip
    audio_clip = AudioFileClip(temp_audio_path)

    # Create a TextClip for subtitles (displayed at the bottom of the video)
    subtitle_clip = TextClip(subtitles_text, fontsize=24, color="white", bg_color="black")\
                        .set_position(("center", "bottom")).set_duration(video_clip.duration)

    # Set the audio for the video and overlay the subtitles
    final_clip = video_clip.set_audio(audio_clip)
    final_video = CompositeVideoClip([final_clip, subtitle_clip])
    final_output_path = f"/tmp/final_video_{generate_random_string()}.mp4"
    final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac")

    return jsonify({"final_video_path": final_output_path})

# ---------------------------------------
# Endpoint: OpenAI GPT interaction (if needed)
# ---------------------------------------
@app.route('/gpt', methods=['POST'])
def gpt_interaction():
    data = request.get_json()
    prompt = data.get("prompt", "Hello")
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return jsonify({"response": response.choices[0].text.strip()})

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
