from __future__ import annotations
import os
from PIL import ImageFont
from luma.core.render import canvas

from board_sources import load_with_remote_overrides, get_national_rail_board, get_tube_board, interleave
from oled_device import create_device

# Create SSD1322 @ SPI0.0 (CE0). If you need rotation, pass rotate=2 (for 180°), etc.
device = create_device(driver="ssd1322", width=256, height=64, rotate=0)

def _load_font(cfg: dict, bold=False):
    ui = cfg.get("ui", {})
    path = ui.get("font_bold_path" if bold else "font_path")
    size = int(ui.get("font_size", 22))
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()

def _trim_to_width(draw, text, font, max_w):
    w = draw.textlength(text, font=font)
    if w <= max_w:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        t = text[:mid] + ell
        if draw.textlength(t, font=font) <= max_w:
            lo = mid + 1
        else:
            hi = mid
    return text[:hi-1] + ell

def draw_board(device, rows, cfg):
    font = _load_font(cfg, bold=False)
    font_bold = _load_font(cfg, bold=True)
    ui = cfg.get("ui", {})
    lh = int(ui.get("line_height", 24))
    x = int(ui.get("left_margin", 4))
    y = 0

    # SSD1322 is 4-bit grayscale; luma maps 0..255 → intensity. Use 255 for white.
    with canvas(device) as draw:
        # Optional header in bold (uncomment if you want a title line)
        # header = "Departures"
        # draw.text((x, y), _trim_to_width(draw, header, font_bold, device.width), font=font_bold, fill=255)
        # y += lh

        for r in rows:
            # Plenty of width (256): show time, ID, and destination
            # Adjust field widths to taste
            line = f"{r['ExptArrival']:>5}  {r['DisplayText']:<7}  {r['Destination']}"
            line = _trim_to_width(draw, line, font, device.width)
            draw.text((x, y), line, font=font, fill=255)
            y += lh
            if y > device.height - lh:
                break

def main():
    cfg, _ = load_with_remote_overrides("config.yml")
    rail = get_national_rail_board(cfg, limit=cfg["defaults"]["national_rail"]["limit"])
    tube = get_tube_board(cfg, limit=cfg["defaults"]["tube"]["limit"])
    rows = interleave(rail, tube) if cfg.get("ui", {}).get("interleave", False) else (rail + tube)
    # Re-index neatly
    for i, r in enumerate(rows, start=1):
        r["Index"] = i
    draw_board(device, rows, cfg)

if __name__ == "__main__":
    main()