"""Render Hangul glyphs into Disaster font cells (24x28, I4, white on black, ink ~rows 3-21)."""
from PIL import Image, ImageDraw, ImageFont
import dfont

FONT = r'C:\Windows\Fonts\malgun.ttf'
SIZE = 20
SS = 4  # supersample
STROKE = 1  # extra weight in supersampled px
ADV = 20  # advance width (same as kanji)
CUSTOM = {'·': 10}  # chars missing from the game font: char -> advance


def render(ch, size=SIZE):
    f = ImageFont.truetype(FONT, size * SS)
    im = Image.new('L', (dfont.CW * SS, dfont.CH * SS))
    dr = ImageDraw.Draw(im)
    # align by reference glyph '국' so all syllables share a baseline
    ref = dr.textbbox((0, 0), '국', font=f)
    x = (2 * SS) - ref[0] + (19 * SS - (ref[2] - ref[0])) // 2
    y = (3 * SS) - ref[1]
    dr.text((x, y), ch, font=f, fill=255, stroke_width=STROKE, stroke_fill=255)
    im = im.resize((dfont.CW, dfont.CH), Image.BOX)
    return im.point(lambda v: 0 if v < 20 else v)


def is_hangul(c):
    return '\uac00' <= c <= '\ud7a3'


class Mapper:
    """Assign Hangul syllables to unused kanji codes."""

    def __init__(self, fontobj, free_codes):
        self.f = fontobj
        self.free = list(free_codes)
        self.map = {}

    def code(self, ch):
        if ch not in self.map:
            self.map[ch] = self.free.pop()
        return self.map[ch]

    def encode(self, text):
        out = bytearray()
        i = 0
        while i < len(text):
            c = text[i]
            if c == '<':  # control tag, keep as ASCII
                j = text.index('>', i)
                out += text[i:j + 1].encode('ascii')
                i = j + 1
                continue
            if is_hangul(c) or c in CUSTOM:
                out += self.code(c)
            else:
                out += c.encode('cp932')
            i += 1
        return bytes(out)

    def apply(self, fonts):
        for ch, code in self.map.items():
            g = render(ch)
            for fo in fonts:
                idx = fo.index[code]
                fo.put(idx, g)
                fo.setwidth(idx, CUSTOM.get(ch, ADV))
