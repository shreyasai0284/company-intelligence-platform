import urllib.request
import urllib.error

url = 'https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/ingest'
req = urllib.request.Request(
    url,
    method='OPTIONS',
    headers={
        'Origin': 'http://cip-frontend-704134886191-ap-south-1.s3-website.ap-south-1.amazonaws.com',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type',
    },
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        print('STATUS', resp.status)
        print('HEADERS')
        for h, v in resp.getheaders():
            if h.lower().startswith('access-control'):
                print(h + ':', v)
except urllib.error.HTTPError as e:
    print('HTTP ERROR', e.code)
    print(e.read().decode())
except Exception as e:
    print('ERROR', type(e).__name__, e)
