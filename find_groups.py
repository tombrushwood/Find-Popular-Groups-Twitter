import tweepy
import re, csv, time, datetime, json, pytz
from x_auth import BEARER_TOKEN, API_KEY, API_SECRET, CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
import requests
from urllib.parse import quote
import pprint
pp = pprint.PrettyPrinter(indent=4)


# =================
# DEV ORDER
# =================

# 1. Pagination working
# 2. Look for users mentioned in tweets
# 3. Look up user info


# =================
# CUSTOMISATION
# =================

query= str(input("Enter search term: \n"))
batch_size = 10 # Testing only [10-100 range] # per batch - @@@ remove
max_tweets = 20 # required - limit total results
from_days_ago = 28 # required - limit  @@@ get rid of this - max 7 days ago


# ===============================
# DATA MODEL FOR TWEET RESPONSE
# ===============================

# {
#   "data": [
#     {
#       "text": "Looking to get started with the Twitter API but new to APIs in general? @jessicagarson will walk you through everything you need to know in APIs 101 session. She’ll use examples using our v2 endpoints, Tuesday, March 23rd at 1 pm EST.nnJoin us on Twitchnhttps://t.co/GrtBOXyHmB",
#       "author_id": "2244994945",
#       "id": "1373001119480344583",
#       "edit_history_tweet_ids": [
#         "1373001119480344583"
#       ],
#       "lang": "en",
#       "conversation_id": "1373001119480344583",
#       "created_at": "2021-03-19T19:59:10.000Z"
#     }
#   ],
#   "includes": {
#     "users": [
#       {
#         "id": "2244994945",
#         "entities": {
#           "url": {
#             "urls": [
#               {
#                 "start": 0,
#                 "end": 23,
#                 "url": "https://t.co/3ZX3TNiZCY",
#                 "expanded_url": "https://developer.twitter.com/en/community",
#                 "display_url": "developer.twitter.com/en/community"
#               }
#             ]
#           },
#           "description": {
#             "hashtags": [
#               {
#                 "start": 17,
#                 "end": 28,
#                 "tag": "TwitterDev"
#               },
#               {
#                 "start": 105,
#                 "end": 116,
#                 "tag": "TwitterAPI"
#               }
#             ]
#           }
#         },
#         "created_at": "2013-12-14T04:35:55.000Z",
#         "username": "TwitterDev",
#         "name": "Twitter Dev"
#       }
#     ]
#   },
#   "meta": {
#     "newest_id": "1373001119480344583",
#     "oldest_id": "1373001119480344583",
#     "result_count": 1
#   }
# }


# =================
# IDEAL DATA MODEL
# =================

# tweet = {
#     id: 1752666704214126628,
#         # x[data][id]
#     name: 'Agata',
#         # x[includes][users][name] 
#             # where x[includes][users][id] == x[data][author_id]
#     username: 'Agata40038925',
#         # x[includes][users][username] 
#             # where x[includes][users][id] == x[data][author_id]
#     full_text: 'RT @jakarinpuribhat: HELLO SINGAPORE \u2764\ufe0f https://t.co/NkneFzy6Bs',
#         # x[data][text]
#         # if x[data][referenced_tweets]
#             # + "RE:" 
#             # + x[includes][tweets][text]
#                 # where x[data][referenced_tweets][id] == x[includes][tweets][id]
#     created_at: '2024-01-31T12:14:39.000Z'
#         # x[data][created_at]
# }
# next_token = 'b26v89c19zqg8o3fr5qdmbh1n7ci9j26suor6iht0pda5'
#     # x[meta][next_token]


# =====================================
# CUSTOMISING THE TWEET DATA RESPONSE
# =====================================

# Configure optional extra forms - otherwise by default, just tweet and id are returned.

# FULL SET OF ADDITIONAL FIELDS
    # tweet_fields = "created_at,author_id,conversation_id,public_metrics,text"
    # expansions = "author_id,referenced_tweets.id,in_reply_to_user_id,attachments.media_keys"
    # user_fields = "name,username,location,verified"
    # media_fields = "url,preview_image_url,type"

# FULL SET OF ADDITIONAL FIELDS
tweet_fields = "created_at,author_id,conversation_id,public_metrics,text"
expansions = "author_id,referenced_tweets.id,in_reply_to_user_id"
user_fields = "name,username,location,verified"
media_fields = ""


def get_parsed_tweets_from_raw_json(raw_tweet_json):

    # set variables
    result_count = raw_tweet_json['meta']['result_count']
    tweet_list = [[] for i in range(result_count)]

    # print(json.dumps(raw_tweet_json, indent=4))  # Debugging - print the response JSON

    # For each tweet in raw response
    for i in range(result_count):

        # Clean the data and assemble the tweet_list object

        tweet_list[i] = {}
        # set tweet_list['id']
        tweet_list[i]['id'] = raw_tweet_json['data'][i]['id']
        # Find author details from author_id
        author_id = raw_tweet_json['data'][i]['author_id']
        user = next((user for user in raw_tweet_json['includes']['users'] if user['id'] == author_id), None)
        if user:
            # set tweet_list['name']
            tweet_list[i]['name'] = user['name']
            # set tweet_list['username']
            tweet_list[i]['username'] = user['username']
        else:
            print(f"No user found for author_id {author_id}")
        # set tweet_list['full_text']
        if 'referenced_tweets' in raw_tweet_json['data'][i]:
            # match with referenced tweet
            post_id = raw_tweet_json['data'][i]['referenced_tweets'][0]['id']
            type = raw_tweet_json['data'][i]['referenced_tweets'][0]['type']
            post = next((post for post in raw_tweet_json['includes']['tweets'] if post['id'] == post_id), None)
            if post:
                # if retweet
                if type == "retweeted":
                    rt = re.match(r"^(.*RT \@.+?: )", raw_tweet_json['data'][i]['text'])
                    tweet_list[i]['full_text'] = str(rt.group(0)) + post['text']
                # if replied to
                elif type == "replied_to":
                    tweet_list[i]['full_text'] = raw_tweet_json['data'][i]['text'] + " RE: " + post['text']
                else:
                    tweet_list[i]['full_text'] = post['text']
            else: # can't find referenced tweet - use shortened version
                tweet_list[i]['full_text'] = raw_tweet_json['data'][i]['text']
        else: # no referenced tweet - use shortened version
            tweet_list[i]['full_text'] = raw_tweet_json['data'][i]['text']
        # set tweet['created_at']
        tweet_list[i]['created_at'] = raw_tweet_json['data'][i]['created_at']

    return tweet_list


def get_next_token_from_raw_json(raw_tweet_json):
    # get next_token for pagination
    if 'next_token' in raw_tweet_json['meta']:
        return raw_tweet_json['meta']['next_token']


# =================
# MAIN FUNCTIONS
# =================

# Get all tweets from all search queries
def get_all_tweets_from_search_queries(query_list, batch_size, max_tweets):

    # @@@ - Check API limits

    # init vars
    returned_tweet_data = []
    all_tweets_in_loop = [[] for i in range(len(query_list))]
    next_token = ""
    print("\nFinding tweets from %d search terms in list" % len(query_list))

    # iterate through query list
    for i, query in enumerate(query_list):

        print("\nFinding tweets from search term '%s'..." % query)

        # ===================================
        # CONSTRUCTING THE FIRST DATA REQUEST
        # ===================================

        # Construct Twitter URL
        url = 'https://api.twitter.com/2/tweets/search/recent'
        headers = {
            'Authorization': 'Bearer ' + BEARER_TOKEN
        }
        query_string = (
            f'?query={quote(query)}'
            f'&max_results={batch_size}'
            f'&tweet.fields={tweet_fields}'
            f'&expansions={expansions}'
            f'&user.fields={user_fields}'
            f'&media.fields={media_fields}'
        )
        full_url = url + query_string
        print(full_url)

        # Make initial request for most recent tweets (100 is the maximum allowed count per batch)
        try:
            # =================================
            # SENDING THE FIRST DATA REQUEST
            # =================================

            r = requests.get(full_url, headers=headers)
            # If the request was successful
            if r.status_code == 200: 
                
                # Get a nice, organised list of tweets
                new_tweets = get_parsed_tweets_from_raw_json(r.json())

                # get the next page for the paginator
                next_token = get_next_token_from_raw_json(r.json())

                # If tweets found, add them to the all_tweets_in_loop array
                all_tweets_in_loop[i].extend(new_tweets)

                # save the id of the oldest tweet less one
                # oldest = all_tweets_in_loop[i][-1].id - 1
                # batch_start_days_ago = utc_now - all_tweets_in_loop[i][-1].includes['users'][0]['created_at']  @@@ Add in

            else:
                print("Failed to retrieve data:", response.status_code, response.text)
        except requests.RequestException as e:
            print("\nReceived an error from Twitter. Waiting 30 seconds before retry. Error returned:", e, "\n")
            time.sleep(30)
            continue

        # If tweets were found...
        if new_tweets:

            # Keep grabbing tweets until there are no tweets left to grab
            while (new_tweets) and (len(all_tweets_in_loop[i]) < max_tweets): # @@@ Add batch_start_days_ago back in

                print("...%s tweets downloaded so far" % (len(all_tweets_in_loop[i])))

                # ====================================
                # CONSTRUCT ADDITIONAL DATA REQUESTS
                # ====================================

                # Construct Twitter URL
                url = 'https://api.twitter.com/2/tweets/search/recent'
                headers = {
                    'Authorization': 'Bearer ' + BEARER_TOKEN
                }
                query_string = (
                    f'?query={quote(query)}'
                    f'&max_results={batch_size}'
                    f'&tweet.fields={tweet_fields}'
                    f'&expansions={expansions}'
                    f'&user.fields={user_fields}'
                    f'&media.fields={media_fields}'
                    f'&next_token={next_token}' # added
                )
                full_url = url + query_string
                print(full_url)

                # Try to get more tweets
                try:

                    # ================================
                    # SEND ADDITIONAL DATA REQUESTS
                    # ================================

                    # generate the request
                    r = requests.get(full_url, headers=headers)

                    # If the request was successful
                    if r.status_code == 200: 
                        new_tweets = get_parsed_tweets_from_raw_json(r.json())
                        next_token = get_next_token_from_raw_json(r.json())

                        # If tweets found, add them to the all_tweets_in_loop array
                        all_tweets_in_loop[i].extend(new_tweets)

                        # save the id of the oldest tweet less one
                        # oldest = all_tweets_in_loop[i][-1].id - 1
                        # batch_start_days_ago = utc_now - all_tweets_in_loop[i][-1].includes['users'][0]['created_at']  @@@ Add in

                    else:
                        print("Failed to retrieve data:", response.status_code, response.text)
                except requests.RequestException as e:
                    print("\nReceived an error from Twitter. Waiting 30 seconds before retry. Error returned:", e, "\n")
                    time.sleep(30)
                    continue

        # Filter tweets by date limit
        # utc_now = datetime.datetime.now(pytz.utc)
        # tweets_in_range = list(filter(lambda x: (utc_now - x.includes['users'][0]['created_at']).days < from_days_ago, all_tweets_in_loop[i]))
        tweets_in_range = all_tweets_in_loop[i]

        if tweets_in_range:
            # print("Found %d tweets from term '%s' over the last %d days. Earliest one found %d days ago (%s)" % (len(tweets_in_range), query, from_days_ago, (utc_now - tweets_in_range[-1].includes['users'][0]['created_at']).days, tweets_in_range[-1].includes['users'][0]['created_at']))
            returned_tweet_data.extend(new_tweets)
        else:
            print("Found 0 tweets from term '%s' over the last %d days." % (query, from_days_ago))
        
    return returned_tweet_data

# Main search function
def get_search_results(query_list, batch_size, max_tweets):

    # Error checking
    if not query_list:
        print("Please specify a search term")
        return False

    # Fetch all tweets from users in list, one by one
    all_tweets = get_all_tweets_from_search_queries(query_list, batch_size, max_tweets)

    # Testing - Print recent tweets from an array
    # pp = pprint.PrettyPrinter(indent=4)
    for tweet in all_tweets:
        print("TWEET:")
        print(tweet)
    


    # ===========================
    # PROCESS TWEETS
    # ===========================
    
    tweet_count = len(all_tweets)
    print("\nProcessing %d tweets found in list..." % tweet_count)

    # Save as a JSON file

    

# =================
# MAIN EXECUTION
# =================

query_list = [x.strip() for x in query.split(",")]
get_search_results(query_list, batch_size, max_tweets)

