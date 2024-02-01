# build_twitter_list.py (Use Twitter Search to build initial list of mavens)

# import base
from __future__ import unicode_literals # support for emojis
import re
import csv
import time
import datetime
import json
# import twitter handers
import tweepy
from twitter_auth import API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
# import helper functions
from helpers import rate_limit_exceeded, batch
from tabulate import tabulate


# =================
# SETUP
# =================

# NB: great list for influencers:
# founder, chair, editor, author, journalist, writer, professor, chancellor, campaigner, TV presenter, broadcaster, trustee, ceo, chief exec, executive

# NB: great list for orgs:
# activis, campaigning for, group, charity

query = str(input("Enter search term to build list from: \n"))
priority_keywords = str(input("Enter a comma separated list of keywords to look for in user descriptions: \n"))
max_tweets = 12000 # 20000
from_days_ago = 28
log_article = str(input("Save an article link for future reference in the CSV? \n"))

# Next steps:
# - remove rate_limiting?
# - create permanent 'rejected' list
# - load existing users in lists, add new, and then save files
# - create 'interesting' list saved separately
# - limit users to UK location + export country with user data
# - possibly use TagDef to describe hashtags (https://rapidapi.com/snokleby/api/tagdef)

# ADD SEE RELATED USERS - SEARCH FORMAT = https://twitter.com/i/connect_people?user_id=1118291417129005058

# =================
# FUNCTIONS
# =================

def get_full_text(tweet):
    # if retweeted, return original text appended
    if hasattr(tweet, "retweeted_status"):
        rt = re.match(r"^(.*RT \@.+?: )", tweet.full_text)
        try:
            full_text = rt.group(0) + tweet.retweeted_status.full_text
            return full_text
        except AttributeError:
            return tweet.full_text
    else:
        return tweet.full_text

# GET ALL TWEETS - for list of screen names over a certain date range
# Twitter only allows access to a users most recent 3240 tweets with this method
def get_all_tweets_from_search_queries(query_list, max_tweets):

    # TWITTER AUTH
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    # Check API limits
    rate_counter = int(api.rate_limit_status()["resources"]["search"]["/search/tweets"]["remaining"])
    print(" ")
    print("%d API requests left this period for search_tweets" % rate_counter)

    # init vars
    tweet_data = []
    all_tweets_in_loop = [[] for i in range(len(query_list))]
    request_count = 0

    # start
    print(" ")
    print("Finding tweets from %d search terms in list" % len(query_list))

    # iterate through screen names
    for i, query in enumerate(query_list):

        # start
        print(" ")
        print("Finding tweets from search term '%s'..." % query)

        # Make initial request for most recent tweets (200 is the maximum allowed count)
        try:
            new_tweets = api.search(q=query, count=200, geocode="54.776350,-4.794210,600km", tweet_mode="extended")
            request_count += 1
        except tweepy.error.TweepError as e:
            print(" ")
            print("Received an error from Twitter. Waiting 30 seconds before retry. Error returned:", e)
            print(" ")
            time.sleep(30)
            continue

        # If tweets found
        if len(new_tweets) > 0:
            all_tweets_in_loop[i].extend(new_tweets)

            # save the id of the oldest tweet less one
            oldest = all_tweets_in_loop[i][-1].id - 1
            batch_start_days_ago = datetime.datetime.now() - all_tweets_in_loop[i][-1].created_at

            #keep grabbing tweets until there are no tweets left to grab
            if max_tweets:
                while (len(new_tweets) > 0) and (batch_start_days_ago.days < from_days_ago) and (len(all_tweets_in_loop[i]) < max_tweets):
                    print("...%s tweets downloaded so far (earliest %s)" % (len(all_tweets_in_loop[i]), all_tweets_in_loop[i][-1].created_at))

                    try:
                        new_tweets = api.search(q=query, count=200, geocode="54.776350,-4.794210,600km", tweet_mode="extended", max_id=oldest)
                        request_count += 1
                        all_tweets_in_loop[i].extend(new_tweets)
                        # update the id of the oldest tweet less one
                        oldest = all_tweets_in_loop[i][-1].id - 1
                        batch_start_days_ago = datetime.datetime.now() - all_tweets_in_loop[i][-1].created_at

                    except tweepy.error.TweepError as e:
                        print(" ")
                        print("Received an error from Twitter. Waiting 30 seconds before retry. Error returned:", e)
                        print(" ")
                        time.sleep(30)
                        continue
            else:
                while (len(new_tweets) > 0) and (batch_start_days_ago.days < from_days_ago):
                    print("...%s tweets downloaded so far (earliest %s)" % (len(all_tweets_in_loop[i]), all_tweets_in_loop[i][-1].created_at))

                    try:
                        new_tweets = api.search(q=query, count=200, geocode="54.776350,-4.794210,600km", tweet_mode="extended", max_id=oldest)
                        request_count += 1
                        all_tweets_in_loop[i].extend(new_tweets)
                        # update the id of the oldest tweet less one
                        oldest = all_tweets_in_loop[i][-1].id - 1
                        batch_start_days_ago = datetime.datetime.now() - all_tweets_in_loop[i][-1].created_at

                    except tweepy.error.TweepError as e:
                        print(" ")
                        print("Received an error from Twitter. Waiting 30 seconds before retry. Error returned:", e)
                        print(" ")
                        time.sleep(30)
                        continue

            # Filter list by tweets from date limit
            tweets_in_range = list(filter(lambda x: (datetime.datetime.now() - x.created_at).days < from_days_ago, all_tweets_in_loop[i]))

            if len(tweets_in_range) > 0:
                print("Found %d tweets from term '%s' over the last %d days. Earliest one found %d days ago (%s)" % (len(tweets_in_range), query, from_days_ago, (datetime.datetime.now() - tweets_in_range[-1].created_at).days, tweets_in_range[-1].created_at))
                tweet_data.extend(tweets_in_range)
            else:
                print("Found 0 tweets from term '%s' over the last %d days." % (query, from_days_ago))
        else:
            print("Found 0 tweets from term '%s' over the last %d days." % (query, from_days_ago))

    return tweet_data



def get_search_results(query_list, max_tweets):

    # Error checking
    if len(query_list) == 0:
        print("Please specify a search term")
        return False

    # TWITTER AUTH
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)

    print(" ")
    print("Searching tweets...")

    # Fetch all tweets from users in list, one by one
    all_tweets = get_all_tweets_from_search_queries(query_list, max_tweets)

    # ===========================
    # PROCESS TWEETS
    # ===========================

    print(" ")
    tweet_count = len(all_tweets)
    print("Processing %d tweets found in list..." % tweet_count)

    # Process tweet_data
    users_mentioned = []
    hashtags_mentioned = []
    for i, tweet in enumerate(all_tweets):
        if (i > 1) and (i % 100 == 0):
            print("...%d tweets processed so far out of %d (%s)" % (i, tweet_count, str(round(i / tweet_count * 100)) + "%"))

        # get full text of tweet (untruncated)
        full_text = get_full_text(tweet)

        # process user mentions
        users_mentioned_in_tweet = re.findall(r'@([\w]+)', full_text)

        for user in users_mentioned_in_tweet:
            # if first entry add new entry, else get index of current user in users_mentioned list, and add new name to list
            if not [x for x in users_mentioned if x['screen_name'].upper() == user.upper()]:
                users_mentioned.append(dict(
                    screen_name = user, # @@@ NOT including '@' so we can use it to search
                    user_list = ["@" + tweet.user.screen_name],
                    example_tweets = full_text # @@@ not a list now
                ))
            else:
                i = [i for i, dic in enumerate(users_mentioned) if dic['screen_name'].upper() == user.upper()][0]
                if ("@" + tweet.user.screen_name) not in users_mentioned[i]["user_list"]:
                    users_mentioned[i]["user_list"].append("@" + tweet.user.screen_name)
                    # users_mentioned[i]["example_tweets"].append(tweet.text)

        # process hashtag mentions
        hashtags_mentioned_in_tweet = re.findall(r'#([\w]+)', full_text)
        for hashtag in hashtags_mentioned_in_tweet:
            # if first entry add new entry, else get index of current user in users_mentioned list, and add new name to list
            if not [x for x in hashtags_mentioned if x['term'].upper() == "#" + hashtag.upper()]:
                hashtags_mentioned.append(dict(
                    term = "#" + hashtag,
                    user_list = ["@" + tweet.user.screen_name],
                    example_tweets = full_text
                ))
            else:
                i = [i for i, dic in enumerate(hashtags_mentioned) if dic['term'].upper() == "#" + hashtag.upper()][0]
                if ("@" + tweet.user.screen_name) not in hashtags_mentioned[i]["user_list"]:
                    hashtags_mentioned[i]["user_list"].append("@" + tweet.user.screen_name)
                    # hashtags_mentioned[i]["example_tweets"].append(tweet.text)


    # GET USER OBJECTS FROM TWITTER

    print("looking up %d users" % len(users_mentioned))
    user_data = []
    usernames = [u['screen_name'] for u in users_mentioned]

    for batch_users in batch(usernames, 100):
        try:
            new_users = api.lookup_users(screen_names=batch_users)
            user_data.extend(new_users)
            print("Found %d users so far" % len(user_data))
        except tweepy.error.TweepError as e:
            print(" ")
            print("Received an error from Twitter. Waiting 30 seconds before retry. Error returned:", e)
            print(" ")
            time.sleep(30)
            continue
        except tweepy.RateLimitError as e:
            print(" ")
            print("Rate limit exceeded.", e)
            rate_limit_exceeded(15, "users/lookup")
            # try again
            new_users = api.lookup_users(screen_names=batch_users)
            user_data.extend(new_users)
            print("Found %d users so far" % len(user_data))

    # user_data = api.lookup_users(screen_names=usernames)

    # print(json.dumps(user_data[0]._json, indent=4))

    # testing search
    # i = [i for i, dic in enumerate(user_data) if dic.screen_name == "tribunemagazine"][0]
    # print(i)
    # print(user_data[i].name)
    # print(user_data[i].description)
    # print(user_data[i].followers_count)
    # print(user_data[i].entities["url"]["urls"][0]["expanded_url"])

    # testing search for specific user
    # i = [i for i, dic in enumerate(users_mentioned) if dic["screen_name"] == "ne_grant"][0]
    # print(i)
    # search_user = api.get_user("ne_grant")
    # print(search_user.name)

    # quit()

    # ===========================
    # DISPLAY TWEETS
    # ===========================

    # get list of keywords to prioritise
    priority_keywords_list = [x.strip() for x in priority_keywords.split(",")]
    # for query in query_list:
    #     priority_keywords_list.append(query)

    # CONSTRUCT USER TABLE

    user_table = []
    priority_user_table = []
    other_user_table = []
    for entry in users_mentioned:
        # locate index of user
        try:
            i = [i for i, dic in enumerate(user_data) if dic.screen_name == entry["screen_name"]][0]
            line_break = ', '
            item = {
                "name": user_data[i].name,
                "screen_name": "@" + entry["screen_name"], # @@@ adding the '@' now after we've embellished the data
                "user_url": "https://www.twitter.com/" + entry["screen_name"], # added
                "description": re.sub(r"\n|\r", " ", user_data[i].description),
                "followers_count": user_data[i].followers_count,
                "mentions_count": len(entry["user_list"]),
                "user_list": line_break.join(entry["user_list"][:5]) + ', ...',
                "example_tweets": re.sub(r"\n|\r", " ", entry["example_tweets"]),
            }
            if "url" in user_data[i].entities:
                item["url"] = str(user_data[i].entities["url"]["urls"][0]["expanded_url"])
            else:
                item["url"] = " "
            # get interesting profiles
            if any(substring.upper() in item["description"].upper() for substring in priority_keywords_list):
                item["priority"] = "yes"
                priority_user_table.append(item)
            elif (item["followers_count"] > 500) and (item["mentions_count"] > 3):
                # get other profiles
                item["priority"] = "no"
                other_user_table.append(item)
        except IndexError as e:
            print("tried to find user '%s', but they may have been suspended or deleted. Error reported: %s" % (entry["screen_name"], e))

    priority_user_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    user_table.extend(priority_user_table)
    other_user_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    user_table.extend(other_user_table)
    user_table_headers = ["Name","Screen Name", "User URL", "Description", "Follower Count", "No. Mentions", "Users Who Tweeted This", "Example Tweet", "URL", "Priority", "Notes"]
    user_table_rows = [list(x.values()) for x in user_table]
    # print(tabulate(user_table_rows[:5], user_table_headers, tablefmt="psql"))

    # CONSTRUCT HASHTAG TABLE

    hashtag_table = []
    priority_hashtag_table = []
    other_hashtag_table = []
    for entry in hashtags_mentioned:
        line_break = ', '
        item = {
            "term": entry["term"],
            "mentions_count": len(entry["user_list"]),
            "user_list": line_break.join(entry["user_list"][:5]) + ', ...',
            "example_tweets": re.sub(r"\n|\r", " ", entry["example_tweets"]),
        }
        # get interesting hashtags
        if any(substring.upper() in item["term"].upper() for substring in priority_keywords_list):
            item["priority"] = "yes"
            priority_hashtag_table.append(item)
        elif item["mentions_count"] > 3:
            # get other hashtags
            item["priority"] = "no"
            other_hashtag_table.append(item)

    priority_hashtag_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    hashtag_table.extend(priority_hashtag_table)
    other_hashtag_table.sort(key=lambda item:item['mentions_count'], reverse=True)
    hashtag_table.extend(other_hashtag_table)
    hashtag_table_headers = ["Hashtag", "No. Mentions", "Users Who Tweeted This", "Example Tweet", "Priority"]
    hashtag_table_rows = [list(x.values()) for x in hashtag_table]
    # print(tabulate(hashtag_table_rows, hashtag_table_headers, tablefmt="psql"))

    print(" ")
    print("Saving full reports...")
    print(" ")

    # WRITE TO RESULTS FILE

    today_str = datetime.datetime.now().strftime("%d-%m-%Y")
    with open('twitter-files/reports/'+query_list[0]+'-report-'+ today_str + "_" + str(from_days_ago) + 'days.txt', 'w', encoding='utf8', errors='ignore') as f:
        seperator = ', '
        f.write("Search Terms: %s\n  >>  Av. Tweet Volume: %d / day (%d tweets total measured over %d days)\n\n" % (seperator.join(query_list), (len(all_tweets) / len(query_list) / from_days_ago), len(all_tweets), from_days_ago)) # @@@ total tweets / terms / day range
        f.write("--- Results ---\n")
        f.write(tabulate(user_table_rows, user_table_headers, tablefmt="psql"))
        f.write("\n\n")
        f.write(tabulate(hashtag_table_rows, hashtag_table_headers, tablefmt="psql"))
        print("Saved list to 'twitter-files/reports/%s-report-%s.txt'" % (query_list[0], today_str))

    # WRITE TO CSV

    with open('twitter-files/reports/'+query_list[0]+'-report-'+ today_str + "_" + str(from_days_ago) + 'days.csv', 'w', newline='', encoding='utf-8-sig', errors='ignore') as csvfile:
        csv_write = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        seperator = ', '
        csv_write.writerow([("Search Terms: %s" % seperator.join(query_list))])
        csv_write.writerow([("Priority Keywords: %s" % seperator.join(priority_keywords_list))])
        csv_write.writerow([("Av. Tweet Volume: %d / day (%d tweets total measured over %d days)" % ((len(all_tweets) / len(query_list) / from_days_ago), len(all_tweets), from_days_ago))])
        if (log_article) and (len(log_article) > 3):
            csv_write.writerow(["See:", log_article])
        csv_write.writerow([" "])

        csv_write.writerow(user_table_headers)
        for row in user_table_rows:
            csv_write.writerow(row)

        csv_write.writerow([" "])

        csv_write.writerow(hashtag_table_headers)
        for row in hashtag_table_rows:
            csv_write.writerow(row)
        print("Saved list to 'twitter-files/reports/%s-report-%s.csv'" % (query_list[0], today_str))

        # OPEN FILE AFTERWARDS
        print(" ")
        open_this_file = input("Do you want to open the CSV report now? (y/n): ")
        if open_this_file == 'y':
            import os, subprocess
            curr_report_path = (os.getcwd() + "\\twitter-files\\reports\\%s-report-%s_%sdays.csv" % (query_list[0], today_str, str(from_days_ago)))
            # print("Opening this directory: \n" + curr_report_path)
            subprocess.Popen(f'explorer /select, {curr_report_path}')
        else:
            pass

    # ===========================
    # FILTER BEFORE SAVING RESULTS
    # ===========================

    # CREATE A FILTERED LIST

    print(" ")
    print("Let's create a filtered list. Selecting from %d unique users and %d unique hashtags..." % (len(user_table), len(hashtag_table)))

    # BUILD MEANINGFUL LIST TO USE LATER

    # @@@ ADD REJECTED_LIST AND READ FROM FILE, THEN APPEND TO REJECTED LIST AFTERWARDS

    saved_users = []
    for i, entry in enumerate(user_table):
        print(" ")
        print("===========================================")
        print(" ")
        print("(%d) %s - %s. %s. [%s] {followers: %d}" % (entry["mentions_count"], entry["screen_name"], entry["name"], entry["description"], entry["url"], entry["followers_count"]))
        print(" ")
        save_this_entry = input("[%d left] -----> Do you wish to save '%s' to the '%s' list? (y/n/end): " % (len(user_table)-i, entry["screen_name"], query_list[0]))
        if save_this_entry == 'y':
            saved_users.append(entry)
        elif save_this_entry == 'n':
            continue
        elif save_this_entry == 'end':
            break
            # @@@ ADD 'NEVER' TO REJECTED LIST?
        else:
            print("Input not recognised, skipping entry")
            continue

    print(" ")
    print("Saved %d users in the '%s' list:" % (len(saved_users), query_list[0]))
    for user in saved_users:
        print(user["screen_name"])

    print(" ")
    saved_hashtags = []
    for i, entry in enumerate(hashtag_table):
        save_this_entry = input("[%d left] Do you wish to save '%s' (mentions: %d) to the '%s' list? (y/n/end): " % (len(hashtag_table)-i, entry["term"], entry["mentions_count"], query_list[0]))

        if save_this_entry == 'y':
            saved_hashtags.append(entry)
        elif save_this_entry == 'n':
            continue
        elif save_this_entry == 'end':
            break
        else:
            print("Input not recognised, skipping entry")
            continue

    print(" ")
    print("Saved %d hashtags in the '%s' list:" % (len(saved_hashtags), query_list[0]))
    for hashtag in saved_hashtags:
        print(hashtag["term"])


    # ===========================
    # SAVED FILTERED LIST
    # ===========================

    # SOURCE TXT FILE LOOKS LIKE THIS
    # --- Orgs ---
    # @user - description [URL]
    # --- Hashtags ---
    # #Hashtag
    # #Hashtag


    print(" ")
    print("Saving filtered lists...")
    print(" ")

    # WRITE TO RESULTS FILE

    today_str = datetime.datetime.now().strftime("%d-%m-%Y")
    with open('twitter-files/lists/'+query_list[0]+'-saved-list-'+ today_str +'.txt', 'w', encoding='utf8', errors='ignore') as f:
        f.write("--- Orgs ---\n")
        for entry in saved_users:
            f.write("%s - %s. %s. [%s] {followers: %d}\n" % (entry["screen_name"], entry["name"], entry["description"], entry["url"], entry["followers_count"]))
        f.write("\n\n")
        f.write("--- Hashtags ---\n")
        for entry in saved_hashtags:
            f.write("%s\n" % entry["term"])
        print("Saved filtered list to 'twitter-files/lists/%s-saved-list-%s.txt'" % (query_list[0], today_str))

    # WRITE TO CSV

    with open('twitter-files/lists/'+query_list[0]+'-saved-list-'+ today_str +'.csv', 'w', newline='', encoding='utf-8-sig', errors='ignore') as csvfile:
        csv_write = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_write.writerow(["Screen Name", "Full Name", "Description", "Url", "Follower count"])
        for entry in saved_users:
            csv_write.writerow([entry["screen_name"], entry["name"], entry["description"], entry["url"], entry["followers_count"]])
        print("Saved filtered list to 'twitter-files/lists/%s-saved-list-%s.csv'" % (query_list[0], today_str))

# =================
# TESTING
# =================

query_list = [x.strip() for x in query.split(",")]
get_search_results(query_list, max_tweets)
