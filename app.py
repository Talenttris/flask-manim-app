import os
import tempfile
import subprocess
from flask import Flask, request, render_template, send_file
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip

# Create the Flask app
app = Flask(__name__)

# Generate voiceover using gTTS
def generate_voiceover(script, output_file="voiceover.mp3"):
    tts = gTTS(text=script, lang='en')  # Generate voiceover
    tts.save(output_file)  # Save to file
    return output_file

# Generate animation using Manim
def generate_animation(script):
    with tempfile.TemporaryDirectory() as tmpdirname:
        script_path = os.path.join(tmpdirname, "manim_script.py")
        output_file = os.path.join(tmpdirname, "animation.mp4")

        # Write the Manim script to a file
        with open(script_path, "w") as f:
            f.write(f"""
from manim import *

class ExampleAnimation(Scene):
    def construct(self):
        text = Text("{script}")
        self.play(Write(text))
        self.wait(2)
""")

        # Run Manim with headless settings
        subprocess.run(
            ["manim", "-pql", script_path, "ExampleAnimation", "--media_dir", tmpdirname, "--disable_caching"],
            check=True
        )

        return output_file  # Return the generated animation file path

# Sync voiceover with animation
def sync_voiceover_with_animation(animation_file, voiceover_file, output_file="final_output.mp4"):
    animation = VideoFileClip(animation_file)  # Load animation
    voiceover = AudioFileClip(voiceover_file)  # Load voiceover

    # Ensure the animation and voiceover are the same length
    if animation.duration > voiceover.duration:
        animation = animation.subclip(0, voiceover.duration)
    else:
        voiceover = voiceover.subclip(0, animation.duration)

    # Set the voiceover as the audio for the animation
    final_video = animation.set_audio(voiceover)
    final_video.write_videofile(output_file, codec="libx264")
    return output_file

# Flask route for the web app
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        script = request.form["script"]
        
        # Generate voiceover
        voiceover_file = generate_voiceover(script)
        
        # Generate animation
        animation_file = generate_animation(script)
        
        # Sync voiceover and animation
        final_output = sync_voiceover_with_animation(animation_file, voiceover_file)
        
        return send_file(final_output, as_attachment=True)
    
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port, debug=True)
