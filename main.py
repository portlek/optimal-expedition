import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw


# Placeholder functions for menu actions
def reset_app(icon, item):
    print("Resetting application...")
    # In the future, this will reset configurations


def quit_app(icon, item):
    print("Quitting application...")
    icon.stop()


def create_image(width, height, color1, color2):
    # Create a simple icon for now
    # In a real application, you would load an image file (e.g., .png)
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


def main():
    # Create an icon (replace with your actual icon path)
    # For simplicity, we generate a basic one here.
    # You should create a 64x64 px .png or .ico file for your app.
    icon_image = create_image(64, 64, "black", "blue")  # Placeholder icon

    # Define the menu
    menu = (item("Reset", reset_app), item("Quit", quit_app))

    # Create the system tray icon
    icon = pystray.Icon("Optimal Expedition", icon_image, "Optimal Expedition", menu)

    print("Application starting in system tray...")
    icon.run()


if __name__ == "__main__":
    main()
