import re, csv, time, datetime, json, pytz
from urllib.parse import quote
from tabulate import tabulate
from pathlib import Path
import requests

# For OAuth v2.0 User Context authentification
from x_auth import BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
from requests_oauthlib import OAuth1Session

# Note: Make sure you pip install each of the libraries above before running this file - and look at x_auth-example.py for some pointers on getting started

# import helper functions
from helpers import get_parsed_tweets_from_raw_json, get_parsed_users_from_raw_json, get_next_token_from_raw_json, batch, format_follower_count


# =================
# CUSTOMISATION
# =================

user_name = "tombrushwood" # change
batch_size = 100 # [10-100 range] per batch
max_tweets = 450 # required - limit total results to this number
from_days_ago = 7 # required - limit to previous X days - cannot be more than 7
max_users = 500 # required - limit user lookups to this number (will prioritise the most mentioned user accounts)

# Configure additional fields needed
tweet_fields = "created_at,author_id,conversation_id,public_metrics,text"
expansions = "author_id,referenced_tweets.id,in_reply_to_user_id"
user_fields = "name,username,location,verified"
media_fields = ""

# Keywords to look for in the descriptions of users mentioned
priority_keywords = str(input("Enter a comma separated list of keywords to look for in user descriptions: \n"))

# NB: great list for influencers:
# founder, chair, editor, author, journalist, writer, professor, chancellor, campaigner, TV presenter, broadcaster, trustee, ceo, chief exec, executive

# NB: great list for sports:
# Community, competition, free, event, spaces, run, sport, active, activity, charity

# NB: great list for campaigning groups:
# campaign, action, charity, activis, supporting, march


# ==============
# Setup folders
# ==============

# Ideal file structure = /reports/{date}/{keyword}-{date}_{num days}.csv
today_str = datetime.datetime.now().strftime("%d-%m-%Y")
base_dir = "reports/" + today_str + "/"
debug_dir = base_dir + "debug/"
Path(debug_dir).mkdir(parents=True, exist_ok=True)


# =================
# MAIN FUNCTIONS
# =================
    
# Lookup user_id from user_name
def get_id_from_user_name(twitter_client, user_name):
    url = f"https://api.twitter.com/2/users/by/username/{user_name}"
    u = twitter_client.get(url)
    user_json = u.json()
    user_id = user_json['data']['id']
    print(f"{user_name} id lookup returned: {user_id}")
    return user_id

# Get new batch of tweets
def get_new_tweets_from_timeline(twitter_client, user_id, next_token="", batch_size=batch_size, tweet_fields=tweet_fields, expansions=expansions, user_fields=user_fields, media_fields=media_fields):
    # Construct and send a data request
    url = f'https://api.twitter.com/2/users/{user_id}/timelines/reverse_chronological'
    query_string = (f'?max_results={batch_size}&tweet.fields={tweet_fields}&expansions={expansions}&user.fields={user_fields}&media.fields={media_fields}')
    if next_token:
        query_string += f'&pagination_token={next_token}'
    # Return a response object
    return twitter_client.get(url + query_string)

# Get all tweets in a sanitised format
def get_all_tweets_from_timeline(user_name, batch_size, max_tweets):

    # @@@ - Check API limits

    # init vars
    returned_tweet_data = []
    new_tweets = []
    all_tweets_in_loop = []
    next_token = ""
    print("\nFinding tweets from timeline")

    # init Twitter OAuth instance
    twitter_client = OAuth1Session(API_KEY, client_secret=API_SECRET, resource_owner_key=ACCESS_TOKEN, resource_owner_secret=ACCESS_TOKEN_SECRET)

    # First, lookup user_id
    user_id = get_id_from_user_name(twitter_client, user_name)

    # Make initial request for most recent tweets (100 is the maximum allowed count per batch)
    response = get_new_tweets_from_timeline(twitter_client, user_id)

    # Debug - save json list of request response found
    with open(debug_dir + 'timeline-'+today_str+'_request-response.json', 'w') as file:
        json.dump(response.json(), file, indent=4)
    
    # If the request was successful, add new_tweets to all_tweets_in_loop
    if response.status_code == 200: 
        new_tweets = get_parsed_tweets_from_raw_json(response.json()) # Get a nice, organised list of tweets
        print("len(new_tweets): " + str(len(new_tweets))) # debug
        next_token = get_next_token_from_raw_json(response.json()) # get the next page for the paginator
        all_tweets_in_loop.extend(new_tweets) # If tweets found, add them to all_tweets_in_loop
        print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop)) )
    else:
        print("Failed to retrieve data:", response.status_code, response.text)
        time.sleep(30)
    
    # Keep grabbing tweets until there are no tweets left to grab
    while ( len(new_tweets) > 0 ) and ( len(all_tweets_in_loop) < max_tweets ) and ( next_token ):

        # Try to get more tweets
        response = get_new_tweets_from_timeline(twitter_client, user_id, next_token)

        # If the request was successful, add new_tweets to all_tweets_in_loop
        if response.status_code == 200: 
            new_tweets = get_parsed_tweets_from_raw_json(response.json()) # Get a nice, organised list of tweets
            print("len(new_tweets): " + str(len(new_tweets))) # debug
            next_token = get_next_token_from_raw_json(response.json()) # get the next page for the paginator
            all_tweets_in_loop.extend(new_tweets) # If tweets found, add them to all_tweets_in_loop
            print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop)) )
        else:
            print("Failed to retrieve data:", response.status_code, response.text)
            time.sleep(30)

    # Filter tweets by date limit to get tweets_in_range
    utc_now = datetime.datetime.now(pytz.utc)
    tweets_in_range = list(filter(lambda x: (utc_now - datetime.datetime.fromisoformat(x['created_at'])).days < from_days_ago, all_tweets_in_loop))

    print('\nlen(tweets_in_range): ' + str(len(tweets_in_range))) # debug

    if tweets_in_range:
        print("Found %d tweets in timeline over the last %d days. Earliest one found %d days ago (%s)" % (len(tweets_in_range), from_days_ago, (utc_now - datetime.datetime.fromisoformat(tweets_in_range[-1]['created_at'])).days, datetime.datetime.fromisoformat(tweets_in_range[-1]['created_at'])))
        returned_tweet_data.extend(tweets_in_range)
    else:
        print("\nFound 0 tweets from timeline over the last %d days." % (from_days_ago))

    print('\nlen(returned_tweet_data): ' + str(len(returned_tweet_data))) # debug
    
    return returned_tweet_data

# Main search function
def get_search_results(user_id, batch_size, max_tweets):

    # Fetch all tweets from users in list, one by one
    all_tweets = get_all_tweets_from_timeline(user_id, batch_size, max_tweets)

    # Debug - save json list of tweets found
    with open(debug_dir + 'timeline-'+today_str+'_tweets.json', 'w') as file:
        json.dump(all_tweets, file, indent=4)


    # ===========================
    # PROCESS TWEETS
    # ===========================
    
    tweet_count = len(all_tweets)
    print("\nProcessing %d tweets found in list..." % tweet_count)
    

    # FIND ALL MENTIONED USERS
    # Note: Now we're going to look at the tweet content and see which users have been mentioned, how many times

    users_mentioned = []
    for i, tweet in enumerate(all_tweets):
        if (i > 1) and (i % 100 == 0):
            print("...%d tweets processed so far out of %d (%s)" % (i, tweet_count, str(round(i / tweet_count * 100)) + "%"))

        # process user mentions
        users_mentioned_in_tweet = re.findall(r'@([\w]+)', tweet['full_text'])

        for user in users_mentioned_in_tweet:
            # if first entry add new entry, else get index of current user in users_mentioned list, and add new name to list
            if not [x for x in users_mentioned if x['username'].upper() == user.upper()]:
                users_mentioned.append(dict(
                    username = user, # Note: We're not including the '@' as we're going to use this as a search key in a moment
                    mentioned_by_users = ["@" + tweet['username']],
                    example_tweet = tweet['full_text']
                ))
            else:
                # get index of where this user is in the users_mentioned list
                i = [i for i, dic in enumerate(users_mentioned) if dic['username'].upper() == user.upper()][0]
                # if this user isn't in the mentioned_by_users list, include it
                if ("@" + tweet['username']) not in users_mentioned[i]["mentioned_by_users"]:
                    users_mentioned[i]["mentioned_by_users"].append("@" + tweet['username'])
                    # and if this user's post was richer in detail than our existing example_tweet, replace it
                    if len(tweet['full_text']) > len(users_mentioned[i]["example_tweet"]):
                        users_mentioned[i]["example_tweet"] = tweet['full_text']

    # print('\nlen(users_mentioned): ' + str(len(users_mentioned))) # debug
    # print(users_mentioned) # debug

    
    # GET USER DATA FOR MENTIONED USERS
    # Note: We now have a list of users mentioned in tweets (users_mentioned), but we don't know much about them - time to get information about who they are

    if max_users < len(users_mentioned):
        print("\nlooking up the %d most frequently mentioned users" % max_users)
    else:
        print("\nlooking up all %d users mentioned" % len(users_mentioned))

    # Ideally, we just want to get the top mentioned users so we don't do unneccessary data lookups, so let's sort users_mentioned by most mentioned, and just return the first 100
    users_mentioned.sort(key=lambda x: len(x["mentioned_by_users"]), reverse=True)

    user_data = []
    # we're using username as a search key to find the data - just get the most mentioned users for efficiency
    all_usernames = [u['username'] for u in users_mentioned[:max_users]]
    for batch_usernames in batch(all_usernames, 100):
        # Lookup users request
        url = 'https://api.twitter.com/2/users/by'
        headers = { 'Authorization': 'Bearer ' + BEARER_TOKEN }
        user_ids = ",".join(batch_usernames)
        user_fields = "name,username,verified,description,public_metrics,location,entities,url"
        query_string = (f'?usernames={user_ids}&user.fields={user_fields}')
        response = requests.get(url + query_string, headers=headers)

        # If the request was successful
        if response.status_code == 200: 
            new_users = get_parsed_users_from_raw_json(response.json(), debug_dir, 'timeline', today_str)
            user_data.extend(new_users)
            print("Found %d users so far" % len(user_data))

        else:
            print("Failed to retrieve data:", response.status_code, response.text)
            time.sleep(30)
            continue

    # print('\nlen(user_data): ' + str(len(user_data))) # debug
    # print(user_data) # debug

    # Debug - save json list of users found
    with open(debug_dir + 'timeline-'+today_str+'_users.json', 'w') as file:
        json.dump(user_data, file, indent=4)

    
    # CONSTRUCT USER TABLE
    # Note: So now we have a list of users mentioned (users_mentioned), and we have some extra information about each user (user_data) - now we need to combine them to get something readable and useable

    # get list of keywords to prioritise
    priority_keywords_list = [x.strip() for x in priority_keywords.split(",")]

    user_table = []
    priority_user_table = []
    other_user_table = []
    # just export the most mentioned users
    for entry in users_mentioned[:max_users]:
        # locate index of user
        try:
            # Create an index for cross comparison of the users_mentioned list and the user_data list
            i = [i for i, dic in enumerate(user_data) if dic['username'] == entry["username"]][0]
            # Assemble a useful, understandable object of users that combines the lists together
            line_break = ', '
            item = {
                "quick_ref_org": user_data[i]['name'] + '\n' + user_data[i]['url'],
                "quick_ref_tw": format_follower_count(user_data[i]['followers_count']) + ' followers - \n' + "https://www.twitter.com/" + entry["username"],
                "quick_ref_bio": "Description: “" + user_data[i]['description'] + "”\n\n ",
                "name": user_data[i]['name'], # retreive from user_data table
                "username": "@" + entry["username"], # note: we're adding the '@' now after we've embellished the data
                "profile_url": "https://www.twitter.com/" + entry["username"],
                "description": user_data[i]['description'], # retreive from user_data table
                "mentions_count": len(entry["mentioned_by_users"]),
                "location": user_data[i]['location'], # retreive from user_data table
                "url": user_data[i]['url'], # retreive from user_data table - might be " "
                "verified": user_data[i]['verified'], # retreive from user_data table
                "followers_count": user_data[i]['followers_count'], # retreive from user_data table
                "listed_count": user_data[i]['listed_count'], # retreive from user_data table
                # "mentioned_by_users": line_break.join(entry["mentioned_by_users"][:5]) + ', ...',
                "example_tweet": re.sub(r"\n|\r", " ", entry["example_tweet"]).replace('\"',"'")
            }
            # get interesting profiles
            if any(substring.upper() in item["description"].upper() for substring in priority_keywords_list):
                item["priority"] = "yes"
                priority_user_table.append(item)
            elif (item["followers_count"] > 100) and (item["mentions_count"] > 1):
                # get other profiles
                item["priority"] = "no"
                other_user_table.append(item)
        except IndexError as e:
            print("tried to find user '%s', but they may have been suspended or deleted. Error reported: %s" % (entry["username"], e))

    priority_user_table.sort(key=lambda item:item['followers_count'], reverse=True)
    priority_user_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    user_table.extend(priority_user_table)
    other_user_table.sort(key=lambda item:item['followers_count'], reverse=True)
    other_user_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    user_table.extend(other_user_table)
    user_table_headers = ["Quick Ref Org", "Quick Ref Twitter", "Quick Ref Bio", "Name", "Username", "Profile URL", "Description", "No. Mentions", "Location", "URL", "Verified", "Follower Count", "Listed Count", "Example Tweet", "Priority", "Notes"]
    user_table_rows = [list(x.values()) for x in user_table]

    # print final results to console
    printable_table_rows = [x[3:8] for x in user_table_rows]
    print(tabulate(printable_table_rows[:5], user_table_headers[3:8], tablefmt="grid", maxcolwidths=40))


    # WRITE RESULTS TO CSV FILE

    print("\nSaving full reports...\n")
    with open(base_dir + 'timeline-report-'+ today_str + "_" + str(from_days_ago) + 'days.csv', 'w', newline='', encoding='utf-8-sig', errors='ignore') as csvfile:
        csv_write = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        seperator = ', '
        csv_write.writerow([("User Timeline: %s" % user_name)])
        csv_write.writerow([("Priority Keywords: %s" % seperator.join(priority_keywords_list))])
        csv_write.writerow([("Av. Tweet Volume: %d / day (%d tweets total measured over %d days)" % ((len(all_tweets) / from_days_ago), len(all_tweets), from_days_ago))])
        csv_write.writerow([" "])

        csv_write.writerow(user_table_headers)
        for row in user_table_rows:
            csv_write.writerow(row)

        print("Saved list to '%stimeline-report-%s_%sdays.csv'" % (base_dir, today_str, str(from_days_ago)))

    # finished, finally


# =================
# MAIN EXECUTION
# =================

get_search_results(user_name, batch_size, max_tweets)

