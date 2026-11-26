# PulseBar

A lightweight, minimalist, always-on-top network speed meter for Windows. Built with Python and `tkinter` to keep memory usage ultra-low while showing real-time upload speed, download speed, ping latency, and Public IP address in a compact dark overlay.

## Features

- **Real-Time Network Stats:** Displays live upload (`↑`) and download (`↓`) speeds with automatic `B/s`, `KB/s`, and `MB/s` scaling.
- **Latency & IP Monitor:** Shows live ping latency (`ms`) in a compact pill badge alongside your local IPv4 address.
- **Low RAM Footprint:** Native `tkinter` canvas UI without heavy browser or Electron overhead.
- **Minimalist Dark Design:** Frameless `#1C1C1C` rounded widget that stays out of the way.
- **Always-on-Top:** Uses Windows Z-order management (`SetWindowPos`) to stay visible above standard windows and taskbar interactions.
- **Draggable & Quick Controls:** Drag anywhere on the widget to reposition it, or right-click to **Center Widget**, toggle **Start with Windows**, or **Quit**.
- **Portable Windows Executable:** Available as a standalone `.exe`—no Python installation required.

## Quick Start (Portable `.exe`)

1. Go to the [**Releases**](../../releases) section of this repository.
2. Download `PulseBar-Portable.zip` from the latest release.
3. Extract the `.zip` file and double-click `PulseBar.exe` to run.

> **Note:** On first launch, Windows SmartScreen may show an *"Unknown publisher"* warning for unsigned builds. Click **More info** → **Run anyway** to start the app.

## Run from Source

### Prerequisites
- Python 3.10+ (Windows recommended)
- `psutil`

### Setup & Run
```bash
git clone https://github.com/sp-sahoo/PulseBar.git
cd PulseBar
pip install psutil
python PulseBar.py
```

### Build Standalone `.exe`
```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name PulseBar PulseBar.py
```
The compiled executable will be generated inside `dist/PulseBar.exe`.

## Controls

- **Left-click + Drag:** Move the widget anywhere on screen.
- **Right-click:**
  - **Start with Windows:** Adds or removes PulseBar from `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` and saves your preference in `settings.json`.
  - **Center Widget:** Moves the widget back to the center of your primary display.
  - **Quit:** Closes the application.
