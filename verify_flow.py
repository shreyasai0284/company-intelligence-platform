import urllib.request
import urllib.error
import json

base = 'https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod'

print('Submitting ingest request...')
payload = json.dumps({'company': 'DemoCorp', 'country': 'US', 'tier': 'Standard'}).encode('utf-8')
req = urllib.request.Request(base + '/ingest', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
run_id = None
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print('INGEST STATUS', r.status)
        body = json.loads(r.read().decode())
        print('RESPONSE', body)
        run_id = body.get('run_id')
except urllib.error.HTTPError as e:
    print('INGEST_HTTP_ERROR', e.code, e.reason)
    try:
        print(e.read().decode())
    except Exception:
        pass
except Exception as e:
    print('INGEST_ERROR', type(e).__name__, e)

if run_id:
    print('Checking status for run_id', run_id)
    req2 = urllib.request.Request(base + f'/status/{run_id}', method='GET')
    try:
        with urllib.request.urlopen(req2, timeout=30) as r:
            print('STATUS GET', r.status)
            print('STATUS RESPONSE', json.loads(r.read().decode()))
    except urllib.error.HTTPError as e:
        print('STATUS_HTTP_ERROR', e.code, e.reason)
        try:
            print(e.read().decode())
        except Exception:
            pass
    except Exception as e:
        print('STATUS_ERROR', type(e).__name__, e)
else:
    print('No run_id returned; cannot check status.')
