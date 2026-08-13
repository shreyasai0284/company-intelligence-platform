import zipfile
from pathlib import Path
root = Path('.')
zip_path = root / 'api-orchestrator-minimal.zip'
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(root / 'lambdas' / 'engine-orchestrator' / 'orchestrator_handler_minimal.py', 'orchestrator_handler_minimal.py')
    z.write(root / 'lambdas' / 'engine-orchestrator' / 'orchestrator_handler.py', 'orchestrator_handler.py')
    src_dir = root / 'agentcore' / 'src'
    for p in src_dir.rglob('*'):
        if p.is_file():
            z.write(p, Path('src') / p.relative_to(src_dir))
print('zip_created', zip_path.exists(), zip_path.stat().st_size)
