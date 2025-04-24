from icrawler.builtin import GoogleImageCrawler
from PIL import Image, ImageDraw, ImageFont
import os
import csv
import difflib
from email.message import EmailMessage
from email.utils import make_msgid
from mimetypes import guess_type

PROSPECT_DATA_PATH = 'data\cbs_prospect_rankings.csv'

# Clear any existing images in the directory
def clear_temp_images():
    for file in os.listdir('./temp_images'):
        file_path = os.path.join('./temp_images', file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error while deleting file {file_path}: {e}")


def clear_final_images():
    for file in os.listdir('./final_graphics'):
        file_path = os.path.join('./final_graphics', file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error while deleting file {file_path}: {e}")


# Download the images
def fetch_images(Name):
    # Create images directory if it doesn't exist
    if not os.path.exists('./temp_images'):
        os.makedirs('./temp_images')
    google_crawler = GoogleImageCrawler(storage={'root_dir': './temp_images'})
    filters = dict(
        size = 'large',
    )
    google_crawler.crawl(keyword=Name, max_num=5, filters=filters)


# Crop the image to a square with the player in the center
def crop_images():
    for file in os.listdir('./temp_images'):
        if file.lower() == 'draft_template_filled.png':
            continue
        try:
            file_path = os.path.join('./temp_images', file)
            img = Image.open(file_path)
            width, height = img.size

            # Determine the size of the square crop
            new_size = min(width, height)

            # Calculate the coordinates for the crop
            left = (width - new_size) / 2
            top = 0  # Changed from (height - new_size) / 2 to 0 for top alignment
            right = (width + new_size) / 2
            bottom = top + new_size  # Changed to ensure square dimensions from the top

            # Crop and save the image
            cropped_img = img.crop((left, top, right, bottom))
            base, ext = os.path.splitext(file)
            new_filename = f"{base}_cropped{ext}"
            new_path = os.path.join('./temp_images', new_filename)
            cropped_img.save(new_path)
        except Exception as e:
            print(f"Error while processing image {file}: {e}")


# Adds the filled template on top of our images
def apply_template_overlay():
    template_path = 'temp_images/draft_template_filled.png'
    template = Image.open(template_path).convert("RGBA")
    template_size = template.size

    for file in os.listdir('./temp_images'):
        if not file.lower().endswith(('_cropped.png', '_cropped.jpg')):
            continue
        if file.lower() == 'draft_template_filled.png':
            continue
        file_path = os.path.join('./temp_images', file)
        base_img = Image.open(file_path).convert("RGBA")

        # Resize base image to match template if needed
        if base_img.size != template_size:
            base_img = base_img.resize(template_size)

        # Composite the template over the image
        combined = Image.alpha_composite(base_img, template)

        # Save result
        base_name, ext = os.path.splitext(file)
        output_path = os.path.join('./final_graphics', f"{base_name}_templated.png")
        combined.save(output_path)
        print(f"Templated image saved: {output_path}")


# Returns a string representing the round and pick for the given overall pick
def get_round_and_pick(overall_pick):
    round_starts = {
        1: 1,
        2: 33,
        3: 65,
        4: 103,
        5: 139,
        6: 177,
        7: 217
    }
    round_ends = {
        1: 32,
        2: 64,
        3: 102,
        4: 138,
        5: 176,
        6: 216,
        7: 257
    }

    for round_number in range(1, 8):
        start = round_starts[round_number]
        end = round_ends[round_number]
        if start <= overall_pick <= end:
            pick_in_round = overall_pick - start + 1
            return f"round {round_number} pick {pick_in_round}"

    return "Pick number out of range"


def fit_text(draw, text, max_width, font_path, max_font_size, min_font_size=40, stroke_width=2):
    font_size = max_font_size
    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, size=font_size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font
        font_size -= 2
    return ImageFont.truetype(font_path, size=min_font_size)


# Adds the text to the template image
def add_text_to_template(player_data):
    player_name = player_data["Name"].lower()
    player_position = player_data["Position"]
    player_school = player_data["School"]
    player_pick = player_data["Pick"]
    player_round_and_pick_string = get_round_and_pick(player_pick)

    font_path = "assets/evogria.otf"
    max_name_font_size = 120
    bottom_row_font_size = 36

    file_path = "assets/draft_template.png"
    img = Image.open(file_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    text_box_top = int(height * 0.805)
    text_box_height = int(height * 0.05)

    # Fixed X starting point
    start_x = int(width * 0.28)
    max_text_width = int(width * 0.66)  # from start_x to right edge (adjustable)

    # Fit name text
    top_row_font = fit_text(
        draw, player_name, max_text_width, font_path, max_name_font_size
    )

    # Y position for name text
    name_bbox = draw.textbbox((0, 0), player_name, font=top_row_font, stroke_width=2)
    text_height = name_bbox[3] - name_bbox[1]
    y = text_box_top + (text_box_height - text_height) / 2

    # Draw name text
    draw.text((start_x, y), player_name, font=top_row_font, fill="white", stroke_width=2, stroke_fill="black")

    # Bottom row metadata
    metadata_row = f"{player_round_and_pick_string}, {player_position}, {player_school}".lower()
    bottom_row_font = ImageFont.truetype(font_path, size=bottom_row_font_size)
    draw.text((start_x, y + top_row_font.size + 16), metadata_row, font=bottom_row_font, fill="white", stroke_width=2, stroke_fill="black")

    # Save output
    new_filename = 'draft_template_filled.png'
    new_path = os.path.join('./temp_images', new_filename)
    img.save(new_path)
    print(f"Saved with fixed-x name and metadata: {new_filename}")


# Returns the player data based on the provided name
# Allows for typos by using difflib, so that we can type quickly.
def find_closest_player(name, csv_path=PROSPECT_DATA_PATH):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        players = list(reader)
        names = [player['Name'] for player in players]
        
        # Find the closest match
        closest_match = difflib.get_close_matches(name, names, n=1, cutoff=0.7)
        if closest_match:
            for player in players:
                if player['Name'] == closest_match[0]:
                    print(f"Found closest player: {player}")
                    return player
        else:
            return None


def generate_samples(player_data):
    fetch_images(player_data["Name"])
    add_text_to_template(player_data)
    crop_images()
    apply_template_overlay()
    

if __name__ == '__main__':
    name = input("Enter player name: ")
    player_data = find_closest_player(name) 
    if not player_data:
        print(f"Could not find player: {name}")
        exit()
    pick = int(input("Enter pick number: "))
    player_data["Pick"] = pick
    clear_final_images()
    generate_samples(player_data)
    clear_temp_images()