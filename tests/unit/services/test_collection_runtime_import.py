import os
import subprocess
import sys
from pathlib import Path


def test_collection_modules_import_with_container_pythonpath(tmp_path: Path) -> None:
    app_dir = Path(__file__).parents[3] / "app"
    environment = dict(os.environ, PYTHONPATH=str(app_dir))

    result = subprocess.run(
        [sys.executable, "-c", "import core.services.collection.regtech_data"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
