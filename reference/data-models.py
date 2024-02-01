# ===================================
# CONSTRUCTING THE FIRST DATA REQUEST
# ===================================

# Here's how we construct a basic request to the Twitter API
# Note: it requires having 'basic' access to Twitter API (currently $100/month), 
# with a compatible app set up with read and write priviledges

import requests
url = 'https://api.twitter.com/2/tweets/search/recent'
headers = {
    'Authorization': 'Bearer ' # + YOUR_BEARER_TOKEN
}
r = requests.get(url, headers=headers)


# =====================================
# CUSTOMISING THE TWEET DATA RESPONSE
# =====================================

# Configure optional extra forms - otherwise by default, just tweet and id are returned.

# FULL SET OF ADDITIONAL FIELDS
tweet_fields = "created_at,author_id,conversation_id,public_metrics,text"
expansions = "author_id,referenced_tweets.id,in_reply_to_user_id,attachments.media_keys"
user_fields = "name,username,location,verified"
media_fields = "url,preview_image_url,type"

query_string = (
    f'?query={quote(query)}'
    f'&max_results={batch_size}'
    f'&tweet.fields={tweet_fields}'
    f'&expansions={expansions}'
    f'&user.fields={user_fields}'
    f'&media.fields={media_fields}'
)
full_url = url + query_string
r = requests.get(full_url, headers=headers)



# ===============================
# DATA MODEL FOR TWEET RESPONSE
# ===============================

# This is an example of the raw data we get back from twitter API v2

{
  "data": [
    {
      "text": "Looking to get started with the Twitter API but new to APIs in general? https://t.co/GrtBOXyHmB",
      "author_id": "2244994945",
      "id": "1373001119480344583",
      "edit_history_tweet_ids": [
        "1373001119480344583"
      ],
      "lang": "en",
      "conversation_id": "1373001119480344583",
      "created_at": "2021-03-19T19:59:10.000Z"
    }
  ],
  "includes": {
    "users": [
      {
        "id": "2244994945",
        "entities": {
          "url": {
            "urls": [
              {
                "start": 0,
                "end": 23,
                "url": "https://t.co/3ZX3TNiZCY",
                "expanded_url": "https://developer.twitter.com/en/community",
                "display_url": "developer.twitter.com/en/community"
              }
            ]
          },
          "description": {
            "hashtags": [
              {
                "start": 17,
                "end": 28,
                "tag": "TwitterDev"
              },
              {
                "start": 105,
                "end": 116,
                "tag": "TwitterAPI"
              }
            ]
          }
        },
        "created_at": "2013-12-14T04:35:55.000Z",
        "username": "TwitterDev",
        "name": "Twitter Dev"
      }
    ]
  },
  "meta": {
    "newest_id": "1373001119480344583",
    "oldest_id": "1373001119480344583",
    "result_count": 1
  }
}


# =================
# IDEAL DATA MODEL
# =================

# We to transform the data so it's more useable

tweet = {
    id: 1752666704214126628,
        # x[data][id]
    name: 'Agata',
        # x[includes][users][name] 
            # where x[includes][users][id] == x[data][author_id]
    username: 'Agata40038925',
        # x[includes][users][username] 
            # where x[includes][users][id] == x[data][author_id]
    full_text: 'RT @jakarinpuribhat: HELLO SINGAPORE \u2764\ufe0f https://t.co/NkneFzy6Bs',
        # x[data][text]
        # if x[data][referenced_tweets]
            # + "RE:" 
            # + x[includes][tweets][text]
                # where x[data][referenced_tweets][id] == x[includes][tweets][id]
    created_at: '2024-01-31T12:14:39.000Z'
        # x[data][created_at]
}
next_token = 'b26v89c19zqg8o3fr5qdmbh1n7ci9j26suor6iht0pda5'
    # x[meta][next_token]