"""WSL interop transport for a Windows simulator listening on loopback UDP."""

import json
import os
from pathlib import Path
import select
import subprocess
import time


class RelayError(OSError):
    """The Windows relay could not return the simulator's response."""


class SimulatorUnavailable(RelayError):
    """A UDP exchange failed, and the relay can still accept another request."""


class WindowsRelay:
    """Exchange one JSON datagram at a time with a Windows subprocess."""

    def __init__(self, script_path: str | Path, port: int):
        path = Path(script_path).resolve(strict=True)
        windows_path = subprocess.check_output(
            ['wslpath', '-w', str(path)], text=True
        ).strip()
        self._pending = bytearray()
        self._process = subprocess.Popen(
            [
                'powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive',
                '-ExecutionPolicy', 'Bypass', '-File', windows_path,
                '-Port', str(port),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=0,
        )
        try:
            if self._read_message(8.0) != {'relay': 'ready'}:
                raise RelayError('Unexpected Windows relay startup response')
        except BaseException:
            self.close()
            raise

    def _read_message(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        output = self._process.stdout
        while (line_end := self._pending.find(b'\n')) == -1:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([output], [], [], remaining)[0]:
                raise RelayError('Windows relay pipe timed out')
            chunk = os.read(output.fileno(), 4096)
            if not chunk:
                raise RelayError('Windows relay exited')
            self._pending.extend(chunk)
            if len(self._pending) > 65536:
                raise RelayError('Windows relay response exceeds the UDP frame size')

        line = bytes(self._pending[:line_end])
        del self._pending[:line_end + 1]
        try:
            message = json.loads(line)
        except (ValueError, UnicodeError) as error:
            raise RelayError('Windows relay received invalid JSON') from error
        if not isinstance(message, dict):
            raise RelayError('Windows relay received a non-object JSON response')
        return message

    def request(self, packet: dict) -> dict:
        line = json.dumps(packet, allow_nan=False, separators=(',', ':')).encode() + b'\n'
        if len(line) > 4096:
            raise ValueError('Windows relay request exceeds 4096 bytes')
        try:
            self._process.stdin.write(line)
            response = self._read_message(0.25)
        except OSError:
            self.close()
            raise
        if 'relay_error' in response:
            raise SimulatorUnavailable(
                f"Simulator UDP on Windows loopback: {response['relay_error']}"
            )
        return response

    def close(self) -> None:
        process = self._process
        process.stdin.close()
        try:
            process.wait(timeout=0.3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=0.5)
        finally:
            process.stdout.close()
