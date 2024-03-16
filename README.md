# stinpaste

Pastebin clone-ish in Flask

DEMO: https://devmaks.biz/


## required env
```
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```

### TODO 

- expiration - tests, allow weekly,monthly
- encryption - unique salt per user. store key per user indb
- login - anonymous and registered user
- toggle switch for encrypt toggle, currently a checkbox
- CSP headers
- systemd unit
- sqlite -> postgres
- styling
- seperate/organize files to:
```
  app/
    __init__.py
    models.py
    views.py
    scheduler.py

```
