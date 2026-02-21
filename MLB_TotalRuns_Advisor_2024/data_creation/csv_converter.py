import csv

input_file = 'games.txt'
games = 'games.csv'


with open(input_file, 'r') as f:
    lines = f.readlines()

# Prepare data for CSV format
data = []
for line in lines:
    # Split each line by '@'
    parts = [part.strip() for part in line.split('@')]
    if len(parts) == 2:
        team1, team2_and_score = parts
        # Split team2_and_score by ','
        team2_parts = [part.strip() for part in team2_and_score.split(',')]
        if len(team2_parts) == 2:
            team2 = team2_parts[0]
            score = team2_parts[1]
            data.append([team1, team2, score])

with open(games, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Team 1', 'Team 2', 'Score'])
    writer.writerows(data)
