import json
import time
import urllib.request

req = urllib.request.Request(
    'http://127.0.0.1:8000/invocations',
    data=json.dumps({'company': 'Contoso', 'country': 'US', 'tier': 'Standard'}).encode(),
    headers={'Content-Type': 'application/json'},
)
resp = urllib.request.urlopen(req, timeout=30)
run_id = json.loads(resp.read().decode())['run_id']
print(run_id)
for _ in range(20):
    time.sleep(3)
    status_req = urllib.request.Request(f'http://127.0.0.1:8000/status/{run_id}')
    status_resp = urllib.request.urlopen(status_req, timeout=30)
    data = json.loads(status_resp.read().decode())
    print('STATUS', data['status'])
    if data['status'] in {'COMPLETED', 'FAILED'}:
        print(json.dumps(data, indent=2))
        break
