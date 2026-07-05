#!/usr/bin/env python3

import argparse
import asyncio
from dataclasses import dataclass
from typing import TypeAlias
import random
import time
from pathlib import Path

try:
    from ppadb.client_async import ClientAsync
    from ppadb.device_async import DeviceAsync
    import yaml
    from yaml.parser import ParserError
    from rich.console import Console
    from rich.text import Text
    from rich.traceback import install

except ModuleNotFoundError as e:
    print(e)
    print('Run "poetry install" to install required packages.')
    print('Run "poetry run trade" to run trade.py script.')
    exit(1)


console = Console(highlight=False)
install(console=console, show_locals=True)


CONFIG_FILE_DIR = "/storage/self/primary/"
CONFIG_FILE_NAME = "AutoTraderConfig.yaml"
TMP_FILE_PATH = Path("tmp.yaml")

CONFIG: TypeAlias = dict[str, list[int]]


# ------------------------------------------------------
# Console Output
# ------------------------------------------------------

_PAD = 11  # width of the widest label "[SUCCESS]" (9) + 2 spaces
_INDENT = "\t" + " " * _PAD  # aligns with message text column


def info(msg):
    console.print(f"\t[cyan]{'[INFO]':{_PAD}}[/cyan]{msg}")


def success(msg):
    console.print(f"\t[green]{'[SUCCESS]':{_PAD}}[/green]{msg}")


def warning(msg):
    console.print(f"\t[yellow]{'[WARNING]':{_PAD}}[/yellow]{msg}")


def error(msg):
    console.print(f"\t[red]{'[ERROR]':{_PAD}}[/red]{msg}")


def action(msg):
    console.print(f"\t[magenta]{' [ACTION]':{_PAD}}[/magenta]{msg}")


def trade(msg):
    console.print(f"\t[blue]{'[TRADE]':{_PAD}}[/blue]{msg}")


def banner():

    console.print(Text(
        "\n"
        "╔══════════════════════════════════════════════╗\n"
        "║                                              ║\n"
        "║           AutoTrader by -ROCKET-             ║\n"
        "║                                              ║\n"
        "╚══════════════════════════════════════════════╝\n",
        style="blue"
    ))


@dataclass
class Button:

    name: str
    delay_after: float
    use_delay_modifier: bool
    reverse_order: bool = False


BUTTONS = [
    Button("TRADE_BTN",      6,  True),
    Button("FIRST_PKMN_BTN", 1,  False, reverse_order=True),
    Button("NEXT_BTN",       4,  True),
    Button("CONFIRM_BTN",    15, True,  reverse_order=True),
    Button("X_BTN",          1,  False),
]


BUTTON_NAMES = {btn.name for btn in BUTTONS}


SLEEP_MODIFIER = 0
TAP_OFFSET = 0.5


class DeviceAsyncWrapper(DeviceAsync):

    config: CONFIG

    # Store friendly device information
    name: str = "Unknown"
    model: str = "Unknown"


class AutoTraderError(Exception):
    pass


async def tap(device: DeviceAsyncWrapper, point: list[int]):

    x, y = point

    # random ±5 pixel jitter
    x += random.randint(-5, 5)
    y += random.randint(-5, 5)

    # Note: this is a tiny 2px diagonal swipe rather than a true tap, since
    # some Android UI elements (e.g. in the trade screen) register more
    # reliably with a short swipe than a zero-distance tap.
    await device.shell(f"input swipe {x} {y} {x+2} {y+2} 125")


async def trade_sequence(devices: list[DeviceAsyncWrapper]):

    global SLEEP_MODIFIER, TAP_OFFSET

    for btn in BUTTONS:

        delay = max(
            btn.delay_after + (SLEEP_MODIFIER if btn.use_delay_modifier else 0), 0
        )

        action(f" Sending {btn.name}")

        # Reverse tap order for buttons that require Device B to go first
        ordered_devices = list(reversed(devices)) if btn.reverse_order else devices

        # First device tap immediately, second device delayed by TAP_OFFSET seconds
        for i, dev in enumerate(ordered_devices):
            await tap(dev, dev.config[btn.name])
            if i == 0:
                await asyncio.sleep(TAP_OFFSET)

        await asyncio.sleep(delay)


async def trade_process(devices: list[DeviceAsyncWrapper], n_trades: int):

    if n_trades < 1:
        return

    await pointer(devices, True)

    try:

        for i in range(1, n_trades + 1):

            trade(f"Trade {i}/{n_trades}")

            await trade_sequence(devices)

        success(f"Completed {n_trades} trades!")

    finally:

        await pointer(devices, False)


async def get_config(device: DeviceAsyncWrapper) -> CONFIG:

    """
    Pulls config file from device and loads coordinates.
    """

    config_file_path = CONFIG_FILE_DIR + CONFIG_FILE_NAME

    await device.pull(config_file_path, TMP_FILE_PATH)

    content = TMP_FILE_PATH.read_text()

    TMP_FILE_PATH.unlink()

    if not content:

        raise AutoTraderError(f"Found no config file at {config_file_path}")

    config: CONFIG = yaml.safe_load(content)

    assert isinstance(config, dict), "Incorrect config format"

    if not BUTTON_NAMES <= set(config.keys()):

        raise AutoTraderError(
            f"Missing config keys: {BUTTON_NAMES - set(config.keys())}"
        )

    for key, coords in config.items():

        assert (
            isinstance(coords, list)
            and len(coords) == 2
            and all(isinstance(i, int) for i in coords)
        ), f"Invalid coordinates for '{key}': expected [x, y] integers, got {coords!r}"

    device.config = config

    return config


async def set_setting(device: DeviceAsyncWrapper, namespace_and_key: str, value):

    await device.shell(f"settings put {namespace_and_key} {value}")


async def pointer(devices: list[DeviceAsyncWrapper], on: bool):

    state = "ON" if on else "OFF"

    info(f"Pointer Location {state}\n")

    for device in devices:

        try:

            await set_setting(device, "system pointer_location", int(on))

            success(f"{device.serial}: Pointer {state}\n")

        except Exception:

            warning(f"{device.serial}: Failed pointer {state}\n")


async def select_devices(devices: list[DeviceAsyncWrapper]) -> list[DeviceAsyncWrapper]:

    """
    Ensures exactly two devices are selected.

    2 devices:
        auto select

    3+ devices:
        manual selection

    Less than 2:
        error
    """

    if len(devices) < 2:

        raise AutoTraderError(
            f"Only {len(devices)} device connected.\nPlease connect 2 devices.\n"
        )

    if len(devices) == 2:

        success("Two devices detected.")

        return devices

    info(f"{len(devices)} devices detected:")

    console.print()

    device_list = []

    for index, device in enumerate(devices, start=1):

        try:

            # Android friendly name
            name = (await device.shell("settings get global device_name")).strip()

            if not name or name == "null":
                name = (await device.shell("getprop ro.product.device")).strip()

            model = (await device.shell("getprop ro.product.model")).strip()

        except Exception as e:

            warning(f"{device.serial}: Failed to read device info ({e})")

            name = "Unknown"
            model = "Unknown"

        # Save the values so we can display them later
        device.name = name
        device.model = model

        device_list.append(device)

        console.print(
            f"{_INDENT}[green]{index}.[/green] "
            f"[cyan]{device.serial}[/cyan]\n"
            f"{_INDENT}   Name : {device.name}\n"
            f"{_INDENT}   Model: {device.model}\n"
        )

    console.print()

    def prompt_device(label: str, exclude_index: int | None) -> int:

        """
        Prompts for a single device index (1-based) for the given label
        (e.g. "Device A"), re-prompting until a valid, unused choice is made.
        Returns the chosen 0-based index into device_list.
        """

        while True:

            try:

                choice = console.input(
                    f"[cyan]Select {label} (enter a number 1-{len(device_list)}): [/cyan]"
                ).strip()

                if choice.lower() == "q":

                    info("Goodbye!")
                    raise SystemExit

                index = int(choice) - 1

                if not (0 <= index < len(device_list)):

                    raise ValueError

                if exclude_index is not None and index == exclude_index:

                    warning("That device is already selected. Choose a different one.")
                    continue

                return index

            except ValueError:

                warning(f"Invalid selection. Enter a number from 1-{len(device_list)}.")

            except EOFError:

                console.print()
                info("Goodbye!")
                raise SystemExit

            except KeyboardInterrupt:

                console.print()
                info("Goodbye!")
                raise SystemExit

    console.print("[yellow]  Q[/yellow] .............. Quit.\n")

    first = prompt_device("Device A", None)

    console.print()

    second = prompt_device("Device B", first)

    selected = [device_list[first], device_list[second]]

    console.print()

    success("Selected devices:\n")

    for label, device in zip(("Device A", "Device B"), selected):

        console.print(
            f"{_INDENT}[cyan]{label}: {device.serial}[/cyan]\n"
            f"{_INDENT}          Name : {device.name}\n"
            f"{_INDENT}          Model: {device.model}\n"
        )

    return selected


async def discover_and_load() -> list[DeviceAsyncWrapper]:

    """
    Queries ADB for connected devices, prompts selection of two,
    then pulls and validates configs from each.
    """

    info("Searching for connected devices...\n")

    client = ClientAsync()

    devices: list[DeviceAsyncWrapper] = await client.devices()

    if not devices:

        raise AutoTraderError("No devices found.")

    devices = await select_devices(devices)

    console.print()

    info("Loading configs...")

    for device in devices:

        try:

            await get_config(device)

        except (AutoTraderError, AssertionError, ParserError) as e:

            raise AutoTraderError(
                f"Failed loading config from {device.serial}", *e.args
            ) from e

    console.print()

    success("Setup complete!")

    return devices


async def setup() -> list[DeviceAsyncWrapper]:

    """
    Finds devices, selects two,
    then loads configs.
    """

    return await discover_and_load()


def parse_args() -> argparse.Namespace:

    """
    Parses command-line flags for initial delay/offset overrides.
    """

    parser = argparse.ArgumentParser(
        prog="trade",
        description="Automates Pokémon GO trading via ADB.",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Initial extra delay (sleep modifier) between steps in the tap "
             "sequence. Can be negative. Default: 0",
    )

    parser.add_argument(
        "--offset",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Initial tap stagger offset between devices. Must be 0 or "
             "positive. Default: 0.5",
    )

    args = parser.parse_args()

    if args.offset is not None and args.offset < 0:

        parser.error("--offset must be 0 or a positive number.")

    return args


def interface(args: argparse.Namespace):

    """
    Main user interface.
    """

    global SLEEP_MODIFIER, TAP_OFFSET

    banner()

    # Apply any startup overrides supplied via CLI flags
    if args.delay is not None:

        SLEEP_MODIFIER = args.delay

    if args.offset is not None:

        TAP_OFFSET = args.offset

    devices: list[DeviceAsyncWrapper] = asyncio.run(setup())

    if args.delay is not None or args.offset is not None:

        console.print()

        if args.delay is not None:
            success(f"Extra delay set to {SLEEP_MODIFIER:.1f}s (from --delay)")

        if args.offset is not None:
            success(f"Tap stagger offset set to {TAP_OFFSET:.1f}s (from --offset)")

    last_interrupt: float | None = None
    DOUBLE_PRESS_WINDOW = 2.0  # seconds to press Ctrl+C again to exit

    show_tips = True

    while True:

        console.print()

        try:

            if show_tips:

                console.print(
                    f"[cyan]Tips:[/cyan]\n\n"
                    f"[yellow]  delay <seconds> [/yellow] Adjust the wait time between steps in tap sequence.\n"
                    f"{_INDENT} default: 0 | ex. delay -1.3, delay 0.5, delay 3\n\n"
                    f"[yellow]  offset <seconds>[/yellow] Adjust the timing of staggered taps between devices.\n"
                    f"{_INDENT} default: 0.5 | ex. offset 0.1, offset 1.2, offset 2\n\n"
                    f"[yellow]  switch[/yellow] ......... Re-select target devices.\n\n"
                    f"[yellow]  Ctrl+C[/yellow] ......... Interrupt trade sequence.\n\n"
                    f"[yellow]  Ctrl+C[/yellow] (x2) .... Cancel and exit.\n\n"
                    f"[yellow]  Q[/yellow] .............. Quit.\n\n"
                )

            show_tips = False

            i = console.input("[cyan]Number of trades? > [/cyan]").strip()

            console.print()

            il = i.lower()

            if il == "q":

                info("Goodbye!")
                break

            if il.startswith("delay"):

                args_split = i.split()

                if len(args_split) == 2:

                    try:

                        SLEEP_MODIFIER = float(args_split[1])

                        success(f"Extra delay set to {SLEEP_MODIFIER:.1f}s")

                    except ValueError:

                        error("Delay must be a number.")

                else:

                    info(f"Current delay: {SLEEP_MODIFIER:.1f}s")

                continue

            if il.startswith("offset"):

                args_split = i.split()

                if len(args_split) == 2:

                    try:

                        new_offset = float(args_split[1])

                        if new_offset < 0:

                            raise ValueError

                        TAP_OFFSET = new_offset

                        success(f"Tap stagger offset set to {TAP_OFFSET:.1f}s")

                    except ValueError:

                        error("Offset must be 0 or a positive number.")

                else:

                    info(f"Current tap stagger offset: {TAP_OFFSET:.1f}s")

                continue

            if il == "switch":

                try:

                    devices = asyncio.run(discover_and_load())
                    show_tips = True

                except AutoTraderError as e:

                    error("\n".join(map(str, e.args)))

                continue

            n = int(i)

            if n <= 0:

                raise ValueError

        except KeyboardInterrupt:

            now = time.perf_counter()

            if last_interrupt is not None and (now - last_interrupt) <= DOUBLE_PRESS_WINDOW:

                console.print()

                info("Goodbye!")

                break

            last_interrupt = now

            warning(f"Press Ctrl+C again within {DOUBLE_PRESS_WINDOW:.0f}s to exit.")

            continue

        except EOFError:

            console.print()

            info("Goodbye!")

            break

        except ValueError:

            error("Enter a positive number.")

            continue

        try:

            trade(f"Starting {n} trade(s)...\n")

            start = time.perf_counter()

            asyncio.run(trade_process(devices, n))

            elapsed = time.perf_counter() - start

            success(f"Finished {n} trade(s) in {elapsed:.1f}s")

            show_tips = True

        except KeyboardInterrupt:

            warning("Trade cancelled.")

            show_tips = True

            continue

        except Exception as e:

            error(str(e))


def main():

    try:

        args = parse_args()

        interface(args)

    except AutoTraderError as e:

        error("\n".join(map(str, e.args)))

    except Exception as e:

        error(f"Unexpected error: {e.__class__.__name__}: {e}")

    except KeyboardInterrupt:

        console.print()

        info("Exiting...")


if __name__ == "__main__":

    main()


# https://github.com/encode/httpx/issues/914#issuecomment-622586610
# https://github.com/aio-libs/aiohttp/issues/4324
# https://github.com/aio-libs/aiohttp/issues/4324#issuecomment-733884349
