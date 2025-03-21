import os
from flask import Flask, request, jsonify
import openai
from pexels_api import API as PexelsAPI
from pydub import AudioSegment
import whisper
import requests
from dotenv import load_dotenv
import random
import string
from elevenlabs import generate, play, set_api_key
import base64
import json
from PIL import Image
from io import BytesIO
from pydub.playback import play as pydub_play
from pydub import AudioSegment

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load your API keys from .env file
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
D_ID_API_KEY = os.getenv("D_ID_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")

# Set the API keys for third-party services
openai.api_key = OPENAI_API_KEY
set_api_key(ELEVEN_LABS_API_KEY)

# Initialize Pexels API
pexels = PexelsAPI(PEXELS_API_KEY)

# Initialize Whisper for subtitle generation
whisper_model = whisper.load_model("base")  # Change the model if needed

# Helper function to generate random string
def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Helper function to generate speech from text using ElevenLabs
def generate_speech(text):
    audio = generate(text, voice="en_us_male")
    return audio

# Endpoint to get Pexels images
@app.route('/pexels', methods=['GET'])
def get_pexels_images():
    query = request.args.get('query', 'nature')  # Default to 'nature' if no query is provided
    pexels.search(query, page=1, results_per_page=5)
    photos = pexels.get_entries()
    results = [{"url": photo.url, "photographer": photo.photographer} for photo in photos]
    return jsonify(results)

# Endpoint to generate AI voiceover using ElevenLabs API
@app.route('/generate_voiceover', methods=['POST'])
def generate_voiceover():
    data = request.get_json()
    text = data.get('text', '')
    
    # Generate speech using ElevenLabs
    audio = generate_speech(text)
    
    # Save the generated audio file to a temporary location
    file_name = generate_random_string() + ".mp3"
    audio.export(file_name, format="mp3")
    
    # Send the generated audio file as a response
    with open(file_name, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode('utf-8')
    
    return jsonify({"audio": audio_data, "file_name": file_name})

# Endpoint to generate subtitles using Whisper
@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    data = request.get_json()
    audio_file = data.get('audio_file')  # Expecting base64-encoded audio file
    
    # Decode the base64 audio file
    audio_data = base64.b64decode(audio_file)
    audio_path = "/tmp/temp_audio.mp3"
    
    with open(audio_path, "wb") as f:
        f.write(audio_data)
    
    # Use Whisper to generate subtitles
    result = whisper_model.transcribe(audio_path)
    subtitles = result['text']
    
    return jsonify({"subtitles": subtitles})

# Endpoint to generate avatar using D-ID API
@app.route('/generate_avatar', methods=['POST'])
def generate_avatar():
    data = request.get_json()
    image_url = data.get('image_url')
    avatar_name = data.get('name', 'Avatar')
    
    # Generate avatar using D-ID API
    response = requests.post(
        "https://api.d-id.com/talks",
        headers={"Authorization": f"Bearer {D_ID_API_KEY}"},
        json={"source_url": image_url, "output_format": "mp4", "voice": "en_us_male", "name": avatar_name},
    )
    
    if response.status_code == 200:
        video_url = response.json().get("output_url")
        return jsonify({"video_url": video_url})
    else:
        return jsonify({"error": "Failed to generate avatar"}), 400

# Endpoint to interact with OpenAI's GPT model
@app.route('/gpt', methods=['POST'])
def gpt_interaction():
    data = request.get_json()
    prompt = data.get('prompt', 'Hello')
    
    # Call the OpenAI API to get a response
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    
    return jsonify({"response": response.choices[0].text.strip()})

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
