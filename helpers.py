import re, json

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
def get_parsed_users_from_raw_json(raw_user_json, debug_dir, keyword, today_str):

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
    with open(debug_dir + keyword + '_' + today_str+'_raw_users.json', 'w') as file:
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

#