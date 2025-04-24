from icrawler.builtin import GoogleImageCrawler
from PIL import Image, ImageDraw, ImageFont
import os
import csv
import difflib
from email.message import EmailMessage
from email.utils import make_msgid
from mimetypes import guess_type
import time
import threading

PROSPECT_DATA_PATH = 'data\cbs_prospect_rankings.csv'
NUM_SAMPLES = 15


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
        # Skip image_server.py and any other .py files
        if file.endswith('.py'):
            continue
        file_path = os.path.join('./final_graphics', file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error while deleting file {file_path}: {e}")


# Download the images
def fetch_images(player_data):
    import glob
    name = player_data["Name"]
    school = player_data["School"]
    search_query = f"{name} {school}"

    if not os.path.exists('./temp_images'):
        os.makedirs('./temp_images')

    # First crawl: name + school (up to NUM_SAMPLES)
    google_crawler = GoogleImageCrawler(storage={'root_dir': './temp_images'})
    google_crawler.crawl(keyword=search_query, max_num=NUM_SAMPLES, filters=None)

    # Count images downloaded
    image_files = [f for f in os.listdir('./temp_images') if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))]
    num_downloaded = len(image_files)

    # If fewer than NUM_SAMPLES, try to fetch the rest with just the name
    if num_downloaded < NUM_SAMPLES:
        remaining = NUM_SAMPLES - num_downloaded
        google_crawler2 = GoogleImageCrawler(storage={'root_dir': './temp_images'})
        google_crawler2.crawl(keyword=name, max_num=remaining, filters=None)


# Async wrapper for fetch_images
def async_fetch_images(player_data):
    thread = threading.Thread(target=fetch_images, args=(player_data,))
    thread.start()
    return thread


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
    start_x = int(width * 0.27)
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
    start = time.time()
    fetch_thread = async_fetch_images(player_data)
    add_text_to_template(player_data)  # Creates the filled template once

    template_path = './temp_images/draft_template_filled.png'
    if not os.path.exists(template_path):
        print("Template overlay image not found!")
        return

    player_name = player_data["Name"].lower().replace(" ", "_")
    img_count = 1
    processed_files = set()
    # Loop while fetch_thread is alive or there are unprocessed images
    while fetch_thread.is_alive() or True:
        files = [f for f in os.listdir('./temp_images') if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith("draft_template_filled")]
        new_files = [f for f in files if f not in processed_files]
        if not new_files and not fetch_thread.is_alive():
            break
        for file in new_files:
            try:
                file_path = os.path.join('./temp_images', file)
                img = Image.open(file_path)
                width, height = img.size

                # Square crop logic
                new_size = min(width, height)
                left = (width - new_size) / 2
                top = 0
                right = left + new_size
                bottom = top + new_size
                cropped_img = img.crop((left, top, right, bottom))

                # Resize to match template dimensions
                template = Image.open(template_path).convert("RGBA")
                cropped_img = cropped_img.resize(template.size).convert("RGBA")

                # Composite
                combined = Image.alpha_composite(cropped_img, template)

                # Save final with player name and index
                output_filename = f"{player_name}_{img_count}.png"
                output_path = os.path.join('./final_graphics', output_filename)
                combined.save(output_path)
                print(f"Processed and saved: {output_path}")
                img_count += 1
                processed_files.add(file)
            except Exception as e:
                print(f"Error processing image {file}: {e}")
        time.sleep(0.2)  # Avoid tight loop
    end = time.time()
    print(f"Total time: {end - start} seconds")
    
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