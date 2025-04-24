import requests
from bs4 import BeautifulSoup
import csv
import re

def scrape_pff_draft_profiles():
    url = "https://www.pff.com/news/draft-2025-nfl-draft-profiles-pff"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the content section
        content = soup.find('div', class_='article-content')
        if not content:
            content = soup  # Use whole page if can't find specific content section
        
        # Extract text content
        text_content = content.get_text()
        
        # Define pattern to extract player rankings with position, name, and school
        # Pattern looks for: number. POSITION NAME, SCHOOL
        pattern = r'(\d+)\.\s+([A-Z/]+)\s+([A-Za-z\'\-\s]+),\s+([A-Za-z\s&\'\-\.]+)'
        matches = re.findall(pattern, text_content)
        
        player_data = []
        
        for match in matches:
            ranking, position, name, school = match
            player_data.append({
                "Rank": ranking.strip(),
                "Position": position.strip(),
                "Name": name.strip(),
                "School": school.strip(),
                "PFF Grade": "N/A"  # Default value, add logic to extract if available
            })
        
        # Write to CSV
        with open('../data/pff_prospect_rankings.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Rank", "Position", "Name", "School", "PFF Grade"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(player_data)
                
        print(f"CSV file created: ../data/pff_prospect_rankings.csv with {len(player_data)} player profiles")
        
    except Exception as e:
        print(f"Error: {e}")
        # Create a blank CSV with error message if there was an error
        with open('../data/pff_prospect_rankings.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Error", f"Failed to scrape data: {str(e)}"])

if __name__ == "__main__":
    scrape_pff_draft_profiles()