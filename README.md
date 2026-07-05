# AutoTrader 2026 Update

AutoTrader is a Python script that lets 2 (or more 😳) **Android** phones automate trading in Pokémon GO by sending *taps* to the screen. The communication with the device is done with Android Debug Bridge (adb).

## Requirements

- Two (or more) Android devices
- PC with Python 3.12+
- Python Poetry package installed for managing .venv and dependencies.
- PC with Google Platform Tools (adb) added to PATH.
- At least one USB cable to connect PC and devices
- [Optional] Wifi on the same network as the PC

## Disclaimer

This is a simple tool to make trading less boring.
The absence of batch trading in the game is the main issue/motivator for this project.

Using the script is not error free.
Keep an eye out on the phones while the script is running.

## License

MIT License

## Setup

Start off by cloning or downloading the files in this repo.

### Setting up Python

1. Install Python 3.12 or higher ([download page](https://www.python.org/downloads/)).

2. Install Poetry package using Python.  `pip install poetry`

3. Move to project directory in your shell and install required packages with `poetry install`

### Setting up adb (Android Debug Bridge)

Follow the instructions to download adb: <https://developer.android.com/studio/releases/platform-tools>

Make sure that `adb` can be used from the command line. Simplest way is to add the `platform-tools` folder (unzipped) to `PATH`.

*Recommended method for Windows users*: Install Google Platform Tools (adb) using WinGet (Windows Package Manager) this will automate the process of downloading tools and adding to `PATH`.
   `winget install -e --id Google.PlatformTools`

### Connecting a phone

#### 1. Enable Developer options

Go to **Settings > About phone > Software Information** and tap *Build Number* until developer mode is turned on.

#### 2. Enable USB debugging

Go to **Settings > Developer options** and enable *USB debugging*.

#### 3. Connect adb with phone

Connect the phone to the computer with a USB cable.
Press *Allow* on the prompt that shows up (the adb server must be running for this, see above).
Check that your device is connected with `adb devices`: the serial number along with the status 'device' should be in the list.

#### 4. [Optional] Configure wireless adb

Optionally, you can let adb communicate over Wifi instead of the USB cable.
**This requires that the computer and phone is connected to the same local network**.
If using USB cables is fine, continue to the next section.

Connect the phone's Wifi to the same network that the computer is on.
While connected with USB cable, use `adb tcpip 5555` to enable adb over Wifi on the phone.
After this, the phone can be unplugged.
Check your phone's local IP address in **Settings > About phone > Status**, it probably looks something like *192.168.x.x*.
Then, enter it with the command `adb connect <ipaddress>`.
A prompt should show up on the phone again, press *Allow*.
Check that your device is connected with `adb devices`.
This time, the IP address along with the status 'authenticated' should be in the list.

### Upload configuration for AutoTrader to phone

*NOTE: This only needs to be done once per device used!*

In order to know where to tap on the screen, AutoTrader reads a config file `AutoTraderConfig.yaml` from the phone.
It should contain the coordinates of each button for that phone.
This means that phones with identical screen resolutions can probably use the same config file.
This section covers how to create and upload that file.

Make a copy of the file `ConfigTemplate.yaml` and call it whatever you like.
In this example it will be called `MyConfig.yaml`.
Edit this file and replace the `[X, Y]` with the X and Y coordinates of the respective button.
The coordinates only need to be *on* the button, they don't need to be precise at all.
To find the coordinates, turn on the Pointer location tool (**Settings > Developer options > Pointer location**), enter a trade, and read the coordinates from the `X:` and `Y:` fields at the top while holding your finger on the desired button.
**Round to whole numbers**.

- **TRADE_BTN** is the button labeled *TRADE* on the friend screen.
- **FIRST_PKMN_BTN** is the first (top-left) Pokémon in the Pokémon selection menu.
- **NEXT_BTN** is the button labeled *NEXT* after selecting a Pokémon to trade.
- **CONFIRM_BTN** is the button on the left hand side of the trade screen to confirm the trade.
- **X_BTN** is the button to close the Pokémon screen after the trade is done.

Below is an example of a completed config file for a Samsung Galaxy M21 (1080 x 2340 px):

```yml
TRADE_BTN:      [890, 1625]
FIRST_PKMN_BTN: [195,  625]
NEXT_BTN:       [540, 1860]
CONFIRM_BTN:    [153, 1150]
X_BTN:          [540, 2075]
```

Once the coordinates are in the config file, use `adb push MyConfig.yaml /sdcard//AutoTraderConfig.yaml` to upload it.

## Usage

How to use the script when everything is ready.

### In-game preparation

Create a *#TAG* with all the Pokémon to trade.

IMPORTANT TIPS:

1. For smoothest process, after creating custom *#TAG* full of Pokémon you intend to trade, filter out any pokemon that may be cause for additional animation during trade sequence. This mainly includes removing those that have been favorited, XXL, XXS, and Pokémon that have earned buddy hearts with the following PoGo search string `xxl, xxs, favorite, !buddy0` within *#TAG* and remove them before beginning trade.

2. Complete your daily special trade(s) first.

## Process

1. Run Script (see section '## Running the script' below)

2.  Select TARGET devices (if more than 2 are connected)

3. Start a trade manually and search for the #TAG on both TARGET devices.

   Tip: In order to maximize candy reward with 100Km+ caught distance utilize `& distance` search string.

     *Example:*
   
     Device #1 `#TAG & distance9500` (Pokémon with #TAG & caught within a distance ≤ 9500Km.)
       
     Device #2 `#TAG & distance9600-` (Pokémon with #TAG & caught a distance ≥ 9600Km)

4. Complete the first normal trade manually.

    -The search query for the #TAG will now be remembered in the upcoming trades on both devices.

### Running the script

Connect 2 or more phones to adb with the steps above.

Execute the script from project directory with:

- `python poetry run trade` or simply `poetry run trade` depending on your Python setup.

The script starts by checking for connected devices, then loads config files, and prompts the user with how many trades to perform, after which the trading begins.

The trading process turns on the *Pointer location* tool, both to visualize the automated taps and to serve as an indicator that the script is running.
To cancel the trading process, press **Ctrl+C**.

When trading has finished or is cancelled, the *Pointer location* tool is turned off.
If this fails, it can be turned off manually in **Settings > Developer options > Pointer location**.

#### Custom delay between taps

Some devices and enviroments might experience more or less lag than what the default values are tailored for.
When in the `Number of trades?` prompt, the following commands may be used

`delay` to get set <value> and `delay <value>` to set the delay modifier between steps in tap sequence.
  The value can be any floating point number, such as `3`, `3.5`, `0`, or even `-1` (Default: 0)

`offset` to get set <value> and `offset <value>` to set the stagger delay for taps between devices.
  The value can be any positive floating point number or 0, such as `1`, `0.2`, `0` . (Default: 0.5)

`switch` to re-select TARGET devices (in cases where more than 2 devices are connected).

By default `delay` only affects the **TRADE_BTN**, **NEXT_BTN**, and **CONFIRM_BTN** timings, since those are the ones that involve waiting for the game server and `offset` affects all steps.

### Additional Info

  Flags `--delay` and `--offset` can be used to set respective values when first launching script.

*Example:*
    
    `poetry run trade --delay 1.2 --offset 0.4`
