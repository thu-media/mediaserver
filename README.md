# mediaserver

Thu meida server list

Simplified from [cgserver](https://github.com/yuantailing/cgserver).

Remove most services except `server list`. Remove user control system.

## Usage

### Server-side

```shell
pip3 install -r requirements.txt
cp mediaserver/settings.py.sample mediaserver/settings.py
cp serverlist/scripts/add_clients.py.sample serverlist/scripts/add_clients.py
```

Then

```shell
python3 manage.py migrate
python3 manage.py runscript add_clients
python3 manage.py runserver
```

### Client-side

```shell
pip3 install -r requirements.txt
cp settings.py.sample settings.py
```

Update crontab, for example:

> */15 * * * * python3 some-path/client-side/report.py
