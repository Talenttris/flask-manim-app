import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import openai
import requests
from pexels import Pexels
import moviepy.editor as mpy
import json

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set up API keys from .env
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
D_ID_API_KEY = os.getenv("D_ID_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize APIs
openai.api_key = OPENAI_API_KEY
pexels_api = Pexels(PEXELS_API_KEY)

# Route to serve homepage
@app.route('/')
def home():
    return render_template('index.html')

# Route to generate AI voiceover using ElevenLabs API
@app.route('/generate_voice', methods=['POST'])
def generate_voice():
    text = request.form['text']
    voice = request.form['voice']
    voiceover_url = f'https://api.elevenlabs.io/v1/generate?voice={voice}&text={text}'

    headers = {
        "Authorization": f"Bearer {ELEVENLABS_API_KEY}"
    }
    
    response = requests.post(voiceover_url, headers=headers)
    audio_url = response.json().get('audio_url', None)
    
    return jsonify({'audio_url': audio_url})

# Route to generate AI avatar using D-ID API
@app.route('/generate_avatar', methods=['POST'])
def generate_avatar():
    text = request.form['text']
    
    # D-ID API request to create avatar from text
    avatar_url = f'https://api.d-id.com/v1/avatars'
    headers = {
        "Authorization": f"Bearer {D_ID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text
    }
    
    response = requests.post(avatar_url, headers=headers, json=payload)
    avatar_response = response.json()
    
    avatar_video_url = avatar_response.get('video_url', None)
    
    return jsonify({'avatar_video_url': avatar_video_url})

# Route to fetch stock footage from Pexels
@app.route('/get_stock_footage', methods=['GET'])
def get_stock_footage():
    query = request.args.get('query', 'nature')
    results = pexels_api.search(query, per_page=5)
    videos = []
    
    for photo in results['photos']:
        videos.append(photo['url'])

    return jsonify({'videos': videos})

# Route to generate subtitles using Whisper API
@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    video_file = request.files['video']
    
    # Save the video file to a temporary location
    video_path = os.path.join('uploads', video_file.filename)
    video_file.save(video_path)
    
    # Send video to Whisper API for subtitle generation
    whisper_url = 'https://api.openai.com/v1/audio/transcriptions'
    headers = {
        'Authorization': f'Bearer {WHISPER_API_KEY}'
    }
    
    files = {'file': open(video_path, 'rb')}
    data = {
        'model': 'whisper-1',
        'language': 'en',
    }
    
    response = requests.post(whisper_url, headers=headers, files=files, data=data)
    
    transcription = response.json()
    subtitles = transcription.get('text', None)
    
    return jsonify({'subtitles': subtitles})

# Route to generate a simple video using MoviePy (just for demo purposes)
@app.route('/generate_video', methods=['POST'])
def generate_video():
    audio_url = request.form['audio_url']
    video_url = request.form['video_url']
    
    # Download audio and video files from URLs
    audio_file = requests.get(audio_url)
    video_file = requests.get(video_url)
    
    # Save files locally (This step may need improvement for larger files)
    with open("audio.mp3", 'wb') as audio_out:
        audio_out.write(audio_file.content)
    with open("video.mp4", 'wb') as video_out:
        video_out.write(video_file.content)
    
    # Create a video clip from the downloaded video
    video_clip = mpy.VideoFileClip("video.mp4")
    
    # Set the audio of the video clip
    audio_clip = mpy.AudioFileClip("audio.mp3")
    final_video = video_clip.set_audio(audio_clip)
    
    # Write the final video to a file
    final_video.write_videofile("final_video.mp4")
    
    return jsonify({'message': 'Video created successfully'})

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)
