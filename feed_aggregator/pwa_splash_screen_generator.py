"""Script to automatically create Splash Screens for iPhone PWA"""
import os

from PIL import Image

IPONE_SCREENS = [
    dict(width=393, height=852, scale=3),  # 14 & 15 Pro
    dict(width=430, height=932, scale=3),  # 14 & 15 Max
    dict(width=428, height=926, scale=3),  # 12 & 13 & 14 Plus
    dict(width=390, height=844, scale=3),  # 12 & 13 & 14
    dict(width=375, height=812, scale=3),  # 12 & 13 Mini
    dict(width=414, height=896, scale=3),  # X & 12 Max
    dict(width=375, height=812, scale=3),  # X & 11
]


def create():
    """Script to automatically create Splash Screens for iPhone PWA"""
    for props in IPONE_SCREENS:
        width = props["width"]
        height = props["height"]
        scale = props["scale"]
        file_name = f"./static/splashscreens/splash_{width}_{height}_{scale}.png"

        if os.path.isfile(file_name) is False:
            # Create a blank image with white background
            image = Image.new("RGB", (width, height), "white")

            logo = Image.open("static/logo.png", "r")

            # Calculate the x and y coordinates to align the text in the middle
            x = (image.width - logo.width) // 2
            y = (image.height - logo.height) // 2 - logo.height // 2

            # Draw the text in the middle
            image.paste(logo, (x, y))

            # Save the image
            image.save(file_name)
