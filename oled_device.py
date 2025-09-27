from __future__ import annotations
import os
from luma.core.interface.serial import spi, i2c
from luma.oled.device import ssd1322, ssd1306, sh1106

def create_device(
    *,
    driver: str | None = None,
    # SPI defaults
    spi_port: int = 0,
    spi_device: int = 0,     # CE0 = /dev/spidev0.0
    gpio_dc: int = 24,
    gpio_reset: int = 25,
    gpio_cs: int | None = None,     # None -> use CE line from spidev
    spi_bus_speed_hz: int = 8000000,
    # I2C fallback
    i2c_port: int = 1,
    i2c_address: int = 0x3C,
    # Panel geometry / rotation
    width: int = 256,
    height: int = 64,
    rotate: int = 0,        # 0 / 1 / 2 / 3 (quarters)
):
    """
    Returns a luma.oled device instance.
    Defaults for SSD1322 256x64 over SPI (port 0, device 0, DC=24, RST=25).
    Set OLED_DRIVER=ssd1322|ssd1306|sh1106 to override, or pass driver="ssd1322".
    """
    drv = (driver or os.getenv("OLED_DRIVER") or "ssd1322").lower()

    # Try SPI
    try:
        serial = spi(
            port=spi_port,
            device=spi_device,
            gpio_DC=gpio_dc,
            gpio_RST=gpio_reset,
            gpio_CS=gpio_cs,
            bus_speed_hz=spi_bus_speed_hz,
        )
        if drv == "ssd1322":
            return ssd1322(serial, width=width, height=height, rotate=rotate)
        elif drv == "sh1106":
            return sh1106(serial, rotate=rotate)
        else:
            return ssd1306(serial, rotate=rotate)
    except Exception:
        # Fallback to I2C if SPI not available
        serial = i2c(port=i2c_port, address=i2c_address)
        if drv == "ssd1322":
            # Most SSD1322 panels are SPI; I2C fallback likely not applicable.
            # If yours is I2C-capable, and wired accordingly, this will work.
            return ssd1322(serial, width=width, height=height, rotate=rotate)
        elif drv == "sh1106":
            return sh1106(serial, rotate=rotate)
        else:
            return ssd1306(serial, rotate=rotate)