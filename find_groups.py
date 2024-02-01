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
max_tweets = 25 # required - limit total results
from_days_ago = 28 # required - limit  @@@ get rid of this - max 7 days ago

# Configure additional fields needed
tweet_fields = "created_at,author_id,conversation_id,public_metrics,text"
expansions = "author_id,referenced_tweets.id,in_reply_to_user_id"
user_fields = "name,username,location,verified"
media_fields = ""


# Clean the data and assemble the tweet_list object
def get_parsed_tweets_from_raw_json(raw_tweet_json):

    # set variables
    result_count = raw_tweet_json['meta']['result_count']
    tweet_list = [[] for i in range(result_count)]

    # print(json.dumps(raw_tweet_json, indent=4))  # Debugging - print the response JSON

    # For each tweet in raw response
    for i in range(result_count):

        # We need to transform the data so it's more useable

        # tweet = {
        #     id: 123,
        #     name: 'XXX',
        #     username: 'XXX',
        #     full_text: 'XXX',
        #     created_at: 'Datetime'
        # }
        
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
    new_tweets = []
    all_tweets_in_loop = [[] for i in range(len(query_list))]
    next_token = ""
    print("\nFinding tweets from %d search terms in list" % len(query_list))

    # iterate through query list
    for i, query in enumerate(query_list):

        print("\nFinding tweets from search term '%s'..." % query)

        # Make initial request for most recent tweets (100 is the maximum allowed count per batch)
        try:
            # Construct and send first data request
            url = 'https://api.twitter.com/2/tweets/search/recent'
            headers = { 'Authorization': 'Bearer ' + BEARER_TOKEN }
            query_string = (f'?query={quote(query)}&max_results={batch_size}&tweet.fields={tweet_fields}&expansions={expansions}&user.fields={user_fields}&media.fields={media_fields}')
            r = requests.get(url + query_string, headers=headers)
            
            # If the request was successful
            if r.status_code == 200: 
                new_tweets = get_parsed_tweets_from_raw_json(r.json())# Get a nice, organised list of tweets
                print("len(new_tweets): " + str(len(new_tweets))) # debug
                print(new_tweets) # debug
                next_token = get_next_token_from_raw_json(r.json()) # get the next page for the paginator
                print("next_token: " + next_token) # debug
                all_tweets_in_loop[i].extend(new_tweets) # If tweets found, add them to all_tweets_in_loop
                print("len(all_tweets_in_loop[i]): " + str( len(all_tweets_in_loop[i])) ) # debug
                print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop[i])) ) # debug
                # batch_start_days_ago = utc_now - all_tweets_in_loop[i][-1]['created_at'] # save the created_at of the oldest tweet
            else:
                print("Failed to retrieve data:", r.status_code, r.text)

        except requests.RequestException as e:
            print("\nReceived an error from Twitter. Waiting 30 seconds before retry. Error returned:", e, "\n")
            time.sleep(30)
            continue

        # Keep grabbing tweets until there are no tweets left to grab
        while ( len(new_tweets) > 0 ) and ( len(all_tweets_in_loop[i]) < max_tweets ): # @@@ Add batch_start_days_ago back in

            # Try to get more tweets
            try:
                print("next_token: " + next_token) # debug

                # Construct and send further data requests
                url = 'https://api.twitter.com/2/tweets/search/recent'
                headers = { 'Authorization': 'Bearer ' + BEARER_TOKEN }
                query_string = (
                    f'?query={quote(query)}&max_results={batch_size}&tweet.fields={tweet_fields}&expansions={expansions}&user.fields={user_fields}&media.fields={media_fields}'
                    f'&next_token={next_token}'
                )
                print(url + query_string) # debug
                r = requests.get(url + query_string, headers=headers)

                # If the request was successful
                if r.status_code == 200: 
                    new_tweets = get_parsed_tweets_from_raw_json(r.json()) # Get a nice, organised list of tweets
                    print("len(new_tweets): " + str(len(new_tweets))) # debug
                    print(new_tweets) # debug
                    next_token = get_next_token_from_raw_json(r.json()) # get the next page for the paginator
                    print("next_token: " + next_token) # debug
                    all_tweets_in_loop[i].extend(new_tweets) # If tweets found, add them to all_tweets_in_loop
                    print("len(all_tweets_in_loop[i]): " + str( len(all_tweets_in_loop[i])) ) # debug
                    print("...%s tweets downloaded so far" % ( len(all_tweets_in_loop[i])) ) # debug
                    # batch_start_days_ago = utc_now - all_tweets_in_loop[i][-1]['created_at'] # save the created_at of the oldest tweet
                else:
                    print("Failed to retrieve data:", r.status_code, r.text)
            except requests.RequestException as e:
                print("\nReceived an error from Twitter. Waiting 30 seconds before retry. Error returned:", e, "\n")
                time.sleep(30)
                continue

        # Filter tweets by date limit
        utc_now = datetime.datetime.now(pytz.utc)
        tweets_in_range = list(filter(lambda x: (utc_now - datetime.datetime.fromisoformat(x['created_at'])).days < from_days_ago, all_tweets_in_loop[i]))

        print('len(tweets_in_range): ' + str(len(tweets_in_range))) # debug

        if tweets_in_range:
            print("Found %d tweets from term '%s' over the last %d days. Earliest one found %d days ago (%s)" % (len(tweets_in_range), query, from_days_ago, (utc_now - datetime.datetime.fromisoformat(tweets_in_range[-1]['created_at'])).days, datetime.datetime.fromisoformat(tweets_in_range[-1]['created_at'])))
            returned_tweet_data.extend(tweets_in_range)
        else:
            print("Found 0 tweets from term '%s' over the last %d days." % (query, from_days_ago))

        print('len(returned_tweet_data): ' + str(len(returned_tweet_data))) # debug
        
    return returned_tweet_data

# Main search function
def get_search_results(query_list, batch_size, max_tweets):

    # Error checking
    if not query_list:
        print("Please specify a search term")
        return False

    # Fetch all tweets from users in list, one by one
    all_tweets = get_all_tweets_from_search_queries(query_list, batch_size, max_tweets)

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

