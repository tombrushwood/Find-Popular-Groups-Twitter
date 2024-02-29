# ==========================================================
# IMPORTANT: 
# THIS USES THE OLD V1.1 END POINT WHICH IS NO LONGER SUPPORTED.
# ==========================================================

print("Aborting.")
quit()

# import base
from __future__ import unicode_literals # support for emojis
import re
import csv
import time
import json
import math
# import twitter handlers
import tweepy
from twitter_auth import API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET



# =================
# SETUP
# =================

export_to_file_path = "twitter-files/twitter-followers/" # + twitter_handle + "-followers.csv"
max_results = 150000 # 200k ... 100k = 8hrs 20mins
output_limit = 5000 # 25k
print("max_results = %s" % max_results)
print("output_limit = %s" % output_limit)
print(" ")
query = str(input("Enter comma separated list of usernames to build lists from: \n"))

# SET CATEGORIES TO LOOK FOR

# journalists: journalist, columnist, editor, correspondent, reporter
journalist_keywords_list = "journalist, columnist, editor, correspondent, reporter"
journalist_keywords = [x.strip() for x in journalist_keywords_list.split(",")]

# authors: author, writer, novelist, screenwriter, co-author
author_keywords_list = "author, writer, novelist, screenwriter, co-author"
author_keywords = [x.strip() for x in author_keywords_list.split(",")]

# celebs / personalities: actress, actor, presenter, broadcaster, comedian
celeb_keywords_list = "actress, actor, presenter, broadcaster, comedian"
celeb_keywords = [x.strip() for x in celeb_keywords_list.split(",")]

# MPs / government leaders: former leader, MP for, member of parliament, minister of, MSP for, Senedd, leader of, mayor of, House of Lords, @UKHouseofLords
mp_keywords_list = "former leader, MP for, member of parliament, minister of, MSP for, Senedd, leader of, mayor of, House of Lords, @UKHouseofLords"
mp_keywords = [x.strip() for x in mp_keywords_list.split(",")]

# entrepreneurs and execs: founder, cofounder, co-chair, chairman, chair of, CEO, creator of, managing director, entrepreneur, director, president of, CIO, CMO, CTO, non exec
exec_keywords_list = "founder, cofounder, co-chair, chairman, chair of, CEO, creator of, managing director, entrepreneur, director, president of, CIO, CMO, CTO, non exec"
exec_keywords = [x.strip() for x in exec_keywords_list.split(",")]

# trustees: fellow, patron, trustee, NED, Ambassador,
trustee_keywords_list = "fellow, patron, trustee, NED, ambassador"
trustee_keywords = [x.strip() for x in trustee_keywords_list.split(",")]

# activists: campaign manager, senior advisor, activist, campaigner
activist_keywords_list = "campaign manager, senior advisor, activist, campaigner"
activist_keywords = [x.strip() for x in activist_keywords_list.split(",")]

# lower level media: host of, podcaster,
other_media_keywords_list = "host of, podcaster"
other_media_keywords = [x.strip() for x in other_media_keywords_list.split(",")]

# other: investor, professor, keynote speaker
other_keywords_list = "investor, professor, keynote speaker"
other_keywords = [x.strip() for x in other_keywords_list.split(",")]


# =================
# FUNCTIONS
# =================

# GET FOLLOWER COUNT
def get_following_list(handle_list):
    print(" ")
    print("Finding Twitter Follower Counts...")

    # TWITTER AUTH
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    # Check API limits
    rate_counter = int(api.rate_limit_status()["resources"]["followers"]["/followers/list"]["remaining"])
    print(" ")
    print("%d API requests left this period for followers_list" % rate_counter)

    # start
    print(" ")
    print("Finding Twitter follower counts from %d search terms in list" % len(handle_list))

    # iterate through screen names
    for twitter_handle in handle_list:
        print(' ')
        print('Processing: ', twitter_handle)

        # Use Twitter API to get follower counts
        user = api.get_user(twitter_handle)
        print("Follower count: ", user.followers_count)

        # Calc time to process
        ttp_batches = user.followers_count / 3000
        ttp_time = (ttp_batches * 15) / 60
        ttp_hours = int(ttp_time)
        ttp_minutes = (ttp_time * 60) % 60
        print("This should take around %d hours %d mins to process." % (ttp_hours, ttp_minutes))
        print(' ')

        followers = []
        try:
            for page in tweepy.Cursor(api.followers, screen_name=twitter_handle, wait_on_rate_limit=True, count=200, skip_status=1).pages():
                followers.extend(page)
                print("Found %d followers so far out of %d (%s)" % (len(followers), user.followers_count, str(round(len(followers) / user.followers_count * 100)) + "%"))

                if len(followers) > max_results:
                    print(" ")
                    print("Max result limit reached. Ending.")
                    break

        except tweepy.error.TweepError as e:
            print(" ")
            print("Received an error from Twitter. Waiting 30 seconds before retry. Error returned:", e)
            print(" ")
            time.sleep(30)
            continue


        # CONSTRUCT USER TABLE

        all_users_table = []

        for follower in followers:
            # construct formatted user obj then append to table
            item = {
                "name": follower.name,
                "screen_name":  "@" + follower.screen_name,
                "user_url": "https://www.twitter.com/" + follower.screen_name, # added
                "description": re.sub(r"\n|\r", " ", follower.description),
                "followers_count": follower.followers_count,
                "friends_count": follower.friends_count,
                "listed_count": follower.listed_count,
                "url": " ",
                "type_journalist": " ",
                "type_author": " ",
                "type_celeb": " ",
                "type_mp": " ",
                "type_exec": " ",
                "type_trustee": " ",
                "type_activist": " ",
                "type_other_media": " ",
                "type_other": " "
            }
            # add url
            if "url" in follower.entities:
                item["url"] = str(follower._json["entities"]["url"]["urls"][0]["expanded_url"])
            else:
                item["url"] = " "
            # add categories
            if any(substring.upper() in item["description"].upper() for substring in journalist_keywords):
                item["type_journalist"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in author_keywords):
                item["type_author"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in celeb_keywords):
                item["type_celeb"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in mp_keywords):
                item["type_mp"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in exec_keywords):
                item["type_exec"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in trustee_keywords):
                item["type_trustee"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in activist_keywords):
                item["type_activist"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in other_media_keywords):
                item["type_other_media"] = "yes"
            if any(substring.upper() in item["description"].upper() for substring in other_keywords):
                item["type_other"] = "yes"

            all_users_table.append(item)


        # CONSTRUCT RESULTS TABLE

        all_users_table.sort(key=lambda item:item['followers_count'], reverse=True)
        # all_users_table.sort(key=lambda item:item['listed_count'], reverse=True)
        user_table_headers = ["Name", "Screen Name", "User URL", "Description", "Follower Count", "Following Count", "Public List Count", "URL", "AutoType: Journalist", "AutoType: Author", "AutoType: Celeb / Personality", "AutoType: MP / Government Leader", "AutoType: Entrepreneur / Exec", "AutoType: Trustee", "AutoType: Activist", "AutoType: Lower Level Media", "AutoType: Other"]
        user_table_rows = [list(x.values()) for x in all_users_table]

        # WRITE TO CSV
        # In format utf-8-sig to support emojis

        with open(export_to_file_path + twitter_handle + "-followers.csv", 'w', newline='', encoding='utf-8-sig', errors='ignore') as csvfile:
            csv_write = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            csv_write.writerow([("Username: %s (Follower Count: %d)" % (twitter_handle, user.followers_count))])
            if output_limit < user.followers_count:
                csv_write.writerow([("Showing top %s most influential followers." % output_limit)])
            else:
                csv_write.writerow(["Showing all followers, ranked by most influential."])
            csv_write.writerow([" "])

            csv_write.writerow(user_table_headers)
            for i, row in zip(range(output_limit), user_table_rows):
                csv_write.writerow(row)

        print(" ")
        print("Saved CSV of followers to '%s%s-followers.csv" % (export_to_file_path, twitter_handle))

    # OPEN FILE AFTERWARDS
    print(" ")
    open_this_file = input("Finished. Do you want to open the reports now? (y/n): ")
    if open_this_file == 'y':
        import os, subprocess
        curr_report_path = os.getcwd() + "\\twitter-files\\twitter-followers\\"
        # print("Opening this directory: \n" + curr_report_path)
        subprocess.Popen(f'explorer /select, {curr_report_path}')
    else:
        pass

# =================
# EXECUTE
# =================

handle_list = [x.strip() for x in query.split(",")]
get_following_list(handle_list)
