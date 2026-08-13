import zipfile
from pathlib import Path
root = Path('.')
zip_path = root / 'engine-orchestrator-update.zip'
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    handler = root / 'lambdas' / 'engine-orchestrator' / 'orchestrator_handler.py'
    z.write(handler, handler.name)
    src_dir = root / 'agentcore' / 'src'
    for p in src_dir.rglob('*'):
        if p.is_file():
            z.write(p, Path('src') / p.relative_to(src_dir))
print('zip_created', zip_path.exists(), zip_path.stat().st_size)
