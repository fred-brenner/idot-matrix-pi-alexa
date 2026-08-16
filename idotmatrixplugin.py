"""Fast Fauxmo plugin for the iDotMatrix BLE bridge.

Fauxmo calls plugin ``on``/``off`` methods synchronously from its asyncio
event loop. BLE commands take several seconds, so this plugin acknowledges
Alexa immediately and performs the bridge command on a single worker thread.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from pathlib import Path

from fauxmo.plugins import FauxmoPlugin


LOGGER = logging.getLogger("idotmatrix-fauxmo")


class IdotmatrixPlugin(FauxmoPlugin):
    """Expose one iDotMatrix display as a fast-acknowledging WeMo device."""

    def __init__(
        self,
        *,
        name: str,
        port: int,
        command: str,
        state_file: str,
    ) -> None:
        self._command = shlex.split(command)
        self._state_path = Path(state_file).expanduser()
        self._state_path.parent.mkdir(parents=True, exist_ok=True)

        self._condition = threading.Condition()
        self._stopping = False
        self._pending_state: str | None = None
        self._actual_state = self._load_state()
        self._desired_state = self._actual_state

        super().__init__(name=name, port=port)
        # Fauxmo 0.6.0 does not expose initial_state on its base class. The
        # plugin's own persisted state is authoritative for GetBinaryState.
        self._latest_action = self._actual_state

        self._worker = threading.Thread(
            target=self._worker_loop,
            name="idotmatrix-ble-worker",
            daemon=True,
        )
        self._worker.start()

        LOGGER.info(
            "initialized %s with state=%s command=%s",
            name,
            self._actual_state,
            self._command,
        )

    def on(self) -> bool:
        """Queue the BLE on command and acknowledge Alexa immediately."""
        return self._request_state("on")

    def off(self) -> bool:
        """Queue the BLE off command and acknowledge Alexa immediately."""
        return self._request_state("off")

    def get_state(self) -> str:
        """Return the latest requested state without waiting for BLE."""
        with self._condition:
            return self._desired_state

    def close(self) -> None:
        """Stop the worker during a clean Fauxmo shutdown."""
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        self._worker.join(timeout=1)

    def _request_state(self, state: str) -> bool:
        with self._condition:
            self._desired_state = state
            self._pending_state = state
            self._save_state(state)
            self._condition.notify()
        LOGGER.info("accepted %s request for %s", state, self.name)
        return True

    def _worker_loop(self) -> None:
        while True:
            with self._condition:
                while self._pending_state is None and not self._stopping:
                    self._condition.wait()
                if self._stopping:
                    return
                state = self._pending_state
                self._pending_state = None

            if state is None:
                continue

            success = self._run_command(state)
            with self._condition:
                if success:
                    self._actual_state = state
                elif self._pending_state is None:
                    # If there is no newer request waiting, reflect the last
                    # confirmed hardware state rather than claiming success.
                    self._desired_state = self._actual_state
                    self._save_state(self._actual_state)

    def _run_command(self, state: str) -> bool:
        LOGGER.info("starting BLE %s command", state)
        try:
            result = subprocess.run(
                [*self._command, state],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        except Exception:
            LOGGER.exception("failed to start BLE %s command", state)
            return False

        if result.returncode == 0:
            LOGGER.info("BLE %s command completed", state)
            return True

        LOGGER.error("BLE %s command failed with exit code %s", state, result.returncode)
        return False

    def _load_state(self) -> str:
        try:
            state = self._state_path.read_text(encoding="utf-8").strip().lower()
        except FileNotFoundError:
            return "off"
        except OSError:
            LOGGER.exception("unable to read state file %s", self._state_path)
            return "off"
        return state if state in {"on", "off"} else "off"

    def _save_state(self, state: str) -> None:
        temporary_path = self._state_path.with_suffix(".tmp")
        try:
            temporary_path.write_text(f"{state}\n", encoding="utf-8")
            os.replace(temporary_path, self._state_path)
        except OSError:
            LOGGER.exception("unable to write state file %s", self._state_path)
