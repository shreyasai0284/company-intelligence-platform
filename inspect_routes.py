import urllib.request
for path in ['/ping','/invocations','/invoke','/']:
    req = urllib.request.Request('http://127.0.0.1:8000' + path, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(path, resp.status, resp.read().decode())
    except Exception as exc:
        print(path, 'ERROR', exc)
