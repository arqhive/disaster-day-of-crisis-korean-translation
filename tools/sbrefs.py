"""Find how each pool string is used: enclosing function, called symbol, voice id."""
import re, bisect
import sbmeta
VOICE = re.compile(rb'^(sv|SV)_[A-Za-z0-9]+_\d+')

def refs(sb):
    code = sb.d[sb.hdr[0]:sb.hdr[1]]
    out = []
    for i in range(len(code) - 2):
        if code[i] == 0x26:
            if code[i + 1] < len(sb.strs):
                out.append((i, code[i + 1], 2))
        elif code[i] == 0x25:
            j = code[i + 1] << 8 | code[i + 2]
            if j >= 256 and j < len(sb.strs):
                out.append((i, j, 3))
    return code, out

def usage(sb):
    syms, funcs = sbmeta.meta(sb)
    code, rs = refs(sb)
    fstarts = [c + 0x0c for c, n in funcs]
    order = sorted(range(len(funcs)), key=lambda k: fstarts[k])
    fs_sorted = [fstarts[k] for k in order]
    res = {}
    for k, (pos, j, ln) in enumerate(rs):
        if j in res:
            continue
        # call symbol: first 4a xx after this ref (skipping other string refs)
        call = None
        p = pos + ln
        while p < min(len(code) - 1, pos + 40):
            if code[p] == 0x4a:
                call = syms[code[p + 1]] if code[p + 1] < len(syms) else None
                break
            p += 1
        voices = []
        for kk in range(max(0, k - 3), min(len(rs), k + 4)):
            q, jj, _ = rs[kk]
            if abs(q - pos) <= 12 and VOICE.match(sb.strs[jj]):
                # same call group: no 4a between
                a, b = sorted((q, pos))
                if 0x4a not in code[a + 2:b]:
                    voices.append(sb.strs[jj].decode())
        fi = bisect.bisect_right(fs_sorted, pos) - 1
        func = funcs[order[fi]][1] if fi >= 0 else ''
        res[j] = dict(func=func, call='.'.join(call) if call else '', voice=voices[0] if voices else '')
    return res
