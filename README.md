# stinpaste

Pastebin clone-ish in Flask


## required env vars

`export GOOGLE_ANALYTICS_ID='G-XXXXXX'`

## TODO 
expiration for pastes, tests, allow weekly,monthly, test scheduler for exp deletes
password/encryption for pastes - semi done, test more. 
CSP headers
seperate/organize files to:
app/
  __init__.py
  models.py
  views.py
  scheduler.py