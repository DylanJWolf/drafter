import requests
from bs4 import BeautifulSoup
import csv

def fetch_cbs_prospect_rankings():
    url = "https://www.cbssports.com/nfl/draft/prospect-rankings/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table")
    if not table:
        print("Could not find the prospect rankings table.")
        return

    all_headers = [th.text.strip() for th in table.find("thead").find_all("th")]
    wanted_fields = ["Rk", "Player", "Pos", "School"]

    # Safely get column indexes
    try:
        wanted_indexes = [all_headers.index(field) for field in wanted_fields]
    except ValueError as e:
        print(f"One or more target columns not found: {e}")
        return

    output_headers = ["Rank", "Name", "Position", "School"]
    rows = []

    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= len(all_headers):  # Ensure full row of expected columns
            cells = [td.text.strip() for td in tds]
            row = [cells[i] for i in wanted_indexes]
            rows.append(row)

    # Write filtered CSV
    with open("../data/cbs_prospect_rankings.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(output_headers)
        writer.writerows(rows)

    print("Clean CSV created: 'cbs_prospect_rankings.csv'")

if __name__ == "__main__":
    fetch_cbs_prospect_rankings()

