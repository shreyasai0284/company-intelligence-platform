import zipfile
from pathlib import Path
root = Path('.')
zip_path = root / 'api-ingestion-update.zip'
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    handler = root / 'lambdas' / 'api-ingestion' / 'ingestion_handler.py'
    z.write(handler, handler.name)
    package_root = root / 'lambdas' / 'api-ingestion'
    for p in package_root.rglob('*'):
        if p.is_file() and p.name != 'ingestion_handler.py':
            rel = p.relative_to(package_root)
            z.write(p, rel)
print('zip_created', zip_path.exists(), zip_path.stat().st_size)
