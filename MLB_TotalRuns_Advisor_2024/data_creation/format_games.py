from collections import defaultdict

# To store format data
formatted_data = defaultdict(list)

with open('games_data/games_sample.txt', 'r') as file:
    for line in file:
        if line.strip() == "":
            continue
        
        # print(f"Processing line: {line.strip()}")  # Debugging
        # Split by ", " to separate matchup and number
        parts = line.strip().split(", ")
        if len(parts) == 2:
            matchup = parts[0]
            number = float(parts[1])

            # Split by " @ " to separate team names
            teams = matchup.split(" @ ")
            if len(teams) == 2:
                team1 = teams[0].strip()
                team2 = teams[1].strip()

                key = tuple(sorted([team1, team2]))

                formatted_data[key].append(number)
                print(f"Updated dictionary: {key} -> {formatted_data[key]}")  # Debugging print statement


print("Formatted Data:")
for key, value in formatted_data.items():
    print(f"{key}: {value}")
