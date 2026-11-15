"""Create a deterministic public source bundle using the export allowlist."""
import hashlib
import argparse
import json
import os
import tempfile
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.export_public import FILE_PATHS, TREE_PATHS, inspect_contents, selected_contents

DIRECTORIES = sorted({name.split('/')[0] for name in (*TREE_PATHS, *FILE_PATHS) if '/' in name or name in TREE_PATHS})


def create_bundle(target, root=ROOT):
    """Snapshot inputs once, then atomically replace a completed local archive."""
    root, target = Path(root).resolve(), Path(target).resolve()
    for name in DIRECTORIES:
        if target.is_relative_to(root / name):
            raise ValueError("output must be outside bundled source directories (use dist/)")
    # Hash and write the same bytes even if an editor changes a source meanwhile.
    contents = selected_contents(root, strict=False)
    public_manifest = root / 'PUBLIC-MANIFEST.json'
    if public_manifest.is_file() and not public_manifest.is_symlink():
        contents['PUBLIC-MANIFEST.json'] = public_manifest.read_bytes()
    inspect_contents(contents)
    contents = dict(sorted(contents.items()))
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.'+target.name+'-', dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name, data in contents.items():
                info = zipfile.ZipInfo(name, date_time=(2026,10,12,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                bundle.writestr(info, data)
            info = zipfile.ZipInfo('BUNDLE-MANIFEST.json', date_time=(2026,10,12,0,0,0))
            bundle.writestr(info, json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        # Preserve the previous bytes only after the replacement is fully built.
        if target.exists():
            old = target.read_bytes()
            old_hash = hashlib.sha256(old).hexdigest()
            previous = target.with_name(target.stem+'-'+old_hash[:12]+target.suffix)
            if previous.exists() and previous.read_bytes() != old:
                raise ValueError('recovery archive name collision; existing files preserved')
            if not previous.exists():
                previous.write_bytes(old)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.sha256').write_text(digest+'  '+target.name+'\n')
    return {"path": str(target), "files": len(contents), "sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'dist/eiv-source.zip')
    args = parser.parse_args()
    result = create_bundle(args.output)
    print(f"Public source bundle: {result['path']} ({result['files']} files). No upload performed.")


if __name__ == '__main__':
    main()
