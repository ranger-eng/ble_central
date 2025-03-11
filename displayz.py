import time
import digitalio
import busio
import board
from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from PIL import Image, ImageDraw, ImageFont

WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0x00, 0x00, 0x00)

class Displayz:
    def __init__(self):

        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        ecs = digitalio.DigitalInOut(board.CE0)
        dc = digitalio.DigitalInOut(board.D22)
        rst = digitalio.DigitalInOut(board.D27)
        busy = digitalio.DigitalInOut(board.D17)
        srcs = None
        self.display = Adafruit_SSD1680(122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=srcs,
                          rst_pin=rst, busy_pin=busy)
        self.display.fill(Adafruit_EPD.WHITE)

        self.display.rotation = 1

        self.fontsize = 14
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", self.fontsize) 


    def dispRawText(self, text):
        image = Image.new("RGB", (self.display.width, self.display.height), "white")
        draw = ImageDraw.Draw(image)

        draw.multiline_text(
            (0, 5),
            text,
            font=self.font,
            fill=BLACK,
        )
        self.display.image(image)
        self.display.display()


    def formatDict(self, data: dict) -> str:
        lines = []  # Store formatted lines

        # Ensure "status" and "timestamp" appear first on the same line
        status = data.get("status", "DISCONNECTED")  # Default to "UNKNOWN" if missing
        timestamp = data.get("timestamp", "???")  # Default to "N/A" if missing
        lines.append(f"status: {status}, {timestamp}")

        # Process other key-value pairs, adding a tab before each
        for key, value in data.items():
            # Handle nested dictionary with "value" and "unit"
            if "status" not in key and "timestamp" not in key:
                if isinstance(value, dict) and "data" in value and "unit": 
                    formatted_value = f"{value['data']} [{value['unit']}]"
                else:
                    formatted_value = str(value)  # Convert other values to string

                lines.append(f"    {key}: {formatted_value}")

        # Join all lines into a single string with newlines
        return "\n".join(lines)
