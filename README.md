# marble-scroll

Scroll emulation for the **Logitech Trackman Marble** (USB Trackball) on Linux.

Hold **both large buttons (left + right) and move the trackball** to scroll. No physical scroll wheel needed.

Fits you if you do not usually use the left or right button when you are scrolling up/down, AND you prefer to hold the buttons BEFORE starting to move the ball and release the buttons AFTER finishing moving the ball. 

For instance, if you use blender, this may not fit you.

If you are using some other trackball mouses without a scroller, you need to change some configuration to fit your mouse.

## How it works

The Marble Mouse has four buttons and a trackball but no scroll wheel. This daemon intercepts raw input events via `evdev`, detects when both main buttons are held simultaneously, and converts trackball motion into scroll wheel events through `uinput`.

**Zero-delay design** — button presses are forwarded immediately. The second button is suppressed only while the first button being held, and scroll mode activates on first motion. If you release both buttons without moving, a middle-click is sent instead.

| Input | Output |
|-------|--------|
| Left click | Left click (no delay) |
| Right click | Right click (no delay) |
| Left + Right hold + move ball | Scroll (vertical & horizontal) |
| Left + Right hold + release (no move) | Middle click |
| Small left button | Browser back (unchanged) |
| Small right button | Browser forward (unchanged) |

The device is identified by vendor/product ID (`046D:C408`), so it works on any USB port. Other mice are completely unaffected.

## Background

Inspired by [MarbleScroll](https://www.fewprojects.com/marblescroll-for-logitech-trackman-marble/) for Windows. The original project uses Windows low-level mouse hooks (`SetWindowsHookEx`) and sets holding the small left button & trackball moving as scrollning; it is even more trivial to set the same combination as scrolling on Linux. But this one sets a different key configuration, which thus uses Linux `evdev`/`uinput` to achieve a similar result natively:

The built-in `libinput` scroll-on-button-down feature works but only supports a single button as the scroll modifier — it cannot use the emulated middle button (left+right simultaneous press) because `libinput` treats emulated buttons as non-real events internally. This daemon bypasses that limitation entirely by operating at the `evdev` layer.

### Notification: no human review after this line.

## Requirements

- Linux with `evdev` and `uinput` support (any modern distro)
- Python 3
- `python-evdev` (`pip install evdev` or `dnf install python3-evdev`)

## Install

```bash
# Copy the script
sudo mkdir -p /opt/marble-scroll
sudo cp marble-scroll.py /opt/marble-scroll/

# Install and enable the systemd service
sudo cp marble-scroll.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now marble-scroll.service
```

## Uninstall

```bash
sudo systemctl disable --now marble-scroll.service
sudo rm /etc/systemd/system/marble-scroll.service
sudo rm -rf /opt/marble-scroll
sudo systemctl daemon-reload
```

## Configuration

Edit the constants at the top of `marble-scroll.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `SCROLL_THRESHOLD_Y` | 8 | Vertical movement (px) before a scroll event fires |
| `SCROLL_THRESHOLD_X` | 30 | Horizontal movement (px) before a scroll event fires |
| `SCROLL_DISTANCE` | 1 | Scroll units per event (increase for faster scrolling) |
| `VENDOR_ID` | `0x046D` | USB vendor ID (Logitech) |
| `PRODUCT_ID` | `0xC408` | USB product ID (Trackman Marble) |

After editing, restart the service:

```bash
sudo systemctl restart marble-scroll.service
```

## How it compares to libinput scroll-on-button-down

| | libinput | marble-scroll |
|---|---------|---------------|
| Scroll trigger | Single button hold | Both main buttons hold |
| Middle click | Emulated (left+right) | Preserved as fallback |
| Button sacrifice | One button becomes scroll-only | None |
| Delay on clicks | None | None |
| Needs root | No (kernel-level) | Yes (evdev grab) |

## License

MIT

---

*Built by [Claude Code](https://claude.ai/code) (Claude Opus 4.6)* with proud✨ <- the outside part is added by human :-P
