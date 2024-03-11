import re, json, requests, datetime, time
from pathlib import Path

# For OAuth v2.0 User Context authentification
from x_auth import BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET


# ==============
# Setup folders
# ==============

# Ideal file structure = /reports/{date}/{keyword}-{date}_{num days}.csv
today_str = datetime.datetime.now().strftime("%d-%m-%Y")
base_dir = "reports/" + today_str + "/"
debug_dir = base_dir + "debug/"

def create_folders(debug_dir=debug_dir):
    print("Reports will be created in: /"+ base_dir)
    Path(debug_dir).mkdir(parents=True, exist_ok=True)


# =================
# HELPER FUNCTIONS
# =================

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

# Clean the data and assemble the user_list object
def get_parsed_users_from_raw_json(raw_user_json, debug_dir=debug_dir, debug_keyword="default", today_str=today_str):

    # We already have:

    # user = {
    #     username = user,
    #     mentioned_by_users = ["@" + tweet['username']],
    #     example_tweet = tweet['full_text']
    # }

    # We want to end up with:

    # user = {
    #     "name":               # TO ADD
    #     "username":           # (have)
    #     "profile_url":        # (to process)
    #     "description":        # TO ADD
    #     "location":           # TO ADD
    #     "url":                # TO ADD
    #     "verified":           # TO ADD
    #     "followers_count":    # TO ADD
    #     "listed_count":       # TO ADD
    #     "mentions_count":     # (to process)
    #     "example_tweet":      # (have)
    #     "priority":           # (to process)
    # }

    # Which means we need to return this dictionary:

    # user = {
    #     "id":                 # x[data][i][id]
    #     "username":           # x[data][i][username]
    #     "name":               # x[data][i][name]
    #     "description":        # x[data][i][description]
    #     "location":           # x[data][i][location]
    #     "url":                # if x[data][i][entities]:
                                    # x[data][i][entities][url][urls][expanded_url]
    #     "verified":           # x[data][i][verified]
    #     "followers_count":    # x[data][i][public_metrics][followers_count]
    #     "listed_count":       # x[data][i][public_metrics][listed_count]
    # }

    # Debug - save json list of tweets found
    with open(debug_dir + debug_keyword + '_' + today_str+'_raw_users.json', 'w') as file:
        json.dump(raw_user_json, file, indent=4)

    # set variables
    result_count = len(raw_user_json['data'])
    user_list = [[] for i in range(result_count)]

    # For each user in raw response
    for i in range(result_count):

        # Create a sanitised list of dictionaries that we can cross reference later
        user_list[i] = {}
        user_list[i]['id'] = raw_user_json['data'][i]['id']
        user_list[i]['username'] = raw_user_json['data'][i]['username'] # KEY
        user_list[i]['name'] = raw_user_json['data'][i]['name']
        user_list[i]['description'] = re.sub(r"\n|\r", " ", raw_user_json['data'][i]['description']) # sanitise
        # set user_list[i]['location']
        if 'location' in raw_user_json['data'][i]:
            user_list[i]['location'] = raw_user_json['data'][i]['location']
        else:
            user_list[i]['location'] = None
        # set user_list[i]['verified']
        if raw_user_json['data'][i]['verified']:
            user_list[i]['verified'] = 'Yes'
        else:
            user_list[i]['verified'] = 'No'
        user_list[i]['followers_count'] = raw_user_json['data'][i]['public_metrics']['followers_count']
        user_list[i]['listed_count'] = raw_user_json['data'][i]['public_metrics']['listed_count']
        # set user_list['url']
        if ('entities' in raw_user_json['data'][i]) and ('url' in raw_user_json['data'][i]['entities']) and ('urls' in raw_user_json['data'][i]['entities']['url']) and ('expanded_url' in raw_user_json['data'][i]['entities']['url']['urls'][0]):
            user_list[i]['url'] = raw_user_json['data'][i]['entities']['url']['urls'][0]['expanded_url']
        else:
            user_list[i]['url'] = " "

    return user_list

# Get next_token for pagination from the raw json response
def get_next_token_from_raw_json(raw_tweet_json):
    if 'next_token' in raw_tweet_json['meta']:
        next_token = raw_tweet_json['meta']['next_token']
        print("next_token: " + next_token) # debug
        return next_token

# Create batches from large lists for processing
def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]
    # USAGE
    # for x in batch(range(0, 10), 3):
    #     print x

# Pretty print follower count
def format_follower_count(num):
    if num >= 1000:
        return f"{num / 1000:.1f}k"
    else:
        return str((num // 100) * 100)
    # Examples
    # print(format_number(136833))  # Output: 136.8k
    # print(format_number(231))     # Output: 200

# Return users_mentioned from all_tweets
def return_users_mentioned_from_all_tweets(all_tweets):

    # FIND ALL MENTIONED USERS
    # Note: Now we're going to look at the tweet content and see which users have been mentioned, how many times

    users_mentioned = []
    for i, tweet in enumerate(all_tweets):
        if (i > 1) and (i % 100 == 0):
            print("...%d tweets processed so far out of %d (%s)" % (i, len(all_tweets), str(round(i / len(all_tweets) * 100)) + "%"))

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
    return users_mentioned

# Return user_data from users_mentioned
def get_user_data_for_users_mentioned(users_mentioned, max_users=100, debug_keyword="debug"):
    
    # GET USER DATA FOR MENTIONED USERS
    # Note: We now have a list of users mentioned in tweets (users_mentioned), but we don't know much about them - time to get information about who they are

    # First, let's sanitise the users_mentioned list to exclude users who don't match the correct regex pattern, and return only valid_users
    valid_regex_pattern = re.compile(r'^[A-Za-z0-9_]{1,15}$')
    valid_users = [user for user in users_mentioned if valid_regex_pattern.match(user['username'])]

    # Ideally, we just want to get the top mentioned users so we don't do unneccessary data lookups, so let's sort valid_users by most mentioned, and just return an amount defined by max_users
    valid_users.sort(key=lambda x: len(x["mentioned_by_users"]), reverse=True)

    user_data = []
    # we're using username as a search key to find the data - just get the most mentioned users for efficiency
    all_usernames = [u['username'] for u in valid_users[:max_users]]
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
            new_users = get_parsed_users_from_raw_json(response.json(), debug_keyword=debug_keyword)
            user_data.extend(new_users)
            print("Found %d users so far" % len(user_data))

        else:
            print("Failed to retrieve data:", response.status_code, response.text)
            # Abort new user lookup upon error
            print("Proceeding with the user data that's already been collected.")
            time.sleep(10)
            break

    # print('\nlen(user_data): ' + str(len(user_data))) # debug
    # print(user_data) # debug
    return valid_users, user_data

# Return user_table_headers and user_table_rows from valid_users and user_data lists
def create_user_table_from_user_data(valid_users, user_data, priority_keywords, max_users=100):

    # CONSTRUCT USER TABLE
    # Note: So now we have a list of users mentioned (valid_users), and we have some extra information about each user (user_data) - now we need to combine them to get something readable and useable

    # get list of keywords to prioritise
    priority_keywords_list = [x.strip() for x in priority_keywords.split(",")]

    user_table = []
    priority_user_table = []
    other_user_table = []
    # just export the most mentioned users
    for entry in valid_users[:max_users]:
        # locate index of user
        try:
            # Create an index for cross comparison of the valid_users list and the user_data list
            i = [i for i, dic in enumerate(user_data) if dic['username'] == entry["username"]][0]
            # Assemble a useful, understandable object of users that combines the lists together
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

    # Add users who match the priority keywords first
    priority_user_table.sort(key=lambda item:item['followers_count'], reverse=True)
    priority_user_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    user_table.extend(priority_user_table)

    # Then add any all users found
    other_user_table.sort(key=lambda item:item['followers_count'], reverse=True)
    other_user_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    user_table.extend(other_user_table)

    # Finally, return the data in the form of an exportable table
    user_table_headers = ["Quick Ref Org", "Quick Ref Twitter", "Quick Ref Bio", "Name", "Username", "Profile URL", "Description", "No. Mentions", "Location", "URL", "Verified", "Follower Count", "Listed Count", "Example Tweet", "Priority", "Notes"]
    user_table_rows = [list(x.values()) for x in user_table]
    
    return user_table_headers, user_table_rows

#