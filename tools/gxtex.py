"""Fast GX texture decode (numpy) + TPL parsing."""
import struct
import numpy as np
from PIL import Image

# format: (block w, block h, bits per pixel)
FMT = {0: (8, 8, 4), 1: (8, 4, 8), 2: (8, 4, 8), 3: (4, 4, 16), 4: (4, 4, 16), 5: (4, 4, 16),
       6: (4, 4, 32), 8: (8, 8, 4), 9: (8, 4, 8), 10: (4, 4, 16), 14: (8, 8, 4)}
NAME = {0: 'I4', 1: 'I8', 2: 'IA4', 3: 'IA8', 4: 'RGB565', 5: 'RGB5A3', 6: 'RGBA8', 8: 'C4', 9: 'C8', 10: 'C14', 14: 'CMPR'}


def size(w, h, f):
    bw, bh, bpp = FMT[f]
    return ((w + bw - 1) // bw) * ((h + bh - 1) // bh) * bw * bh * bpp // 8


def _untile(blocks, w, h, bw, bh):
    """blocks: (nby, nbx, bh, bw, C) -> (H, W, C)"""
    nby, nbx = blocks.shape[:2]
    img = blocks.transpose(0, 2, 1, 3, 4).reshape(nby * bh, nbx * bw, -1)
    return img[:h, :w]


def _565(v):
    r = ((v >> 11) & 31) * 255 // 31
    g = ((v >> 5) & 63) * 255 // 63
    b = (v & 31) * 255 // 31
    return np.stack([r, g, b, np.full_like(r, 255)], -1).astype(np.uint8)


def _5a3(v):
    op = (v & 0x8000) != 0
    r = np.where(op, ((v >> 10) & 31) * 255 // 31, ((v >> 8) & 15) * 17)
    g = np.where(op, ((v >> 5) & 31) * 255 // 31, ((v >> 4) & 15) * 17)
    b = np.where(op, (v & 31) * 255 // 31, (v & 15) * 17)
    a = np.where(op, 255, ((v >> 12) & 7) * 255 // 7)
    return np.stack([r, g, b, a], -1).astype(np.uint8)


def decode(data, w, h, f, pal=None):
    bw, bh, bpp = FMT[f]
    nbx, nby = (w + bw - 1) // bw, (h + bh - 1) // bh
    n = size(w, h, f)
    raw = np.frombuffer(data[:n], dtype=np.uint8)
    if len(raw) < n:
        raise ValueError('short')
    if f == 14:
        b = raw.reshape(nby, nbx, 2, 2, 8)  # 8x8 block = 2x2 sub 4x4
        c0 = b[..., 0].astype(np.uint16) << 8 | b[..., 1]
        c1 = b[..., 2].astype(np.uint16) << 8 | b[..., 3]
        idx = np.unpackbits(b[..., 4:8], axis=-1).reshape(nby, nbx, 2, 2, 16, 2)
        idx = idx[..., 0] * 2 + idx[..., 1]
        a = _565(c0).astype(np.int32)
        bb = _565(c1).astype(np.int32)
        gt = (c0 > c1)[..., None]
        p2 = np.where(gt, (2 * a + bb) // 3, (a + bb) // 2)
        p3 = np.where(gt, (a + 2 * bb) // 3, 0)
        pal4 = np.stack([a, bb, p2, p3], -2)  # (...,4,4ch)
        px = np.take_along_axis(pal4, idx[..., None].astype(np.int64), -2)  # (...,16,4)
        px = px.reshape(nby, nbx, 2, 2, 4, 4, 4).transpose(0, 1, 2, 4, 3, 5, 6).reshape(nby, nbx, 8, 8, 4)
        return Image.fromarray(_untile(px.astype(np.uint8), w, h, 8, 8), 'RGBA')
    if bpp == 4:
        v = np.stack([raw >> 4, raw & 15], -1).reshape(nby, nbx, bh, bw)
    elif bpp == 8:
        v = raw.reshape(nby, nbx, bh, bw)
    elif bpp == 16:
        v = (raw[0::2].astype(np.uint16) << 8 | raw[1::2]).reshape(nby, nbx, bh, bw)
    if f == 0:
        g = (v * 17).astype(np.uint8)
        px = np.stack([g, g, g, np.full_like(g, 255)], -1)
    elif f == 1:
        g = v.astype(np.uint8)
        px = np.stack([g, g, g, np.full_like(g, 255)], -1)
    elif f == 2:
        g = ((v & 15) * 17).astype(np.uint8)
        px = np.stack([g, g, g, ((v >> 4) * 17).astype(np.uint8)], -1)
    elif f == 3:
        g = (v & 255).astype(np.uint8)
        px = np.stack([g, g, g, (v >> 8).astype(np.uint8)], -1)
    elif f == 4:
        px = _565(v)
    elif f == 5:
        px = _5a3(v)
    elif f == 6:
        r = raw.reshape(nby, nbx, 2, 16, 2)
        ar, gb = r[:, :, 0], r[:, :, 1]
        px = np.stack([ar[..., 1], gb[..., 0], gb[..., 1], ar[..., 0]], -1).reshape(nby, nbx, 4, 4, 4)
    elif f in (8, 9, 10):
        if pal is None:
            g = (v * (17 if f == 8 else 1)).astype(np.uint8)
            px = np.stack([g, g, g, np.full_like(g, 255)], -1)
        else:
            px = pal[np.clip(v & 0x3fff, 0, len(pal) - 1)]
    return Image.fromarray(_untile(px, w, h, bw, bh), 'RGBA')


def palette(d, po):
    n, _, pf, off = struct.unpack('>HBBII', d[po:po + 12])[0:4] if False else (None,) * 4
    n = struct.unpack('>H', d[po:po + 2])[0]
    pf = struct.unpack('>I', d[po + 4:po + 8])[0]
    off = struct.unpack('>I', d[po + 8:po + 12])[0]
    return n, pf, off


def tpl_images(d, base=0):
    """Yield (index, w, h, fmt, data_abs_offset, nbytes, pal_rgba) for TPL at base."""
    n, toff = struct.unpack('>II', d[base + 4:base + 12])
    if not (0 < n < 2000) or base + toff + 8 * n > len(d):
        return
    for i in range(n):
        io, po = struct.unpack('>II', d[base + toff + 8 * i:base + toff + 8 * i + 8])
        if not io or base + io + 12 > len(d):
            continue
        h, w, f, off = struct.unpack('>HHII', d[base + io:base + io + 12])
        if f not in FMT or not (1 <= w <= 1024 and 1 <= h <= 1024):
            continue
        nb = size(w, h, f)
        if base + off + nb > len(d):
            continue
        pal = None
        if po and f in (8, 9, 10):
            pn, pf, pd = palette(d, base + po)
            vals = np.frombuffer(d[base + pd:base + pd + 2 * pn], dtype='>u2').astype(np.uint16)
            if pf == 0:
                g = (vals & 255).astype(np.uint8)
                pal = np.stack([g, g, g, (vals >> 8).astype(np.uint8)], -1)
            elif pf == 1:
                pal = _565(vals)
            else:
                pal = _5a3(vals)
        yield i, w, h, f, base + off, nb, pal
