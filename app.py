import os
import openai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import moviepy.editor as mp
import requests
from pydub import AudioSegment
from pexels_api import API  # Correct import for pexels-api

load_dotenv()

app = Flask(__name__)

# Load environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')

# Pexels API setup (correct usage of Pexels API client)
pexels_api = API(PEXELS_API_KEY)

# Home route to render UI
@app.route('/')
def home():
    return render_template('index.html')

# AI Voiceover (via OpenAI API)
@app.route('/generate_voiceover', methods=['POST'])
def generate_voiceover():
    data = request.json
    text = data.get("text")
    if not text:
        return jsonify({"error": "Text input is required"}), 400
    
    # Generating voiceover with OpenAI API or other services
    voice = generate_ai_voiceover(text)  # Placeholder for voice generation
    return jsonify({"voiceover": voice})

# AI Voiceover Function (to be implemented based on available APIs)
def generate_ai_voiceover(text):
    # Use OpenAI API or any other voice synthesis tool here
    return "Generated voiceover for the text"

# Avatar generation function (using D-ID or another AI tool)
@app.route('/generate_avatar', methods=['POST'])
def generate_avatar():
    data = request.json
    text = data.get("text")
    if not text:
        return jsonify({"error": "Text input is required"}), 400
    
    avatar = generate_ai_avatar(text)
    return jsonify({"avatar": avatar})

def generate_ai_avatar(text):
    # Implement using D-ID or another avatar creation service
    return "Generated Avatar Image URL or Information"

# Subtitles generation function (using Whisper or another AI tool)
@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    data = request.json
    audio_url = data.get("audio_url")
    if not audio_url:
        return jsonify({"error": "Audio URL is required"}), 400
    
    subtitles = generate_subtitles_from_audio(audio_url)
    return jsonify({"subtitles": subtitles})

def generate_subtitles_from_audio(audio_url):
    # Implement using Whisper or other tools to transcribe and generate subtitles
    return "Generated Subtitles"

# Movie or video editing function
@app.route('/edit_video', methods=['POST'])
def edit_video():
    data = request.json
    video_url = data.get("video_url")
    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400
    
    video = download_video(video_url)
    edited_video = apply_video_edits(video)
    return jsonify({"video": edited_video})

def download_video(video_url):
    # Download the video from the URL
    response = requests.get(video_url)
    return response.content

def apply_video_edits(video):
    # Apply moviepy edits here (such as trim, add audio, etc.)
    return "Edited Video URL or Information"

if __name__ == '__main__':
    app.run(debug=True)
