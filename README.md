# stinpaste

Pastebin clone-ish in Flask


## required env
```
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```

`export GOOGLE_ANALYTICS_ID='G-XXXXXX'`

## TODO 
expiration for pastes, tests, allow weekly,monthly, test scheduler for exp deletes
password/encryption for pastes - semi done, test more. 
CSP headers
add accessor-IP to logs
seperate/organize files to:
app/
  __init__.py
  models.py
  views.py
  scheduler.py

