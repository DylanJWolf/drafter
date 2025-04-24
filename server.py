from flask import Flask, render_template_string, request, redirect, url_for
import os
from drafter import run_player_image_pipeline

gallery_dir = os.path.join(os.path.dirname(__file__), 'final_graphics')

app = Flask(__name__)

FORM_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Player Image Generator</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #222; color: #fff; text-align: center; }
        input, button { font-size: 1.2em; margin: 0.5em; }
        .container { margin-top: 5vh; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Player Image Generator</h1>
        <form method="post" action="/generate">
            <input type="text" name="player_name" placeholder="Player Name" required><br>
            <input type="number" name="pick_number" placeholder="Pick Number" required><br>
            <button type="submit">Generate Images</button>
        </form>
        {% if error %}<div style="color: red;">{{ error }}</div>{% endif %}
    </div>
</body>
</html>
'''

GALLERY_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Generated Images</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #111; color: #fff; font-family: sans-serif; text-align: center; }
        .gallery { display: flex; flex-wrap: wrap; gap: 1em; justify-content: center; }
        img { max-width: 300px; border: 2px solid #fff; background: #222; padding: 5px; border-radius: 8px; }
        a { color: #4af; }
    </style>
</head>
<body>
    <h1>Generated Images for {{ player_name }}</h1>
    <div class="gallery">
        {% for img in images %}
            <img src="/final_graphics/{{ img }}" alt="{{ img }}">
        {% endfor %}
    </div>
    <br><a href="/">&larr; Generate another</a>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    return render_template_string(FORM_HTML, error=None)

@app.route('/generate', methods=['POST'])
def generate():
    player_name = request.form.get('player_name', '').strip()
    pick_number = request.form.get('pick_number', '').strip()
    if not player_name or not pick_number.isdigit():
        return render_template_string(FORM_HTML, error="Please enter valid player name and pick number.")
    success, result = run_player_image_pipeline(player_name, pick_number)
    if not success:
        return render_template_string(FORM_HTML, error=result)
    return redirect(url_for('gallery', player_name=result))

@app.route('/gallery')
def gallery():
    player_name = request.args.get('player_name', '')
    # List images in final_graphics for the player
    images = [f for f in os.listdir(gallery_dir)
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) and
              player_name.lower().replace(' ', '_') in f.lower()]
    images.sort()
    return render_template_string(GALLERY_HTML, images=images, player_name=player_name)

# Serve static images from final_graphics
def _static_serve(path):
    from flask import send_from_directory
    return send_from_directory(gallery_dir, path)

app.add_url_rule('/final_graphics/<path:path>', 'static_files', _static_serve)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
