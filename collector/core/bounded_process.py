import os
import selectors
import subprocess
import time
from collections.abc import Sequence


def run_bounded(command: Sequence[str], max_bytes: int, timeout: float) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise RuntimeError("bounded process pipes are unavailable")

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    stdout = bytearray()
    stderr = bytearray()
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(command, timeout)
            events = selector.select(remaining)
            if not events:
                continue
            for key, _mask in events:
                chunk = os.read(key.fd, 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    if len(stdout) + len(chunk) > max_bytes:
                        process.kill()
                        process.wait()
                        return subprocess.CompletedProcess(command, 63, b"", bytes(stderr))
                    stdout.extend(chunk)
                elif len(stderr) < 64 * 1024:
                    stderr.extend(chunk[: 64 * 1024 - len(stderr)])
        return subprocess.CompletedProcess(command, process.wait(), bytes(stdout), bytes(stderr))
    finally:
        selector.close()


def run_text_bounded(command: Sequence[str], max_bytes: int, timeout: float) -> subprocess.CompletedProcess[str]:
    result = run_bounded(command, max_bytes, timeout)
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        result.stdout.decode("utf-8", errors="replace"),
        result.stderr.decode("utf-8", errors="replace"),
    )
