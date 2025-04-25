from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import os
from drafter import run_player_image_pipeline, find_closest_player
from threading import Thread

gallery_dir = os.path.join(os.path.dirname(__file__), 'final_graphics')

app = Flask(__name__)

FORM_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>RFP's Draft Graphics Generator</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #222; color: #fff; text-align: center; }
        input, button { font-size: 1.2em; margin: 0.5em; }
        .container { margin-top: 5vh; }
    </style>
</head>
<body>
    <div class="container">
        <h1>RFP's Draft Image Generator</h1>
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
    <div class="gallery" id="gallery">
        {% for img in images %}
            <img src="/final_graphics/{{ img }}" alt="{{ img }}">
        {% endfor %}
    </div>
    <br><a href="/">&larr; Generate another</a>
    <script>
    const playerName = {{ player_name|tojson }};
    function fetchImages() {
        fetch(`/gallery_data?player_name=${encodeURIComponent(playerName)}`)
            .then(resp => resp.json())
            .then(data => {
                const gallery = document.getElementById('gallery');
                // Remove all children
                while (gallery.firstChild) gallery.removeChild(gallery.firstChild);
                // Add new images
                data.images.forEach(img => {
                    const el = document.createElement('img');
                    el.src = `/final_graphics/${img}`;
                    el.alt = img;
                    gallery.appendChild(el);
                });
            });
    }
    setInterval(fetchImages, 2000); // Poll every 2 seconds
    </script>
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

    # Check if player exists before starting background task
    player_data = find_closest_player(player_name)
    if not player_data:
        return render_template_string(FORM_HTML, error=f"Could not find player: {player_name}")

    corrected_name = player_data['Name']

    # Start image generation in background
    def bg_task():
        run_player_image_pipeline(corrected_name, pick_number)
    Thread(target=bg_task, daemon=True).start()

    # Redirect to /gallery with corrected player name
    return redirect(url_for('gallery', player_name=corrected_name))

@app.route('/gallery')
def gallery():
    player_name = request.args.get('player_name', '')
    images = [f for f in os.listdir(gallery_dir)
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) and
              player_name.lower().replace(' ', '_') in f.lower()]
    images.sort()
    return render_template_string(GALLERY_HTML, images=images, player_name=player_name)

@app.route('/gallery_data')
def gallery_data():
    player_name = request.args.get('player_name', '')
    images = [f for f in os.listdir(gallery_dir)
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) and
              player_name.lower().replace(' ', '_') in f.lower()]
    images.sort()
    return jsonify({'images': images})

# Serve static images from final_graphics
def _static_serve(path):
    from flask import send_from_directory
    return send_from_directory(gallery_dir, path)

app.add_url_rule('/final_graphics/<path:path>', 'static_files', _static_serve)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
