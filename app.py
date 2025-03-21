import os
import requests
from flask import Flask, request, render_template, send_file
from moviepy.editor import VideoFileClip, AudioFileClip
from dotenv import load_dotenv
from pexels_api import API as PexelsAPI
from whisper import Whisper

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# API keys from environment
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
D_ID_API_KEY = os.getenv("D_ID_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

# 1. AI Voiceover Generation (Completed with ElevenLabs)
def generate_voiceover(script, voice="Rachel", output_file="voiceover.mp3"):
    headers = {
        "Authorization": f"Bearer {ELEVENLABS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {"text": script, "voice": voice}
    response = requests.post("https://api.elevenlabs.io/v1/text-to-speech", json=data, headers=headers)
    
    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return output_file
    return None

# 2. AI Avatar Generation (D-ID API)
def generate_avatar(script, avatar_name="Rachel"):
    # Integrate with D-ID API for AI avatar
    response = requests.post(
        "https://api.d-id.com/avatars",
        headers={"Authorization": f"Bearer {D_ID_API_KEY}"},
        json={"script": script, "avatar": avatar_name}
    )
    avatar_video = "avatar_video.mp4"  # Store avatar video locally
    with open(avatar_video, 'wb') as f:
        f.write(response.content)  # Save the avatar video
    return avatar_video

# 3. Stock Footage (Pexels API)
def fetch_stock_video(query="nature"):
    pexels = PexelsAPI(PEXELS_API_KEY)
    pexels.search(query, page=1, results_per_page=1)
    video_url = pexels.get_videos()[0].video_files[0].link  # Extract video link
    return video_url

# 4. Subtitles & Effects (Whisper AI)
def generate_subtitles(video_file):
    whisper = Whisper(WHISPER_API_KEY)
    subtitles = whisper.transcribe(video_file)
    return subtitles

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        script = request.form["script"]
        voice = request.form.get("voice", "Rachel")

        # Generate voiceover
        voiceover_file = generate_voiceover(script, voice)
        if not voiceover_file:
            return "Error generating voiceover", 500

        # Generate avatar video
        avatar_video_file = generate_avatar(script)
        if not avatar_video_file:
            return "Error generating avatar video", 500
        
        # Fetch stock footage
        stock_video_url = fetch_stock_video()
        
        # Combine everything (animations, voice, avatar, stock footage, subtitles) here
        # Sync everything and generate final video

        return send_file(avatar_video_file, as_attachment=True)
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
