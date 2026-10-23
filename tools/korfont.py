"""Render Hangul glyphs into Disaster font cells (24x28, I4, white on black, ink ~rows 3-21)."""
import math
import re

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


NARROW = (19, 18, 17, 16, 15, 14)   # 좁은 한글 폭 단계
NARROW_SPACE = 4                    # 좁힌 줄의 띄어쓰기 폭(원래 7)


def render_narrow(ch, adv):
    """가로로 좁힌 한글. 게임은 24px 칸의 가운데에서 폭(adv)만큼만 그리므로
    잉크를 칸 가운데 기준으로 adv/20 배 좁혀 그 영역 안에 넣는다."""
    g = render(ch)
    box = g.getbbox()
    if box is None:
        return g
    ink = g.crop((box[0], 0, box[2], g.size[1]))
    nw = max(1, round(ink.size[0] * adv / ADV))
    lo, hi = (dfont.CW - adv) / 2, (dfont.CW + adv) / 2
    x = round(dfont.CW / 2 + ((box[0] + box[2]) / 2 - dfont.CW / 2) * adv / ADV - nw / 2)
    x = max(math.ceil(lo), min(x, math.floor(hi) - nw))   # 반 픽셀 경계는 안쪽으로
    out = Image.new('L', g.size)
    out.paste(ink.resize((nw, g.size[1]), Image.LANCZOS), (x, 0))
    return out


class Mapper:
    """Assign Hangul syllables to unused kanji codes."""

    def __init__(self, fontobj, free_codes):
        self.f = fontobj
        self.free = list(free_codes)
        self.map = {}
        self.narrow = {}                     # (한글, 폭) -> 코드
        self.space = None                    # 좁은 띄어쓰기 코드
        self.widths = {c: w for c, w, p in fontobj.ents}

    def width(self, text, adv=ADV, space=None):
        """태그를 뺀 글자 폭 합 (한글은 adv, 띄어쓰기는 space 를 주면 그 폭)"""
        w = 0
        for c in re.sub(r'<[^>]*>', '', text):
            if is_hangul(c):
                w += adv
            elif c == ' ' and space is not None:
                w += space
            elif c in CUSTOM:
                w += CUSTOM[c]
            else:
                w += self.widths.get(c.encode('cp932'), 0)
        return w

    def encode_fit(self, text, limit):
        """줄(<n>·<p>·<LINE> 사이)마다 폭이 limit 를 넘으면 그 줄의 한글은 좁은 글자, 띄어쓰기는 좁은 띄어쓰기로 바꿔 넣는다.
        넘치는 줄이 없으면 None. 좁은 글자 자리는 기존 배정이 끝난 뒤 남는 자리에서 새로 잡는다."""
        out, changed = [], False
        for seg in re.split(r'(<n>|<p>|<LINE>)', text):
            if seg in ('<n>', '<p>', '<LINE>') or self.width(seg) <= limit:
                out.append(self.encode(seg))
                continue
            adv = next((a for a in NARROW if self.width(seg, a, NARROW_SPACE) <= limit), NARROW[-1])
            changed = True
            b = bytearray()
            for part in re.split(r'(<[^>]*>)', seg):
                if part.startswith('<'):
                    b += part.encode('ascii')
                    continue
                for c in part:
                    if c == ' ':
                        if self.space is None:
                            self.space = self.free.pop()
                        b += self.space
                    elif is_hangul(c):
                        if (c, adv) not in self.narrow:
                            self.narrow[(c, adv)] = self.free.pop()
                        b += self.narrow[(c, adv)]
                    else:
                        b += self.encode(c)
            out.append(bytes(b))
        return b''.join(out) if changed else None

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
        if self.space is not None:
            for fo in fonts:
                idx = fo.index[self.space]
                fo.put(idx, Image.new('L', (dfont.CW, dfont.CH)))
                fo.setwidth(idx, NARROW_SPACE)
        for (ch, adv), code in self.narrow.items():
            g = render_narrow(ch, adv)
            for fo in fonts:
                idx = fo.index[code]
                fo.put(idx, g)
                fo.setwidth(idx, adv)
