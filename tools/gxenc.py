"""GX texture encoders: CMPR (via Pillow BC1), RGB5A3, I4."""
import io
import numpy as np
from PIL import Image


def _bc1_blocks(img):
    """Pillow DXT1 -> array (h/4, w/4, 8) of BC1 blocks."""
    w, h = img.size
    buf = io.BytesIO()
    img.convert('RGBA').save(buf, format='DDS', pixel_format='DXT1')
    raw = np.frombuffer(buf.getvalue()[128:], dtype=np.uint8)
    return raw[:(h // 4) * (w // 4) * 8].reshape(h // 4, w // 4, 8)


def cmpr(img):
    w, h = img.size
    assert w % 8 == 0 and h % 8 == 0
    b = _bc1_blocks(img).copy()
    # colors LE -> BE
    b[..., [0, 1, 2, 3]] = b[..., [1, 0, 3, 2]]
    # index bytes: reverse 2-bit order (pixel0 to high bits)
    idx = b[..., 4:8]
    idx = ((idx & 0x03) << 6) | ((idx & 0x0c) << 2) | ((idx & 0x30) >> 2) | ((idx & 0xc0) >> 6)
    b[..., 4:8] = idx
    # tile: 8x8 macro block = 2x2 sub-blocks (TL, TR, BL, BR)
    b = b.reshape(h // 8, 2, w // 8, 2, 8).transpose(0, 2, 1, 3, 4)
    return b.tobytes()


def rgb5a3(img):
    a = np.asarray(img.convert('RGBA'), dtype=np.uint16)
    h, w = a.shape[:2]
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    opaque = al >= 0xF8
    v_op = 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    v_tr = ((al >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
    v = np.where(opaque, v_op, v_tr).astype('>u2')
    v = v.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3)
    return v.tobytes()


def i4(img):
    # intensity from luminance of the visible image (composited on black)
    im = img.convert('RGBA')
    bg = Image.new('RGBA', im.size, (0, 0, 0, 255))
    bg.alpha_composite(im)
    g = np.asarray(bg.convert('L'), dtype=np.uint16)
    h, w = g.shape
    v = ((g + 8) // 17).clip(0, 15).astype(np.uint8)
    v = v.reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 2)
    return (v[:, 0] << 4 | v[:, 1]).astype(np.uint8).tobytes()


BLOCK = {'CMPR': (8, 8), 'RGB5A3': (4, 4), 'I4': (8, 8)}


def _pad(img, bw, bh):
    """Pad to block multiple by repeating the last row/column."""
    w, h = img.size
    W, H = -(-w // bw) * bw, -(-h // bh) * bh
    if (W, H) == (w, h):
        return img
    a = np.asarray(img.convert('RGBA'))
    a = np.pad(a, ((0, H - h), (0, W - w), (0, 0)), mode='edge')
    return Image.fromarray(a, 'RGBA')


def encode(img, fmt):
    return {'CMPR': cmpr, 'RGB5A3': rgb5a3, 'I4': i4}[fmt](_pad(img, *BLOCK[fmt]))


ENC = {k: (lambda im, k=k: encode(im, k)) for k in BLOCK}
