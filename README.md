# stinpaste

Pastebin clone-ish in Flask

DEMO: https://devmaks.biz/


## required env
```
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
export GOOGLE_ANALYTICS_ID='G-XXXXXX'
```

### TODO 

- expiration - tests, allow weekly,monthly
- encryption - unique salt per user. store key per user indb
- toggle switch for encrypt toggle, currently a checkbox
- CSP headers
- systemd unit
- sqlite -> postgres
- icons/favicons/styling
- seperate/organize files to:
```
  app/
    __init__.py
    models.py
    views.py
    scheduler.py

```
