#!/usr/bin/env python3
"""
Scroll emulation for Logitech USB Trackball (Marble Mouse), v2.
No timing window — uses motion to confirm scroll intent.

Logic:
- Press left/right → immediately forwarded, no delay
- While holding one, press the other → second button is "armed" (not forwarded)
- Ball moves while both held → release the first button, enter scroll mode
- Release either while armed (no motion) → send middle-click instead

This means zero latency on normal clicks and drags.
"""

import evdev
from evdev import ecodes, UInput
import select
import sys

VENDOR_ID = 0x046D
PRODUCT_ID = 0xC408

SCROLL_THRESHOLD_Y = 8
SCROLL_THRESHOLD_X = 30
SCROLL_DISTANCE = 1


def find_trackball():
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if dev.info.vendor == VENDOR_ID and dev.info.product == PRODUCT_ID:
            caps = dev.capabilities().get(ecodes.EV_KEY, [])
            if ecodes.BTN_LEFT in caps:
                return dev
        dev.close()
    return None


def emit(ui, etype, ecode, value):
    ui.write(etype, ecode, value)
    ui.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)


IDLE = 0
ONE_HELD = 1       # one button held, forwarded normally
ARMED = 2          # both held, second button suppressed, waiting for motion
SCROLLING = 3      # motion confirmed, scrolling


def run(dev):
    caps = dev.capabilities()
    rel_caps = list(caps.get(ecodes.EV_REL, []))
    if ecodes.REL_WHEEL not in rel_caps:
        rel_caps.append(ecodes.REL_WHEEL)
    if ecodes.REL_HWHEEL not in rel_caps:
        rel_caps.append(ecodes.REL_HWHEEL)
    caps[ecodes.EV_REL] = rel_caps

    key_caps = list(caps.get(ecodes.EV_KEY, []))
    if ecodes.BTN_MIDDLE not in key_caps:
        key_caps.append(ecodes.BTN_MIDDLE)
    caps[ecodes.EV_KEY] = key_caps
    caps.pop(ecodes.EV_SYN, None)

    ui = UInput(caps, name="Marble Scroll Virtual Mouse")

    state = IDLE
    left_down = False
    right_down = False
    first_btn = None   # which button was pressed first
    dx = 0
    dy = 0

    dev.grab()

    try:
        while True:
            r, _, _ = select.select([dev.fd], [], [])
            for event in dev.read():
                if event.type == ecodes.EV_KEY:
                    is_left = event.code == ecodes.BTN_LEFT
                    is_right = event.code == ecodes.BTN_RIGHT
                    is_lr = is_left or is_right
                    pressed = event.value == 1
                    released = event.value == 0

                    if pressed and is_lr:
                        if is_left:
                            left_down = True
                        else:
                            right_down = True

                        if state == IDLE:
                            # first button — forward immediately
                            first_btn = event.code
                            ui.write(event.type, event.code, event.value)
                            state = ONE_HELD

                        elif state == ONE_HELD:
                            # second button — suppress it, arm for scroll
                            dx = 0
                            dy = 0
                            state = ARMED

                        # ignore extra presses in ARMED/SCROLLING

                    elif released and is_lr:
                        if is_left:
                            left_down = False
                        else:
                            right_down = True  # typo guard
                            right_down = False

                        if state == ARMED:
                            # both were held, no motion — send middle click
                            # first release the first button we forwarded
                            emit(ui, ecodes.EV_KEY, first_btn, 0)
                            emit(ui, ecodes.EV_KEY, ecodes.BTN_MIDDLE, 1)
                            emit(ui, ecodes.EV_KEY, ecodes.BTN_MIDDLE, 0)
                            state = IDLE
                            first_btn = None

                        elif state == SCROLLING:
                            if not left_down and not right_down:
                                state = IDLE
                                first_btn = None
                            # don't forward the release — first btn was
                            # already released when entering scroll mode

                        elif state == ONE_HELD:
                            # normal release of the only held button
                            ui.write(event.type, event.code, event.value)
                            state = IDLE
                            first_btn = None

                        else:
                            ui.write(event.type, event.code, event.value)

                    else:
                        # other buttons (side, extra, etc)
                        ui.write(event.type, event.code, event.value)

                elif event.type == ecodes.EV_REL:
                    if state == ARMED:
                        # motion while armed — enter scroll mode
                        # release the first button we already forwarded
                        emit(ui, ecodes.EV_KEY, first_btn, 0)
                        state = SCROLLING

                        # process this motion event as scroll
                        if event.code == ecodes.REL_Y:
                            dy += event.value
                        elif event.code == ecodes.REL_X:
                            dx += event.value

                    elif state == SCROLLING:
                        if event.code == ecodes.REL_Y:
                            dy += event.value
                        elif event.code == ecodes.REL_X:
                            dx += event.value

                        if abs(dy) >= SCROLL_THRESHOLD_Y:
                            scroll_val = -SCROLL_DISTANCE if dy > 0 else SCROLL_DISTANCE
                            emit(ui, ecodes.EV_REL, ecodes.REL_WHEEL, scroll_val)
                            dy = 0
                            dx = 0

                        if abs(dx) >= SCROLL_THRESHOLD_X:
                            scroll_val = SCROLL_DISTANCE if dx > 0 else -SCROLL_DISTANCE
                            emit(ui, ecodes.EV_REL, ecodes.REL_HWHEEL, scroll_val)
                            dx = 0
                            dy = 0

                    else:
                        # normal motion — pass through
                        ui.write(event.type, event.code, event.value)

                elif event.type == ecodes.EV_SYN:
                    if state not in (ARMED, SCROLLING):
                        ui.write(event.type, event.code, event.value)

                else:
                    ui.write(event.type, event.code, event.value)

    except (OSError, KeyboardInterrupt):
        pass
    finally:
        dev.ungrab()
        ui.close()


def main():
    dev = find_trackball()
    if not dev:
        print("Logitech USB Trackball not found", file=sys.stderr)
        sys.exit(1)

    print(f"Grabbed: {dev.name} at {dev.path}", file=sys.stderr)
    run(dev)


if __name__ == "__main__":
    main()
