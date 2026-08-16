#!/usr/bin/env python3
"""Command-line bridge between Alexa/fauxmo and an iDotMatrix display."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

from idotmatrix.client import IDotMatrixClient
from idotmatrix.connection_manager import ConnectionManager
from idotmatrix.screensize import ScreenSize


LOGGER = logging.getLogger("idotmatrix-bridge")
SIZE_BY_NAME = {
    "16": ScreenSize.SIZE_16x16,
    "16x16": ScreenSize.SIZE_16x16,
    "32": ScreenSize.SIZE_32x32,
    "32x32": ScreenSize.SIZE_32x32,
    "64": ScreenSize.SIZE_64x64,
    "64x64": ScreenSize.SIZE_64x64,
}


def configured_screen_size() -> ScreenSize:
    value = os.environ.get("IDOTMATRIX_SIZE", "64x64").lower()
    try:
        return SIZE_BY_NAME[value]
    except KeyError as exc:
        valid = ", ".join(sorted(SIZE_BY_NAME))
        raise ValueError(f"IDOTMATRIX_SIZE must be one of: {valid}") from exc


def make_client() -> IDotMatrixClient:
    address = os.environ.get("IDOTMATRIX_ADDRESS", "").strip() or None
    return IDotMatrixClient(
        screen_size=configured_screen_size(),
        mac_address=address,
    )


async def set_state(state: str) -> None:
    client = make_client()
    address = os.environ.get("IDOTMATRIX_ADDRESS", "").strip() or "auto-discovery"
    LOGGER.info("connecting to %s", address)
    try:
        await client.connect()
        if state == "on":
            # Match the original LED_ON.bat behavior: wake the panel, set its
            # clock, and use clock style 7 in 24-hour mode without the date.
            await client.turn_on()
            await client.common.set_time(datetime.now())
            await client.clock.show(
                style=int(os.environ.get("IDOTMATRIX_CLOCK_STYLE", "7")),
                show_date=False,
                hour24=True,
            )
        else:
            await client.turn_off()
        LOGGER.info("display turned %s", state)
    finally:
        await client.disconnect()


async def discover() -> None:
    devices = await ConnectionManager.discover_devices()
    if not devices:
        LOGGER.warning("no iDotMatrix devices found")
        return
    for address in devices:
        print(address)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("on", "off", "discover"))
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("IDOTMATRIX_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args()
    try:
        if args.action == "discover":
            asyncio.run(discover())
        else:
            asyncio.run(set_state(args.action))
    except KeyboardInterrupt:
        return 130
    except Exception:
        LOGGER.exception("unable to set display state to %s", args.action)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
