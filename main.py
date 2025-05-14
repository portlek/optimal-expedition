import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
from pynput import mouse, keyboard
import mss  # Added mss
import threading  # Will be needed for tkinter later
import tkinter as tk  # Added tkinter

# Global variables for map coordinates
corner1_coords = None
corner2_coords = None

# Global variables for item markers and overlay
item_markers = []
active_overlay_window = None  # Will hold our tkinter window later
selection_overlay_window = None  # For the Alt+T region selection GUI

# --- pynput Listener Globals ---
current_keys = set()  # To track currently pressed modifier keys
listener_keyboard = None
listener_mouse = None
# --- End pynput Listener Globals ---

# --- Tkinter selection globals ---
selection_start_pos = None
selection_current_rect_id = None
# --- End Tkinter selection globals ---

icon_image = None


def close_selection_overlay():
    global selection_overlay_window, selection_current_rect_id
    if selection_overlay_window:
        try:
            selection_overlay_window.destroy()
        except tk.TclError:
            pass
    selection_overlay_window = None
    selection_current_rect_id = None  # Clear rect ID too
    print("DEBUG: Selection overlay closed.")


# Placeholder functions for menu actions
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
        print("Closing active item marking overlay (simulated)...")
        active_overlay_window = None
    # In the future, this will reset all configurations


def quit_app(icon, item):
    global listener_keyboard, listener_mouse  # Ensure we can access to stop them
    print("Quitting application...")
    close_selection_overlay()  # Ensure selection overlay is closed if open
    if listener_keyboard and listener_keyboard.is_alive():
        listener_keyboard.stop()
    if listener_mouse and listener_mouse.is_alive():
        listener_mouse.stop()
    icon.stop()


def create_image(width, height, color1, color2):
    # Create a simple icon for now
    # In a real application, you would load an image file (e.g., .png)
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


# --- Placeholder functions for coordinate capture (to be called by pynput listeners) ---
def set_corner1_coords(x, y):
    global corner1_coords
    corner1_coords = (x, y)
    print(f"Corner 1 set at: {corner1_coords}")


def set_corner2_coords(x, y):
    global corner2_coords
    corner2_coords = (x, y)
    print(f"Corner 2 set at: {corner2_coords}")


# --- End Placeholder functions ---


# --- New function to handle map capture and overlay ---
def trigger_map_capture_and_overlay():
    global corner1_coords, corner2_coords, active_overlay_window, item_markers

    if active_overlay_window:
        print("Overlay window is already active. Please close it first or reset.")
        # TODO: Maybe bring to front?
        return

    if corner1_coords is None or corner2_coords is None:
        print(
            "Map corners not defined. Please set corners first (Alt+Shift+Left/Right Click)."
        )
        return

    print(
        f"Alt+Y detected. Capturing region between {corner1_coords} and {corner2_coords}."
    )

    # Ensure coordinates are ordered (top-left, bottom-right)
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

    # --- Actual screenshotting will happen here in the next step ---
    # with mss.mss() as sct:
    #     sct_img = sct.grab(monitor)
    #     # For now, just simulate
    #     print(f"Simulated screenshot taken for monitor: {monitor}")

    # --- Placeholder for opening the Tkinter overlay ---
    # This will be replaced by actual Tkinter window creation and display
    active_overlay_window = "simulated_window_object"  # Placeholder
    item_markers = []  # Clear previous markers for the new overlay session
    print(
        "Overlay window (simulated) opened. Right-click on it to add markers (not implemented yet)."
    )
    print("Use 'Reset' from tray to clear this simulated overlay.")


# --- End new function ---


# --- Region Selection Functions (New) ---
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


# --- Tkinter callback functions defined BEFORE create_selection_gui ---
# These will now accept explicit function references for actions if needed


def _tk_on_selection_b1_press(event, global_selection_start_pos_ref, canvas_local_vars):
    # Modifies global_selection_start_pos_ref indirectly by assigning to selection_start_pos
    # Modifies canvas_local_vars directly (it's a dict or a mutable object)
    global selection_start_pos, selection_current_rect_id

    canvas_local_vars["drag_start_pos"] = (event.x, event.y)
    selection_start_pos = (event.x_root, event.y_root)
    print(
        f"DEBUG: Selection mouse press. Canvas: {canvas_local_vars['drag_start_pos']}, Screen: {selection_start_pos}"
    )
    if selection_current_rect_id:
        try:
            event.widget.delete(selection_current_rect_id)  # event.widget is the canvas
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
    global selection_start_pos  # Read this global
    screen_end_pos = (event.x_root, event.y_root)
    print(f"DEBUG: Selection mouse release. Screen End: {screen_end_pos}")

    current_screen_start_pos = selection_start_pos
    close_overlay_func()  # Call passed function reference

    if current_screen_start_pos and screen_end_pos:
        finalize_func(
            current_screen_start_pos, screen_end_pos
        )  # Call passed function reference
    else:
        print(
            "DEBUG: Invalid selection points (screen start or end missing on release)."
        )


def _tk_on_escape_press(event, close_overlay_func):
    print("DEBUG: Escape pressed in selection GUI.")
    close_overlay_func()  # Call passed function reference


def create_selection_gui():
    global selection_overlay_window, selection_start_pos, selection_current_rect_id

    canvas_local_vars = {"drag_start_pos": None}  # To store canvas-relative drag start

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
    selection_current_rect_id = None  # Ensure it's reset before new canvas

    root.title("Region Selector (Press Esc to cancel)")
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    canvas = tk.Canvas(root, bg="gray", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Pass function references explicitly via lambdas
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
    if selection_overlay_window:  # Fallback cleanup
        print("DEBUG: Selection GUI mainloop ended, ensuring cleanup.")
        close_selection_overlay()


def start_region_selection_mode():
    global selection_overlay_window
    if selection_overlay_window:
        print("DEBUG: Selection mode already active or not cleaned up.")
        try:
            selection_overlay_window.destroy()  # Attempt to close if zombie
        except:
            pass
        selection_overlay_window = None

    print("DEBUG: Alt+T detected. Starting region selection mode in a new thread.")
    # Run the Tkinter GUI in a separate thread
    gui_thread = threading.Thread(target=create_selection_gui, daemon=True)
    gui_thread.start()


# --- End Region Selection Functions ---


# --- pynput Listener Callbacks ---
def on_key_press(key):
    global current_keys
    # print(f"DEBUG: Raw key press: {key}, current_keys before add: {current_keys}")

    if key in {
        keyboard.Key.shift_l,
        keyboard.Key.shift_r,
        keyboard.Key.alt_l,
        keyboard.Key.alt_r,
    }:
        current_keys.add(key)
        # print(f"DEBUG: Added modifier to current_keys: {key}. Current keys: {current_keys}")

    try:
        alt_is_pressed = any(
            k in current_keys for k in {keyboard.Key.alt_l, keyboard.Key.alt_r}
        )

        is_y_key_event = False
        is_t_key_event = False  # New for Alt+T
        char_val = None

        if hasattr(key, "char") and key.char is not None:
            char_val = key.char.lower()
            if char_val == "y":
                is_y_key_event = True
            elif char_val == "t":  # Check for 't'
                is_t_key_event = True
            # print(f"DEBUG: Key has char: '{key.char}', lowercased_char: '{char_val}'")
        elif isinstance(key, keyboard.KeyCode):
            if key.vk == 89:  # VK_Y
                is_y_key_event = True
                # print(f"DEBUG: Key is VK_Y (89). Key: {key}")
            elif key.vk == 84:  # VK_T = 84
                is_t_key_event = True
                # print(f"DEBUG: Key is VK_T (84). Key: {key}")
        # else:
        # print(f"DEBUG: Key {key} is not 'y' or 't' by char and not VK_Y or VK_T.")

        if alt_is_pressed:
            if is_y_key_event and key not in {keyboard.Key.alt_l, keyboard.Key.alt_r}:
                # print("DEBUG: Alt+Y combination DETECTED! Calling trigger_map_capture_and_overlay.")
                trigger_map_capture_and_overlay()
                return
            elif is_t_key_event and key not in {keyboard.Key.alt_l, keyboard.Key.alt_r}:
                # print("DEBUG: Alt+T combination DETECTED! Calling start_region_selection_mode.")
                start_region_selection_mode()
                return

    except AttributeError as e_attr:
        # print(f"DEBUG: AttributeError during Alt key check for key {key}: {e_attr}")
        pass
    except Exception as e_gen:
        # print(f"DEBUG: Generic Exception during Alt key check for key {key}: {e_gen}")
        pass


def on_key_release(key):
    global current_keys
    # print(f"DEBUG: Raw key release: {key}, current_keys before remove: {current_keys}")
    if key in current_keys:
        current_keys.remove(key)
        # print(f"DEBUG: Removed from current_keys: {key}. Current keys after remove: {current_keys}")

    if key == keyboard.Key.esc:
        pass


def on_mouse_click(x, y, button, pressed):
    """Handles global mouse clicks. Currently does nothing specific for general clicks."""
    # print(f"DEBUG: Global mouse click: ({x},{y}), button: {button}, pressed: {pressed}, current_keys: {current_keys}")
    # The old Alt+Shift+Click logic for corners has been removed
    # as corners are now set via the Alt+T GUI method.
    pass


# --- End pynput Listener Callbacks ---


def main():
    global listener_keyboard, listener_mouse  # Make them accessible
    # Create an icon (replace with your actual icon path)
    # For simplicity, we generate a basic one here.
    # You should create a 64x64 px .png or .ico file for your app.
    icon_image = create_image(64, 64, "black", "blue")  # Placeholder icon

    # Define the menu
    menu = (item("Reset", reset_app), item("Quit", quit_app))

    # Create the system tray icon
    icon = pystray.Icon("Optimal Expedition", icon_image, "Optimal Expedition", menu)

    # Initialize and start pynput keyboard and mouse listeners
    print("Starting input listeners...")
    try:
        listener_keyboard = keyboard.Listener(
            on_press=on_key_press, on_release=on_key_release
        )
        listener_mouse = mouse.Listener(on_click=on_mouse_click)

        listener_keyboard.start()
        listener_mouse.start()

        print("Application starting in system tray...")
        # icon.run() is blocking, so listeners must be started before this.
        # Listeners run in their own threads.
        icon.run()  # This will block until icon.stop() is called

    finally:
        print("Stopping input listeners...")
        if listener_keyboard and listener_keyboard.is_alive():
            listener_keyboard.stop()
            # listener_keyboard.join() # Join can block quit_app too long if pystray is difficult
        if listener_mouse and listener_mouse.is_alive():
            listener_mouse.stop()
            # listener_mouse.join()
        print("Listeners stopped.")


if __name__ == "__main__":
    main()
