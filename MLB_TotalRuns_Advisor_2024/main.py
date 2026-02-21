from yahoo_scraper import scrape_yahoo_odds
from data_processing import read_historical_data, calculate_betting_strength, determine_betting_recommendation
from twitter import authenticate_twitter, post_to_twitter
import logging

def main():
    logging.info("Starting main function")
    try:
        # Fetch Yahoo's Expected Runs
        url = "https://sports.yahoo.com/mlb/odds/"
        yahoo_expected_runs = scrape_yahoo_odds(url)

        # Read Historical Data
        historical_data = read_historical_data()

        # Calculate Betting Strength
        betting_strength = calculate_betting_strength(yahoo_expected_runs, historical_data)

        # Determine Betting Recommendation
        betting_recommendations = determine_betting_recommendation(betting_strength, yahoo_expected_runs)

        # Prepare messages
        messages = [f"For {teams[0]} v {teams[1]} there is a {recommendation}" for teams, recommendation in betting_recommendations.items()]

        # Authenticate Twitter API
        client = authenticate_twitter()

        # Post to Twitter
        if not messages:
            client.create_tweet(text="There are no recommended bets today")
        else:
            for message in messages:
                client.create_tweet(text=message)

    except Exception as e:
        logging.error(f"Error in main function: {e}")
    

    # if not messages:
    #     print("There are no recommended bets today")
    # else:
    #     print(messages)


if __name__ == "__main__":
    main()