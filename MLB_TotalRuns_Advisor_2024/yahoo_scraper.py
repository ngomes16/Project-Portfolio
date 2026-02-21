import requests
from bs4 import BeautifulSoup

def scrape_yahoo_odds(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  


        soup = BeautifulSoup(response.content, "html.parser")

        # Find ONLY the upcoming games section for good daily updates
        upcoming_games_section = soup.find("h3", class_="YahooSans-Bold Pb(20px) smartphone_Bdb(border-standings)", text="Upcoming")

        if upcoming_games_section:
            # Now go through these games
            games_container = upcoming_games_section.find_next("div", class_="bet-packs-wrapper")
            if games_container:
                # Iterate over each game container
                odds_data = {}
                games = games_container.find_all("div", class_="Fxg(1)")
                for game in games:
                    # Initialize variables to store team names and the associated number
                    team_names = []
                    associated_number = None

                    # Find all spans with team names
                    team_spans = game.find_all("span", class_="Fw(600) Pend(4px) Ell D(ib) Maw(190px) Va(m)")
                    for team_span in team_spans:
                        # Get names of teams
                        team_names.append(team_span.text.strip())

                    # Find the over under
                    # HARD CODED SPECIFIC TO WEBSITE
                    associated_spans = game.find_all("span", class_="Lh(19px)")
                    if len(associated_spans) >= 4:
                        try:
                            associated_number = float(associated_spans[3].text.replace('O ', '').replace('U ', ''))
                        except ValueError:
                            continue

                    if len(team_names) == 2 and associated_number is not None:
                        # Sort team names alphabetically NOT NEEDED ANYMORE BUT WILL KEEP
                        sorted_teams = tuple(sorted(team_names))
                        odds_data[sorted_teams] = associated_number

                return odds_data
            else:
                print("No games container found under upcoming games section.")
                return {}
        else:
            print("Upcoming games section not found.")
            return {}

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}

if __name__ == "__main__":
    url = "https://sports.yahoo.com/mlb/odds/"
    yahoo_expected_runs = scrape_yahoo_odds(url)
    print(yahoo_expected_runs)
