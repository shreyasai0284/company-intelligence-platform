import json
import urllib.request

base = 'https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod'
payload = json.dumps({'company': 'apple', 'country': 'United States', 'tier': 'Standard'}).encode()
req = urllib.request.Request(
    base + '/ingest',
    data=payload,
    headers={'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=30) as resp:
    body = resp.read().decode()
    print('INGEST', resp.status, body)
    data = json.loads(body)
    run_id = data['run_id']

status_req = urllib.request.Request(base + '/status/' + run_id, method='GET')
with urllib.request.urlopen(status_req, timeout=30) as resp2:
    print('STATUS', resp2.status, resp2.read().decode())
