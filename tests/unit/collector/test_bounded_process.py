import subprocess
import sys

import pytest

from collector.core.bounded_process import run_bounded


def test_unknown_length_output_is_stopped_at_the_byte_limit() -> None:
    result = run_bounded(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 2048)"],
        max_bytes=1024,
        timeout=5,
    )

    assert result.returncode == 63
    assert result.stdout == b""


def test_output_within_the_limit_is_returned() -> None:
    result = run_bounded(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 512)"],
        max_bytes=1024,
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout == b"x" * 512


def test_timeout_terminates_the_process() -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        run_bounded([sys.executable, "-c", "import time; time.sleep(5)"], max_bytes=1024, timeout=0.05)
