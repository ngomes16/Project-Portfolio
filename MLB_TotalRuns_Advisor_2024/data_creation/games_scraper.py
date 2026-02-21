import requests
from bs4 import BeautifulSoup
import pandas as pd



url = "https://www.baseball-reference.com/leagues/majors/2023-schedule.shtml"

page = requests.get(url)

soup = BeautifulSoup(page.text, "html.parser")

games = soup.find_all("p", class_="game")

for game in games:
    strong_tag = game.find('strong')
    if strong_tag:
        # Extract the strong tag team and score
        strong_team = strong_tag.find('a').text.strip()
        strong_score = int(strong_tag.text.strip().split('(')[-1].split(')')[0])
        
        # Extract the other team and score
        all_teams = game.find_all('a', href=True)
        for team in all_teams:
            team_name = team.text.strip()
            if team_name != strong_team:
                other_team_score = int(team.next_sibling.strip().split('(')[-1].split(')')[0])
                print(f"{strong_team} @ {team_name}, {strong_score + other_team_score}")
                break  # Exit loop once other team and score found
