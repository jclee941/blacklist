import hashlib
import os
from pathlib import Path
import re
import subprocess
import textwrap
import zipfile


def test_release_zip_preserves_signed_installation_payload(tmp_path: Path) -> None:
    # Given: the signing job has produced a bundle with its manifest signature.
    workflow = (Path(__file__).parents[2] / ".github/workflows/release.yml").read_text()
    zip_step = re.search(r"        id: release-zip\n.*?        run: \|\n((?:          [^\n]*\n)+)", workflow, re.DOTALL)
    assert zip_step is not None, "The release must produce an installable ZIP"
    bundle = tmp_path / "release-signed/blacklist-7.8.9"
    bundle.mkdir(parents=True)
    payload = {
        "install.sh": b"#!/bin/bash\nexit 0\n",
        "MANIFEST.sha256": b"manifest",
        "MANIFEST.sha256.asc": b"detached-signature",
        "images/blacklist-app.tar.gz": b"offline-image",
    }
    for name, data in payload.items():
        destination = bundle / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (bundle / "install.sh").chmod(0o755)

    # When: the real workflow ZIP command runs on the already-signed payload.
    subprocess.run(
        ["bash", "-euo", "pipefail", "-c", textwrap.dedent(zip_step.group(1))],
        cwd=tmp_path,
        env={**os.environ, "RELEASE_VERSION": "7.8.9"},
        check=True,
        capture_output=True,
        timeout=30,
    )

    # Then: unpacking preserves every install asset and the signed manifest.
    archive = tmp_path / "blacklist-7.8.9-release.zip"
    with zipfile.ZipFile(archive) as zipped:
        for name, data in payload.items():
            assert zipped.read(f"blacklist-7.8.9/{name}") == data
        assert zipped.getinfo("blacklist-7.8.9/install.sh").external_attr >> 16 & 0o111
    digest, filename = archive.with_suffix(".zip.sha256").read_text().split()
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert filename == archive.name
    upload = workflow.split("name: release-bundle", 1)[1].split("retention-days:", 1)[0]
    assert "blacklist-*-release.zip" in upload.split()
    assert "blacklist-*-release.zip.sha256" in upload.split()
    publish = workflow.split("  create-release:", 1)[1]
    assert "blacklist-*-release.zip \\" in publish
    assert "blacklist-*-release.zip.sha256 \\" in publish
