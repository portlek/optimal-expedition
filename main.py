import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageTk
from pynput import mouse, keyboard
import mss
import threading
import tkinter as tk

corner1_coords = None
corner2_coords = None

item_markers = []
active_overlay_window = None
selection_overlay_window = None

current_keys = set()
listener_keyboard = None
listener_mouse = None

selection_start_pos = None
selection_current_rect_id = None

icon_image = None


def close_selection_overlay():
    global selection_overlay_window, selection_current_rect_id
    if selection_overlay_window:
        try:
            selection_overlay_window.destroy()
        except tk.TclError:
            pass
    selection_overlay_window = None
    selection_current_rect_id = None
    print("DEBUG: Selection overlay closed.")


def reset_app(icon, item):
    global corner1_coords, corner2_coords, item_markers, active_overlay_window, selection_start_pos
    print("Resetting application...")
    close_selection_overlay()
    corner1_coords = None
    corner2_coords = None
    item_markers = []
    selection_start_pos = None
    print("Map coordinates, item markers, and selection start pos reset.")
    if active_overlay_window:
        print("Closing active item marking overlay...")
        try:
            active_overlay_window.destroy()
        except tk.TclError:
            pass
        active_overlay_window = None


def quit_app(icon, item):
    global listener_keyboard, listener_mouse
    print("Quitting application...")
    close_selection_overlay()
    if listener_keyboard and listener_keyboard.is_alive():
        listener_keyboard.stop()
    if listener_mouse and listener_mouse.is_alive():
        listener_mouse.stop()
    icon.stop()


def create_image(width, height, color1, color2):
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


def set_corner1_coords(x, y):
    global corner1_coords
    corner1_coords = (x, y)
    print(f"Corner 1 set at: {corner1_coords}")


def set_corner2_coords(x, y):
    global corner2_coords
    corner2_coords = (x, y)
    print(f"Corner 2 set at: {corner2_coords}")


def trigger_map_capture_and_overlay():
    global corner1_coords, corner2_coords, active_overlay_window, item_markers

    if active_overlay_window:
        print("Overlay window is already active. Please close it first or reset.")
        # TODO: Maybe bring to front?
        # For now, let's try to bring it to the front if it exists.
        if (
            isinstance(active_overlay_window, tk.Toplevel)
            and active_overlay_window.winfo_exists()
        ):
            active_overlay_window.lift()
            active_overlay_window.attributes("-topmost", True)
            active_overlay_window.attributes(
                "-topmost", False
            )  # To allow other windows to come on top later
            return
        # If it's not a valid window or doesn't exist, proceed to create a new one.

    if corner1_coords is None or corner2_coords is None:
        print(
            "Map corners not defined. Please set corners first (Alt+Shift+Left/Right Click)."
        )
        return

    print(
        f"Alt+Y detected. Capturing region between {corner1_coords} and {corner2_coords}."
    )

    cap_x1 = min(corner1_coords[0], corner2_coords[0])
    cap_y1 = min(corner1_coords[1], corner2_coords[1])
    cap_x2 = max(corner1_coords[0], corner2_coords[0])
    cap_y2 = max(corner1_coords[1], corner2_coords[1])

    monitor = {
        "top": cap_y1,
        "left": cap_x1,
        "width": cap_x2 - cap_x1,
        "height": cap_y2 - cap_y1,
    }

    if monitor["width"] <= 0 or monitor["height"] <= 0:
        print("Invalid capture region (zero width or height). Please redefine corners.")
        return

    captured_image_data = None
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            captured_image_data = sct_img
            print(
                f"Screenshot taken. Type: {type(sct_img)}, Size: ({sct_img.width}, {sct_img.height}), Monitor: {monitor}"
            )
    except Exception as e:
        print(f"Error during screenshot: {e}")
        return

    if captured_image_data:
        # Convert the mss screenshot to a PIL Image, then to PhotoImage
        img = Image.frombytes(
            "RGB",
            (captured_image_data.width, captured_image_data.height),
            captured_image_data.rgb,
            "raw",
            "BGR",
        )

        overlay_root = tk.Tk()
        overlay_root.withdraw()  # Hide the main root window for the overlay

        active_overlay_window = tk.Toplevel(overlay_root)
        active_overlay_window.title("Map Overlay")
        active_overlay_window.geometry(
            f"{captured_image_data.width}x{captured_image_data.height}+{cap_x1}+{cap_y1}"
        )
        active_overlay_window.attributes("-topmost", True)  # Keep it on top

        photo = ImageTk.PhotoImage(img)

        canvas = tk.Canvas(
            active_overlay_window,
            width=captured_image_data.width,
            height=captured_image_data.height,
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.image = photo  # Keep a reference!

        # Placeholder for right-click menu
        def on_overlay_right_click(event):
            print(
                f"Overlay right-clicked at screen ({event.x_root}, {event.y_root}), window ({event.x}, {event.y})"
            )
            # TODO: Implement marker type selection menu

        canvas.bind("<Button-3>", on_overlay_right_click)

        # Ensure reset_app can close this specific Toplevel window's root
        def on_overlay_close():
            print("DEBUG: Overlay window closed via X button or programmatically.")
            global active_overlay_window
            if active_overlay_window:
                # overlay_root.destroy() # This would destroy the hidden root, handling all Toplevels.
                # We need to be careful if overlay_root is shared or created per overlay.
                # For now, destroying the Toplevel itself should be managed by reset_app or quit_app.
                # Let's ensure that active_overlay_window is set to None.
                # The actual destroy() will be called by reset_app or quit_app.
                # However, if the user closes it with 'X', we need to handle it.
                active_overlay_window.destroy()  # Destroy the Toplevel
                active_overlay_window = None  # Clear the global reference

        active_overlay_window.protocol("WM_DELETE_WINDOW", on_overlay_close)

        item_markers = []  # Reset markers for the new overlay
        print(
            f"Item marking overlay created at ({cap_x1}, {cap_y1}) with size {captured_image_data.width}x{captured_image_data.height}."
        )
        print("Use 'Reset' from tray to clear this overlay.")
        # active_overlay_window.mainloop() # This would block. We want it to run alongside.
    else:
        print("Screenshot capture failed. Item marking overlay will not open.")


def finalize_region_selection(screen_start_coords, screen_end_coords):
    if not screen_start_coords or not screen_end_coords:
        print("DEBUG: Finalize_region_selection called with invalid screen positions.")
        return
    print(
        f"DEBUG: Finalizing region. Screen Start: {screen_start_coords}, Screen End: {screen_end_coords}"
    )
    x1, y1 = screen_start_coords
    x2, y2 = screen_end_coords
    final_start = (min(x1, x2), min(y1, y2))
    final_end = (max(x1, x2), max(y1, y2))
    set_corner1_coords(final_start[0], final_start[1])
    set_corner2_coords(final_end[0], final_end[1])
    trigger_map_capture_and_overlay()


def _tk_on_selection_b1_press(event, global_selection_start_pos_ref, canvas_local_vars):
    global selection_start_pos, selection_current_rect_id

    canvas_local_vars["drag_start_pos"] = (event.x, event.y)
    selection_start_pos = (event.x_root, event.y_root)
    print(
        f"DEBUG: Selection mouse press. Canvas: {canvas_local_vars['drag_start_pos']}, Screen: {selection_start_pos}"
    )
    if selection_current_rect_id:
        try:
            event.widget.delete(selection_current_rect_id)
        except tk.TclError:
            pass
        selection_current_rect_id = None


def _tk_on_selection_b1_motion(event, canvas_local_vars):
    global selection_current_rect_id
    if canvas_local_vars.get("drag_start_pos"):
        if selection_current_rect_id:
            try:
                event.widget.delete(selection_current_rect_id)
            except tk.TclError:
                pass
        selection_current_rect_id = event.widget.create_rectangle(
            canvas_local_vars["drag_start_pos"][0],
            canvas_local_vars["drag_start_pos"][1],
            event.x,
            event.y,
            outline="red",
            width=2,
        )


def _tk_on_selection_b1_release(event, close_overlay_func, finalize_func):
    global selection_start_pos
    screen_end_pos = (event.x_root, event.y_root)
    print(f"DEBUG: Selection mouse release. Screen End: {screen_end_pos}")

    current_screen_start_pos = selection_start_pos
    close_overlay_func()

    if current_screen_start_pos and screen_end_pos:
        finalize_func(current_screen_start_pos, screen_end_pos)
    else:
        print(
            "DEBUG: Invalid selection points (screen start or end missing on release)."
        )


def _tk_on_escape_press(event, close_overlay_func):
    print("DEBUG: Escape pressed in selection GUI.")
    close_overlay_func()


def create_selection_gui():
    global selection_overlay_window, selection_start_pos, selection_current_rect_id

    canvas_local_vars = {"drag_start_pos": None}

    if selection_overlay_window:
        try:
            selection_overlay_window.destroy()
        except tk.TclError:
            pass
        selection_overlay_window = None

    print("DEBUG: Creating selection GUI...")
    root = tk.Tk()
    selection_overlay_window = root
    selection_start_pos = None
    selection_current_rect_id = None

    root.title("Region Selector (Press Esc to cancel)")
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    canvas = tk.Canvas(root, bg="gray", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    canvas.bind(
        "<ButtonPress-1>",
        lambda e: _tk_on_selection_b1_press(e, selection_start_pos, canvas_local_vars),
    )
    canvas.bind(
        "<B1-Motion>", lambda e: _tk_on_selection_b1_motion(e, canvas_local_vars)
    )
    canvas.bind(
        "<ButtonRelease-1>",
        lambda e: _tk_on_selection_b1_release(
            e, close_selection_overlay, finalize_region_selection
        ),
    )
    root.bind("<Escape>", lambda e: _tk_on_escape_press(e, close_selection_overlay))

    root.config(cursor="crosshair")
    root.mainloop()
    if selection_overlay_window:
        print("DEBUG: Selection GUI mainloop ended, ensuring cleanup.")
        close_selection_overlay()


def start_region_selection_mode():
    global selection_overlay_window
    if selection_overlay_window:
        print("DEBUG: Selection mode already active or not cleaned up.")
        try:
            selection_overlay_window.destroy()
        except:
            pass
        selection_overlay_window = None

    print("DEBUG: Alt+T detected. Starting region selection mode in a new thread.")
    gui_thread = threading.Thread(target=create_selection_gui, daemon=True)
    gui_thread.start()


def on_key_press(key):
    global current_keys

    if key in {
        keyboard.Key.shift_l,
        keyboard.Key.shift_r,
        keyboard.Key.alt_l,
        keyboard.Key.alt_r,
    }:
        current_keys.add(key)

    try:
        alt_is_pressed = any(
            k in current_keys for k in {keyboard.Key.alt_l, keyboard.Key.alt_r}
        )

        is_t_key_event = False
        char_val = None

        if hasattr(key, "char") and key.char is not None:
            char_val = key.char.lower()
            if char_val == "t":
                is_t_key_event = True
        elif isinstance(key, keyboard.KeyCode):
            if key.vk == 84:
                is_t_key_event = True

        if (
            alt_is_pressed
            and is_t_key_event
            and key not in {keyboard.Key.alt_l, keyboard.Key.alt_r}
        ):
            start_region_selection_mode()
            return

    except AttributeError as e_attr:
        pass
    except Exception as e_gen:
        pass


def on_key_release(key):
    global current_keys
    if key in current_keys:
        current_keys.remove(key)

    if key == keyboard.Key.esc:
        pass


def main():
    global listener_keyboard
    icon_image = create_image(64, 64, "black", "blue")

    menu = (item("Reset", reset_app), item("Quit", quit_app))

    icon = pystray.Icon("Optimal Expedition", icon_image, "Optimal Expedition", menu)

    print("Starting input listeners...")
    try:
        listener_keyboard = keyboard.Listener(
            on_press=on_key_press, on_release=on_key_release
        )

        listener_keyboard.start()

        print("Application starting in system tray...")
        icon.run()

    finally:
        print("Stopping input listeners...")
        if listener_keyboard and listener_keyboard.is_alive():
            listener_keyboard.stop()
        print("Listeners stopped.")


if __name__ == "__main__":
    main()
