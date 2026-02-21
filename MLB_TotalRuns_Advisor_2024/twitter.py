import tweepy
import os

def authenticate_twitter():
    bearer_token = os.environ.get('BEARER_TOKEN')
    api_key = os.environ.get('API_KEY')
    api_key_secret = os.environ.get('API_KEY_SECRET')
    access_token = os.environ.get('ACCESS_TOKEN')
    access_token_secret = os.environ.get('ACCESS_TOKEN_SECRET')

    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_key_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    return client

def post_to_twitter(client, messages):
    for message in messages:
        try:
            client.create_tweet(text=message)
            print(f"Posted tweet: {message}")
        except tweepy.errors.Forbidden as e:
            print(f"Error posting tweet: {e} - You may need a different access level.")
        except tweepy.TweepyException as e:
            print(f"Error posting tweet: {e}")





# client.create_tweet(text = "yo")