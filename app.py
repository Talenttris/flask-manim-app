from flask import Flask, request, render_template, send_file
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip
import subprocess

app = Flask(__name__)

def generate_voiceover(script, output_file="voiceover.mp3"):
    tts = gTTS(text=script, lang='en')
    tts.save(output_file)
    return output_file

def generate_animation(script, output_file="animation.mp4"):
    with open("manim_script.py", "w") as f:
        f.write(f"""
from manim import *

class ExampleAnimation(Scene):
    def construct(self):
        text = Text("{script}")
        self.play(Write(text))
        self.wait(2)

scene = ExampleAnimation()
scene.render()
        """)
    
    subprocess.run(["manim", "-ql", "manim_script.py", "ExampleAnimation", "-o", output_file])
    return output_file

def sync_voiceover_with_animation(animation_file, voiceover_file, output_file="final_output.mp4"):
    animation = VideoFileClip(animation_file)
    voiceover = AudioFileClip(voiceover_file)

    if animation.duration > voiceover.duration:
        animation = animation.subclip(0, voiceover.duration)
    else:
        voiceover = voiceover.subclip(0, animation.duration)

    final_video = animation.set_audio(voiceover)
    final_video.write_videofile(output_file, codec="libx264")
    return output_file

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        script = request.form["script"]
        voiceover_file = generate_voiceover(script)
        animation_file = generate_animation(script)
        final_output = sync_voiceover_with_animation(animation_file, voiceover_file)
        return send_file(final_output, as_attachment=True)
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
