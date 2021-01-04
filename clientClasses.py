import tweepy
from tweepy import API
from tweepy import Cursor
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

import datetime as dt

from textblob import TextBlob

import numpy as np
import pandas as pd
import re
import matplotlib.pyplot as plt

consumer_key = "AUds4eS1BHAq2UcjeaBbmQi0K"
consumer_secret = "iVWKUBzAclrz1ow3XBP5ReMwAX6WUBO9NaXlCYEeiHGj5UVN7a"
access_token = "1319171958286749697-n8l6vveS4glZHOQUHxnH6ozI6ek2eI"
access_token_secret = "X9WKg1NTCmc96R9KscIpJrtQyLcHRMLF1YGuwAgT0MPy2"

# auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
# auth.set_access_token(access_token, access_token_secret)
# api = tweepy.API(auth)

# popularity metric that measures absolute value of relevance
# number of tweets + number of likes + number of retweets*3 + number of replies
# directional for love or hate


class TwitterClient():
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator().authenticate_twitter_app()
        self.twitter_client = API(self.auth)

        self.twitter_user = twitter_user
    
    def get_twitter_client_api(self):
        return self.twitter_client

    def get_tweets(self, num_tweets):
        tweets = []
        for tweet in Cursor(self.twitter_client.user_timeline, id=self.twitter_user).items(num_tweets):
            tweets.append(tweet)
        return tweets

    def get_friend_list(self, num_friends):
        friend_list = []
        for friend in Cursor(self.twitter_client.friends, id=self.twitter_user).items(num_friends):
            friend_list.append(friend)
        return friend_list

    def get_home_timeline_tweets(self, num_tweets):
        home_timeline_tweets = []
        for tweet in Cursor(self.twitter_client.home_timeline, id=self.twitter_user).items(num_tweets):
            home_timeline_tweets.append(tweet)
        return home_timeline_tweets

    def keywords_search(self, keywords, num_tweets, startDate, endDate):
        tweets = []
        for tweet in Cursor(self.twitter_client.search, q=keywords, until=endDate, lang="en").items(num_tweets):
            if tweet.retweet_count > 0:
                if tweet not in tweets:
                    tweets.append(tweet)
            else:
                tweets.append(tweet)
        return tweets

class TwitterAuthenticator():
    def authenticate_twitter_app(self):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        return auth

class TwitterStreamer():
    def __init__(self):
        self.twitter_authenticator = TwitterAuthenticator()

    def stream_tweets(self, fetched_tweet_filename, hash_tag_list):
        # handles twitter authentification and connection to twitter streaming api
        listener = TwitterListener(fetched_tweet_filename)
        auth = self.twitter_authenticator.authenticate_twitter_app()
        stream = Stream(auth, listener)
        stream.filter(track=hash_tag_list)

class TwitterListener(StreamListener):
    def __init__(self, fetched_tweet_filename):
        self.fetched_tweet_filename = fetched_tweet_filename

    def on_data(self, data):
        try: 
            print(data)
            with open(self.fetched_tweet_filename, 'a') as tf:
                tf.write(data)
            return True
        except BaseException as e:
            print("Error on_data: %s" % str(e))
        return True

    def on_error(self, status):
        if status == 420:
            # check for twitter rates limit to prevent banning
            return False
        print(status)

class TweetAnalyzer():
    def clean_tweet(self, tweet):
        return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())

    def analyze_sentiment(self, tweet):
        analysis = TextBlob(self.clean_tweet(tweet))

        if analysis.sentiment.polarity > 0:
            return 1
        elif analysis.sentiment.polarity == 0:
            return 0
        else:
            return -1

    def tweet_pop(self, likes, retweets):
        return 6 + 3*retweets + likes


    def actual_score(self, sentiment, likes, retweets):

        return 6*sentiment + sentiment*likes + sentiment*retweets*3


    def tweets_to_dataframe(self, tweets):
        df = pd.DataFrame(data=[tweet.text for tweet in tweets], columns=['tweets'])

        df['likes'] = np.array([tweet.favorite_count for tweet in tweets])

        df['retweets'] = np.array([tweet.retweet_count for tweet in tweets])

         # df['replies'] = np.array([tweet.reply_count for tweet in tweets])
         # reply_count is only part of the premium api

        df['where'] = np.array([tweet.coordinates for tweet in tweets])
        
        df['when'] = np.array([str(tweet.created_at) for tweet in tweets])

        return df

    def date_grouper(self, df):
        days = [date.split(" ")[0] for date in df['when'].values]
        df['day'] = days
        tweetsGrouped = df[['day', 'pop', 'score']].groupby('day')['score'].agg(np.sum)
        # tweetsGrouped['daily pop'] = tweetsGrouped['pop'].agg(np.sum)
        # tweetsGrouped['daily score'] = tweetsGrouped['score'].agg(np.sum)
        return tweetsGrouped 

if __name__ == "__main__":
    
    hash_tag_list = ["andy dalton", "red rifle"]
    """
    fetched_tweet_filename = "tweets.json"

    twit_cli = TwitterClient("colincowherd")
    print(twit_cli.get_tweets(1))

    twit_streamer = TwitterStreamer()
    twit_streamer.stream_tweets(fetched_tweet_filename, hash_tag_list)
    """
    twitter_client = TwitterClient()
    tweet_analyzer = TweetAnalyzer()
    api = twitter_client.get_twitter_client_api()

    # tweets = api.user_timeline(screen_name="colincowherd", count=200)
    tweets = twitter_client.keywords_search(hash_tag_list, 1000, dt.date.today()-dt.timedelta(days=30), dt.date.today())

    df = tweet_analyzer.tweets_to_dataframe(tweets)

    df['sentiment'] = np.array([tweet_analyzer.analyze_sentiment(tweet) for tweet in df['tweets']])

    df['pop'] = tweet_analyzer.tweet_pop(df['likes'], df['retweets'])

    df['score'] = tweet_analyzer.actual_score(df['sentiment'], df['likes'], df['retweets'])

    # print(tweets[2].retweet_count)
    # print(dir(tweets[0]))

    out = tweet_analyzer.date_grouper(df)

    print(out.head(20))
    # print(np.mean(df['retweets']))

    # Time Series
    # time_likes = pd.Series(data=df['likes'].values, index=df['when'])
    # time_likes.plot(figsize=(16, 4), color='r')
    # plt.show()