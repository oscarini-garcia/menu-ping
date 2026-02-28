from setuptools import setup

APP = ["menu_ping.py"]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Menu Ping",
        "CFBundleDisplayName": "Menu Ping",
        "CFBundleIdentifier": "com.oscar.menuping",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,  # hide from Dock (menu-bar-only app)
    },
    "packages": ["rumps"],
}

setup(
    app=APP,
    name="Menu Ping",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
