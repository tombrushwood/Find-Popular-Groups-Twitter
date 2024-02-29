# ==========================================================
# IMPORTANT:
# AS OF JUNE 2023, TWITTER NO LONGER SUPPORTS THIS FUNCTION, UNLESS YOU'RE ON THE ENTERPRISE TIER ($42,000 PER MONTH)
# ==========================================================

print("Aborting.")
quit()


import re, csv, time, datetime, json, pytz
from urllib.parse import quote
from tabulate import tabulate
from pathlib import Path
import requests

# For OAuth v2.0 User Context authentification
from x_auth import BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
from requests_oauthlib import OAuth1Session

# Note: Make sure you pip install each of the libraries above before running this file - and look at x_auth-example.py for some pointers on getting started

# =================
# CUSTOMISATION
# =================

user_name = str(input("Enter username to get follower list from: \n"))
batch_size = 20 # 1000 [10-1000 range] per batch. Note: lookup will be in reverse date order, so newest followers are fetched first.
max_users = 20 # 50000 required - limit follower lookups to this number

# Configure additional fields needed
tweet_fields = "" # "created_at,author_id,conversation_id,public_metrics,text"
expansions = ""
user_fields = "" # "name,username,location,verified"

# SET CATEGORIES TO LOOK FOR

def str_to_list(str):
    list = [x.strip() for x in str.split(",")]
    return list

journalist_keywords = str_to_list("journalist, columnist, editor, correspondent, reporter")
author_keywords = str_to_list("author, writer, novelist, screenwriter, co-author")
celeb_keywords_list = str_to_list("actress, actor, presenter, broadcaster, comedian")
mp_keywords = str_to_list("former leader, MP for, member of parliament, minister of, MSP for, Senedd, leader of, mayor of, House of Lords, @UKHouseofLords")
exec_keywords = str_to_list("founder, cofounder, co-chair, chairman, chair of, CEO, creator of, managing director, entrepreneur, director, president of, CIO, CMO, CTO, non exec")
trustee_keywords = str_to_list("fellow, patron, trustee, NED, ambassador")
activist_keywords = str_to_list("campaign manager, senior advisor, activist, campaigner")
other_media_keywords = str_to_list("host of, podcaster")
other_keywords_list = str_to_list("investor, professor, keynote speaker")

# ==============
# Setup folders
# ==============

# Ideal file structure = /reports/{date}/{username}-followers_limit-{max_users}.csv
today_str = datetime.datetime.now().strftime("%d-%m-%Y")
base_dir = "reports/" + today_str + "/"
debug_dir = base_dir + "debug/"
Path(debug_dir).mkdir(parents=True, exist_ok=True)


# =================
# HELPER FUNCTIONS
# =================

def get_next_token_from_raw_json(raw_tweet_json):
    # get next_token for pagination
    if 'next_token' in raw_tweet_json['meta']:
        return raw_tweet_json['meta']['next_token']

# Create batches from large lists for processing
def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]
    # USAGE
    # for x in batch(range(0, 10), 3):
    #     print x


# =================
# MAIN FUNCTIONS
# =================

# Lookup user_id from user_name
def get_id_from_user_name(user_name):
    url = f"https://api.twitter.com/2/users/by/username/{user_name}"
    headers = { 'Authorization': 'Bearer ' + BEARER_TOKEN }
    u = requests.get(url, headers=headers)
    user_json = u.json()
    user_id = user_json['data']['id']
    print(f"{user_name} id lookup returned: {user_id}")
    return user_id

# Get new batch of tweets
def get_new_followers(user_id, next_token="", batch_size=batch_size, tweet_fields=tweet_fields, expansions=expansions, user_fields=user_fields):
    # Construct and send a data request
    url = f'https://api.twitter.com/2/users/{user_id}/followers'
    headers = { 'Authorization': 'Bearer ' + BEARER_TOKEN }
    query_string = (f'?max_results={batch_size}&tweet.fields={tweet_fields}&expansions={expansions}&user.fields={user_fields}')
    if next_token:
        query_string += f'&pagination_token={next_token}'
    # Return a response object
    return requests.get(url + query_string, headers=headers)

def get_all_followers(user_name):
    
    # @@@ - Check API limits            

    # init vars
    new_users = []
    all_users_in_loop = []
    next_token = ""
    print(f"\nFinding followers of {user_name}")

    # First, lookup user_id
    user_id = get_id_from_user_name(user_name)

    # Make initial request for most recent followers (1000 is the maximum allowed count per batch)
    response = get_new_followers(user_id)

    # Debug - save json list of request response found
    with open(debug_dir + user_name + '-followers_request-response.json', 'w') as file:
        json.dump(response.json(), file, indent=4)

    
    # # If the request was successful, add new_users to all_users_in_loop
    # if response.status_code == 200:
    #     new_users = get_parsed_users_from_raw_json(response.json()) # Get a nice, organised list of tweets
    #     print("len(new_users): " + str(len(new_users))) # debug
    #     next_token = get_next_token_from_raw_json(response.json()) # get the next page for the paginator
    #     all_users_in_loop.extend(new_users) # If tweets found, add them to all_tweets_in_loop
    #     print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop)) )
    # else:
    #     print("Failed to retrieve data:", response.status_code, response.text)
    #     time.sleep(30)
    
    # # Keep grabbing tweets until there are no tweets left to grab
    # while ( len(new_tweets) > 0 ) and ( len(all_tweets_in_loop) < max_tweets ) and ( next_token ):

    #     # Try to get more tweets
    #     response = get_new_tweets_from_timeline(twitter_client, user_id, next_token)

    #     # If the request was successful, add new_tweets to all_tweets_in_loop
    #     if response.status_code == 200: 
    #         new_tweets = get_parsed_tweets_from_raw_json(response.json()) # Get a nice, organised list of tweets
    #         print("len(new_tweets): " + str(len(new_tweets))) # debug
    #         next_token = get_next_token_from_raw_json(response.json()) # get the next page for the paginator
    #         all_tweets_in_loop.extend(new_tweets) # If tweets found, add them to all_tweets_in_loop
    #         print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop)) )
    #     else:
    #         print("Failed to retrieve data:", response.status_code, response.text)
    #         time.sleep(30)




# =================
# MAIN EXECUTION
# =================

get_all_followers(user_name)