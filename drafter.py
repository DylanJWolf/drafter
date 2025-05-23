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
from concurrent.futures import ThreadPoolExecutor

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
def fetch_images(player_data, num_samples=15):
    import glob
    name = player_data["Name"]
    school = player_data["School"]
    search_query = f"{name} {school}"

    if not os.path.exists('./temp_images'):
        os.makedirs('./temp_images')

    # First crawl: name + school (up to num_samples)
    google_crawler = GoogleImageCrawler(storage={'root_dir': './temp_images'})
    google_crawler.downloader_threads = 4
    google_crawler.crawl(keyword=search_query, max_num=num_samples, filters=None)

    # Count images downloaded
    image_files = [f for f in os.listdir('./temp_images') if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))]
    num_downloaded = len(image_files)

    # If fewer than num_samples, try to fetch the rest with just the name
    if num_downloaded < num_samples:
        remaining = num_samples - num_downloaded
        google_crawler2 = GoogleImageCrawler(storage={'root_dir': './temp_images'})
        google_crawler2.crawl(keyword=name, max_num=remaining, filters=None)


# Async wrapper for fetch_images
def async_fetch_images(player_data, num_samples=15):
    thread = threading.Thread(target=fetch_images, args=(player_data, num_samples))
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


def generate_samples(player_data, num_samples=15):
    start = time.time()
    fetch_thread = async_fetch_images(player_data, num_samples)
    add_text_to_template(player_data)  # Creates the filled template once

    template_path = './temp_images/draft_template_filled.png'
    if not os.path.exists(template_path):
        print("Template overlay image not found!")
        return

    player_name = player_data["Name"].lower().replace(" ", "_")
    img_count = 1
    processed_files = set()
    max_workers = min(8, os.cpu_count() or 4)  # Use up to 8 threads, or CPU count
    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = []

    def process_image(file, img_count):
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

            # --- Save as temporary file first ---
            temp_output_path = output_path + '.tmp'
            combined.save(temp_output_path, format='PNG')

            # --- After save finishes, rename ---
            os.rename(temp_output_path, output_path)

            print(f"Processed and saved: {output_path}")
        except Exception as e:
            print(f"Error processing image {file}: {e}")

    # Loop while fetch_thread is alive or there are unprocessed images
    while fetch_thread.is_alive() or True:
        files = [f for f in os.listdir('./temp_images') if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith("draft_template_filled")]
        new_files = [f for f in files if f not in processed_files]
        if not new_files and not fetch_thread.is_alive():
            break
        for file in new_files:
            futures.append(executor.submit(process_image, file, img_count))
            img_count += 1
            processed_files.add(file)
        # Remove completed futures
        futures = [f for f in futures if not f.done()]
        time.sleep(0.05)  # Much tighter loop for responsiveness
    # Wait for all processing to finish
    for f in futures:
        f.result()
    end = time.time()
    print(f"Total time: {end - start} seconds")


def run_player_image_pipeline(player_name, pick_number, num_samples=15):
    player_data = find_closest_player(player_name)
    if not player_data:
        return False, f"Could not find player: {player_name}"
    player_data["Pick"] = int(pick_number)
    clear_final_images()
    clear_temp_images() # Clear in case there was an interuption in the previous run
    generate_samples(player_data, num_samples)
    clear_temp_images()
    return True, player_data["Name"]


if __name__ == '__main__':
    name = input("Enter player name: ")
    pick = int(input("Enter pick number: "))
    num_samples = input("How many images to generate? (default 15): ")
    try:
        num_samples = int(num_samples)
        if num_samples <= 0:
            num_samples = 15
    except Exception:
        num_samples = 15
    run_player_image_pipeline(name, pick, num_samples)