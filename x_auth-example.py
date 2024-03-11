
# Instructions:
# - Set up your Twitter Developer account here: https://developer.twitter.com/en/portal/dashboard
# - Make sure you have created a project with an app that has read and write permissions
# - Upgrade your project to basic level access ($100)
# - copy/paste this file and rename it to x_auth.py
# - Generate a bearer token for your app, and copy/paste it below
# - Generate API + access Tokens, and copy/paste them below


# TWITTER AUTH V2

# Needed for basic OAuth 2.0 App-Only authentication (for find_groups.py)
BEARER_TOKEN = "..."


# Needed for OAuth 2.0 with PKCE (authenticating as a user, for get_timeline.py)

# Essentially a user name and password, sometimes called the consumer_key and consumer_secret
API_KEY = "..." # (API key)
API_SECRET = "..." # (API secret key)

# Essentially the user you are making the request on behalf of
ACCESS_TOKEN = "..." # (Access token)
ACCESS_TOKEN_SECRET = "..." # (Access token secret)