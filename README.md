# Menu Ping

A macOS menu bar app that shows live ping latency as a color-coded badge.

- **Green** — latency is good (default: <= 100 ms)
- **Yellow** — latency is high (default: <= 200 ms)
- **Red** (`Err`) — timeout / unreachable

## Features

- Color-coded rounded badge in the menu bar with the ping time in ms
- Pick a ping target: Google DNS, Cloudflare, Quad9, OpenDNS, localhost, or any custom host
- Adjustable thresholds: Tight (50/100 ms), Normal (100/200 ms), Relaxed (200/500 ms), or custom
- Pings every 2 seconds
- Start at Login toggle — automatically launch on login via macOS LaunchAgent
- Runs as a menu-bar-only app (no Dock icon)

## Requirements

- macOS
- Python 3.9+

## Install

### 1. Install dependencies

```bash
pip3 install rumps pyobjc-framework-Cocoa
```

### 2. Run directly

```bash
python3 menu_ping.py
```

### 3. Build as a standalone .app (optional)

```bash
pip3 install py2app
python3 setup.py py2app
```

The app bundle will be at `dist/Menu Ping.app`. Copy it to `/Applications`:

```bash
cp -R "dist/Menu Ping.app" /Applications/
```

Then open it from Finder or:

```bash
open "/Applications/Menu Ping.app"
```

## Usage

Click the badge in the menu bar to access:

| Menu Item      | Description                                      |
|----------------|--------------------------------------------------|
| **Target**         | Choose the host to ping (or enter a custom one)        |
| **Thresholds**     | Set green/yellow latency thresholds                     |
| **Start at Login** | Toggle auto-launch on login (requires built .app)       |
| **About**          | Version info                                            |
| **Quit**           | Stop the app                                            |

## Version

Current version: **1.0.0**

## License

MIT
