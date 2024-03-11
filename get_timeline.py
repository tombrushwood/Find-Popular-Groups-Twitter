import csv, time, datetime, json, pytz
from tabulate import tabulate

# For OAuth v2.0 User Context authentification
from x_auth import API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
from requests_oauthlib import OAuth1Session

# Note: Make sure you pip install each of the libraries above before running this file - and look at x_auth-example.py for some pointers on getting started

# Next let's import all shared helper functions and global vars
from helpers import *


# =================
# CUSTOMISATION
# =================

# setup timeline search - input user slug to find tweets from their timeline
user_name = "tombrushwood" # Change as required

# configure search volumes
batch_size = 100 # required - [10-100 range] per batch
max_tweets = 450 # required - limit total results to this number (Note: 5 max requests per 15 mins to this endpoint)
from_days_ago = 7 # required - limit to previous X days - cannot be more than 7
max_users = 500 # required - limit user lookups to this number (will prioritise the most mentioned user accounts)
report_title_prefix = "timeline" # used for filenames on report exports and for debugging

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

# We will first make sure we have the required folders set up for exporting the final reports and debug files
create_folders()


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
def get_all_tweets_from_timeline(user_name, max_tweets=max_tweets):

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
    
    # If the request was successful, add new_tweets to all_tweets_in_loop
    if response.status_code == 200: 
        new_tweets = get_parsed_tweets_from_raw_json(response.json()) # Get a nice, organised list of tweets
        print("len(new_tweets): " + str(len(new_tweets))) # debug
        next_token = get_next_token_from_raw_json(response.json()) # get the next page for the paginator
        all_tweets_in_loop.extend(new_tweets) # If tweets found, add them to all_tweets_in_loop
        print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop)) )
    else:
        print("Failed to retrieve data:", response.status_code, response.text)
        # Abort script if we failed to retreive any tweets due to error
        print("No tweet data. Aborting.")
        time.sleep(10)
        quit()
    
    # Keep grabbing tweets until there are no tweets left to grab
    no_errors = True
    while ( len(new_tweets) > 0 ) and ( len(all_tweets_in_loop) < max_tweets ) and ( next_token ) and ( no_errors ):

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
            # Abort new tweet lookup upon error
            no_errors = False
            print("Proceeding with the data that's already been gathered.")
            time.sleep(10)
            continue

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
def get_search_results(user_name):

    # Fetch all tweets from users in list, one by one
    all_tweets = get_all_tweets_from_timeline(user_name)

    # Debug - save json list of tweets found
    with open(debug_dir + report_title_prefix+'-'+today_str+'_tweets.json', 'w') as file:
        json.dump(all_tweets, file, indent=4)


    # ===========================
    # PROCESS TWEETS
    # ===========================
    
    print("\nProcessing %d tweets found in list..." % len(all_tweets))

    # FIND ALL MENTIONED USERS
    # Note: Now we're going to look at the tweet content and see which users have been mentioned, how many times
    users_mentioned = return_users_mentioned_from_all_tweets(all_tweets)
    
    # GET USER DATA FOR MENTIONED USERS
    # Note: We now have a list of users mentioned in tweets (users_mentioned), but we don't know much about them - time to get information about who they are
    if max_users < len(users_mentioned):
        print("\nlooking up the %d most frequently mentioned users" % max_users)
    else:
        print("\nlooking up all %d users mentioned" % len(users_mentioned))
    valid_users, user_data = get_user_data_for_users_mentioned(users_mentioned, debug_keyword=report_title_prefix)

    # Debug - save json list of users found
    with open(debug_dir + report_title_prefix+'-'+today_str+'_users.json', 'w') as file:
        json.dump(user_data, file, indent=4)

    # CONSTRUCT USER TABLE
    # Note: So now we have a list of users mentioned (valid_users), and we have some extra information about each user (user_data) - now we need to combine them to get something readable and useable
    user_table_headers, user_table_rows = create_user_table_from_user_data(valid_users, user_data, priority_keywords, max_users)

    # PRINT RESULTS TO CONSOLE
    printable_table_rows = [x[3:8] for x in user_table_rows]
    print(tabulate(printable_table_rows[:5], user_table_headers[3:8], tablefmt="grid", maxcolwidths=40))

    # WRITE RESULTS TO CSV FILE
    print("\nSaving full reports...\n")
    with open(base_dir + report_title_prefix+'-report-'+ today_str + "_" + str(from_days_ago) + 'days.csv', 'w', newline='', encoding='utf-8-sig', errors='ignore') as csvfile:
        csv_write = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        csv_write.writerow([("User Timeline: %s" % str(user_name))])
        csv_write.writerow([("Priority Keywords: %s" % str(priority_keywords))])
        csv_write.writerow([("Av. Tweet Volume: %d / day (%d tweets total measured over %d days)" % ((len(all_tweets) / from_days_ago), len(all_tweets), from_days_ago))])
        csv_write.writerow([" "])

        csv_write.writerow(user_table_headers)
        for row in user_table_rows:
            csv_write.writerow(row)

        print("Saved list to '%s%s-report-%s_%sdays.csv'" % (base_dir, report_title_prefix, today_str, str(from_days_ago)))

    # finished, finally


# =================
# MAIN EXECUTION
# =================

get_search_results(user_name)

