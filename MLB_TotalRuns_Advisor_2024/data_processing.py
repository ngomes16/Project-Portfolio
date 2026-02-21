def read_historical_data():
    historical_data = {}
    with open('games_data/formatted_data.txt', 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                # THIS IS ASSUMING the format is consistent ('team1', 'team2'): [list_of_scores]
                key_value = line.split(':')
                teams = eval(key_value[0].strip())
                scores = eval(key_value[1].strip())
                historical_data[teams] = scores
    return historical_data

def calculate_betting_strength(yahoo_expected_runs, historical_data):
    betting_strength = {}

    for teams, yahoo_expected in yahoo_expected_runs.items():
        # Find using either order of teams
        historical_scores = historical_data.get(teams, historical_data.get((teams[1], teams[0]), []))

        if not historical_scores:
            betting_strength[teams] = "No historical data available"
            continue

        # Calculate % of games where matchup went over yahoo's guess
        count_above = sum(1 for score in historical_scores if score > yahoo_expected)
        total_games = len(historical_scores)

        percentage_above = count_above / total_games if total_games > 0 else 0.0

        # Out of 10.0
        betting_strength_score = percentage_above * 10.0

        betting_strength[teams] = betting_strength_score

    return betting_strength

def determine_betting_recommendation(betting_strength, yahoo_expected_runs):
    betting_recommendations = {}

    for teams, strength_score in betting_strength.items():
        # Check if strength_score is a number
        if isinstance(strength_score, (int, float)):
            # Round to one decimal point for ease
            rounded_strength_score = round(strength_score, 1)
            
            yahoo_prediction = yahoo_expected_runs.get(teams, "unknown")

            if rounded_strength_score >= 8.0:
                betting_recommendations[teams] = f"very favored bet for the Over on line of {yahoo_prediction}"
            elif rounded_strength_score >= 7.2:
                betting_recommendations[teams] = f"favored bet for the Over on line of {yahoo_prediction}"
            elif rounded_strength_score >= 6.7:
                betting_recommendations[teams] = f"slightly favored bet for the Over on line of {yahoo_prediction}"
            elif 0.0 <= rounded_strength_score <= 2.0:
                betting_recommendations[teams] = f"very favored bet for the Under on line of {yahoo_prediction}"
            elif 2.1 <= rounded_strength_score <= 2.8:
                betting_recommendations[teams] = f"favored bet for the Under on line of {yahoo_prediction}"
            elif 2.9 <= rounded_strength_score <= 3.3:
                betting_recommendations[teams] = f"slightly favored bet for the Under on line of {yahoo_prediction}"
            if 3.4 <= rounded_strength_score <= 6.6:
                continue  # Skip "No bet" recommendations

            
    return betting_recommendations


# based on betting strength {rounded_strength_score}
# based on betting strength {10 - rounded_strength_score}
