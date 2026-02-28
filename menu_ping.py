#!/opt/homebrew/bin/python3.10
"""Menu bar ping monitor for macOS."""

import os
import plistlib
import subprocess
import threading
import rumps
from AppKit import (
    NSAttributedString, NSFont, NSColor, NSImage, NSBezierPath, NSRect,
    NSForegroundColorAttributeName, NSFontAttributeName,
    NSMakeSize, NSMakeRect,
)
from Foundation import NSSize

DEFAULT_HOST = "8.8.8.8"
DEFAULT_GOOD = 100    # ms — green threshold
DEFAULT_WARN = 200    # ms — yellow threshold
PING_INTERVAL = 2     # seconds
BUNDLE_ID = "com.oscar.menuping"
LAUNCH_AGENT_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{BUNDLE_ID}.plist")

HOSTS = [
    ("Google DNS — 8.8.8.8", "8.8.8.8"),
    ("Cloudflare — 1.1.1.1", "1.1.1.1"),
    ("Quad9 — 9.9.9.9", "9.9.9.9"),
    ("OpenDNS — 208.67.222.222", "208.67.222.222"),
    ("localhost — 127.0.0.1", "127.0.0.1"),
]

THRESHOLD_PRESETS = [
    ("Tight  (50 / 100 ms)", 50, 100),
    ("Normal (100 / 200 ms)", 100, 200),
    ("Relaxed (200 / 500 ms)", 200, 500),
]

BG_COLORS = {
    "red":    NSColor.colorWithSRGBRed_green_blue_alpha_(0.85, 0.15, 0.15, 1.0),
    "yellow": NSColor.colorWithSRGBRed_green_blue_alpha_(0.90, 0.65, 0.0, 1.0),
    "green":  NSColor.colorWithSRGBRed_green_blue_alpha_(0.15, 0.70, 0.15, 1.0),
}
FG_COLOR = NSColor.whiteColor()
FONT = NSFont.monospacedDigitSystemFontOfSize_weight_(11, 0.6)


def make_badge_image(text, color_name):
    """Create a small rounded-rect badge image with colored bg and white text."""
    attrs = {
        NSForegroundColorAttributeName: FG_COLOR,
        NSFontAttributeName: FONT,
    }
    attr_str = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    text_size = attr_str.size()

    pad_x, pad_y = 6, 2
    w = text_size.width + pad_x * 2
    h = text_size.height + pad_y * 2

    img = NSImage.alloc().initWithSize_(NSMakeSize(w, h))
    img.lockFocus()

    bg = BG_COLORS[color_name]
    bg.setFill()
    rect = NSMakeRect(0, 0, w, h)
    path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, 4, 4)
    path.fill()

    attr_str.drawAtPoint_((pad_x, pad_y))

    img.unlockFocus()
    img.setTemplate_(False)
    return img


class PingApp(rumps.App):
    def __init__(self):
        super().__init__("Ping", quit_button=None)
        self.host = DEFAULT_HOST
        self.good_ms = DEFAULT_GOOD
        self.warn_ms = DEFAULT_WARN
        self.running = True
        self._pending_result = None

        # --- build menu ---
        # Target submenu
        self.target_items = {}
        target_menu = rumps.MenuItem("Target")
        for label, ip in HOSTS:
            item = rumps.MenuItem(label, callback=self._set_target)
            item._ip = ip
            if ip == self.host:
                item.state = True
            self.target_items[ip] = item
            target_menu.add(item)
        target_menu.add(rumps.separator)
        target_menu.add(rumps.MenuItem("Custom…", callback=self._custom_target))

        # Thresholds submenu
        self.threshold_items = {}
        thresh_menu = rumps.MenuItem("Thresholds")
        for label, g, w in THRESHOLD_PRESETS:
            item = rumps.MenuItem(label, callback=self._set_threshold)
            item._good = g
            item._warn = w
            if g == self.good_ms and w == self.warn_ms:
                item.state = True
            self.threshold_items[(g, w)] = item
            thresh_menu.add(item)
        thresh_menu.add(rumps.separator)
        thresh_menu.add(rumps.MenuItem("Custom…", callback=self._custom_threshold))

        # Start at Login toggle
        self.login_item = rumps.MenuItem("Start at Login", callback=self._toggle_login)
        self.login_item.state = os.path.exists(LAUNCH_AGENT_PATH)

        self.menu = [
            target_menu, thresh_menu, rumps.separator,
            self.login_item,
            rumps.separator,
            rumps.MenuItem("About", callback=self._about),
            rumps.separator,
            rumps.MenuItem("Quit", callback=self._quit),
        ]

        # Single timer drives everything: kick off ping in bg, apply result on main thread
        self._ping_in_flight = False
        self._timer = rumps.Timer(self._tick, PING_INTERVAL)
        self._timer.start()

    # ---- ping logic ----

    @staticmethod
    def _ping(host):
        try:
            out = subprocess.run(
                ["ping", "-c", "1", "-W", "2000", host],
                capture_output=True, text=True, timeout=5,
            )
            for line in out.stdout.splitlines():
                if "time=" in line:
                    part = line.split("time=")[1]
                    return float(part.split()[0])
        except Exception:
            pass
        return None

    def _tick(self, _):
        """Fires on main thread every PING_INTERVAL seconds."""
        if self._ping_in_flight:
            return
        self._ping_in_flight = True
        t = threading.Thread(target=self._bg_ping, daemon=True)
        t.start()

    def _bg_ping(self):
        """Runs ping in background, then updates UI on main thread."""
        ms = self._ping(self.host)

        if ms is None:
            text, color = "Err", "red"
        elif ms > self.warn_ms:
            text, color = f"{ms:.0f}ms", "yellow"
        else:
            text, color = f"{ms:.0f}ms", "green"

        self._pending_badge = (text, color)
        self._ping_in_flight = False

    @rumps.timer(0.3)
    def _apply_badge(self, _):
        """Fast main-thread poller to apply badge as soon as result is ready."""
        badge_data = getattr(self, "_pending_badge", None)
        if badge_data is None:
            return
        text, color = badge_data
        self._pending_badge = None
        try:
            status_item = self._nsapp.nsstatusitem
            badge = make_badge_image(text, color)
            status_item.setImage_(badge)
            status_item.setTitle_("")
        except AttributeError:
            pass

    # ---- callbacks ----

    def _set_target(self, sender):
        self.host = sender._ip
        for item in self.target_items.values():
            item.state = False
        sender.state = True

    def _custom_target(self, _):
        w = rumps.Window(
            message="Enter an IP address or hostname:",
            title="Custom Target",
            default_text=self.host,
            dimensions=(260, 22),
        )
        r = w.run()
        if r.clicked and r.text.strip():
            self.host = r.text.strip()
            for item in self.target_items.values():
                item.state = False

    def _set_threshold(self, sender):
        self.good_ms = sender._good
        self.warn_ms = sender._warn
        for item in self.threshold_items.values():
            item.state = False
        sender.state = True

    def _custom_threshold(self, _):
        w = rumps.Window(
            message="Enter green/yellow thresholds in ms (e.g. 80 150):",
            title="Custom Thresholds",
            default_text=f"{self.good_ms} {self.warn_ms}",
            dimensions=(260, 22),
        )
        r = w.run()
        if r.clicked and r.text.strip():
            parts = r.text.strip().split()
            if len(parts) == 2:
                try:
                    self.good_ms = int(parts[0])
                    self.warn_ms = int(parts[1])
                    for item in self.threshold_items.values():
                        item.state = False
                except ValueError:
                    pass

    @staticmethod
    def _get_app_path():
        """Return the path to the running .app bundle, or None."""
        p = os.path.abspath(__file__)
        while p != "/":
            if p.endswith(".app"):
                return p
            p = os.path.dirname(p)
        return None

    def _toggle_login(self, sender):
        if sender.state:
            # Remove launch agent
            try:
                os.remove(LAUNCH_AGENT_PATH)
            except FileNotFoundError:
                pass
            sender.state = False
        else:
            # Create launch agent
            app_path = self._get_app_path()
            if app_path is None:
                rumps.alert(
                    title="Start at Login",
                    message="Could not detect the .app bundle path. "
                            "Please run Menu Ping from the built .app.",
                )
                return
            plist = {
                "Label": BUNDLE_ID,
                "ProgramArguments": ["/usr/bin/open", app_path],
                "RunAtLoad": True,
            }
            os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
            with open(LAUNCH_AGENT_PATH, "wb") as f:
                plistlib.dump(plist, f)
            sender.state = True

    def _about(self, _):
        rumps.alert(
            title="Menu Ping",
            message=(
                "Version 1.0.0\n\n"
                "A tiny menu bar app that pings so you don't have to.\n\n"
                "Because refreshing speedtest.net 47 times a day "
                "wasn't cutting it anymore."
            ),
        )

    def _quit(self, _):
        self.running = False
        rumps.quit_application()


if __name__ == "__main__":
    PingApp().run()
