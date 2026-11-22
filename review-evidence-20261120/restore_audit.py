"""Diagnose restored filenames and bytes without modifying the tree or its verifier."""
import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def run(root):
    manifest_path = root / "__migration_manifest__.json"
    manifest = json.loads(manifest_path.read_text())
    expected = {row["path"]: row for row in manifest["files"]}
    actual, links, dirs, ignored = set(), [], set(), []
    for folder, subdirs, filenames in os.walk(root, followlinks=False):
        for name in [*subdirs, *filenames]:
            path = Path(folder) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                links.append(relative)
            elif path.is_dir():
                dirs.add(relative)
            elif name == ".DS_Store":
                ignored.append(relative)
            elif path != manifest_path:
                actual.add(relative)
    normalize = lambda name: unicodedata.normalize("NFC", name)
    from_manifest = {normalize(s): s for s in expected}
    from_disk = {normalize(s): s for s in actual}
    if len(from_manifest) != len(expected) or len(from_disk) != len(actual):
        raise ValueError("Normalized filename collision, refuse to pair files")
    common = from_manifest.keys() & from_disk.keys()
    changed = [s for s in sorted(common)
               if digest(root / from_disk[s]) != expected[from_manifest[s]]["sha256"]]
    return dict(manifest_sha256=digest(manifest_path), manifest_files=len(expected),
                disk_files=len(actual), raw_missing_count=len(expected.keys() - actual),
                raw_extra_count=len(actual - expected.keys()),
                normalized_unique_pairs=len(common),
                normalization_only_names=sum(from_disk[s] != from_manifest[s] for s in common),
                missing=sorted(from_manifest.keys() - from_disk.keys()),
                extra=sorted(from_disk.keys() - from_manifest.keys()), changed_bytes=changed,
                dirs_missing=sorted(set(manifest["directories"]) - dirs),
                dirs_extra=sorted(dirs - set(manifest["directories"])),
                symlinks=sorted(links), ignored=sorted(ignored))


if __name__ == "__main__":
    print(json.dumps(run(Path(sys.argv[1]).resolve()), ensure_ascii=False, indent=2))
