import clienttask
import settings
import json
import urllib.request

if __name__ == '__main__':
    url = settings.DST_URL
    report = clienttask.alltasks()
    data = dict(
        client_id=settings.CLIENT_ID,
        client_secret=settings.CLIENT_SECRET,
        report=json.dumps(report),
    )
    request = urllib.request.urlopen(url, urllib.parse.urlencode(data).encode('utf-8'))
    assert request.code == 200
    content = request.read().decode('utf-8')
    content = json.loads(content)
    print(content)
