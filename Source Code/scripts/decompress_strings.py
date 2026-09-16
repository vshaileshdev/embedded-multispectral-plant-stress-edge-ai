"""
Final string extraction: decompress all miCOMPRESSED elements and scan for UTF-16 strings.
Also tries loading with mat_dtype=True and variable_names filtering.
"""
import io, sys, zlib, struct, json, pathlib
import numpy as np
from scipy.io import loadmat

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RAW = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Source Code/backend/data/raw/tomato')
RESULTS = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Results')
RESULTS.mkdir(parents=True, exist_ok=True)


def extract_utf16_strings(data: bytes, min_len: int = 2, max_len: int = 80) -> list:
    """Scan raw bytes for UTF-16 LE readable strings."""
    results = []
    i = 0
    buf = []
    while i < len(data) - 1:
        cu = struct.unpack_from('<H', data, i)[0]
        if 0x0020 <= cu <= 0x00FF:  # printable Latin
            buf.append(chr(cu))
        else:
            if len(buf) >= min_len:
                s = ''.join(buf).strip()
                if min_len <= len(s) <= max_len:
                    results.append(s)
            buf = []
        i += 2
    if len(buf) >= min_len:
        s = ''.join(buf).strip()
        if min_len <= len(s) <= max_len:
            results.append(s)
    return results


def scan_and_decompress(mat_path: pathlib.Path) -> list:
    """Read file, decompress all COMPRESSED elements, collect UTF-16 strings."""
    data = mat_path.read_bytes()
    offset = 128  # skip file header
    all_strings = []

    while offset < len(data) - 8:
        dt_raw, n_raw = struct.unpack_from('<II', data, offset)
        dt = dt_raw & 0x0000FFFF
        small_sz = (dt_raw >> 16) & 0xFFFF

        if small_sz > 0:
            # Small element
            offset += 8
            continue

        n_bytes = n_raw
        data_start = offset + 8

        if data_start + n_bytes > len(data):
            break

        if dt == 15:  # miCOMPRESSED
            compressed = data[data_start:data_start + n_bytes]
            try:
                decompressed = zlib.decompress(compressed)
                strings = extract_utf16_strings(decompressed)
                all_strings.extend(strings)
            except Exception as e:
                pass

        elif dt == 14:  # miMATRIX (uncompressed)
            element_bytes = data[data_start:data_start + n_bytes]
            strings = extract_utf16_strings(element_bytes)
            all_strings.extend(strings)

        # Advance
        pad = (8 - n_bytes % 8) % 8 if n_bytes % 8 else 0
        offset = data_start + n_bytes + pad

    # Deduplicate preserving order
    seen = set()
    unique = []
    for s in all_strings:
        s = s.strip()
        if s and s not in seen and len(s) > 1:
            seen.add(s)
            unique.append(s)
    return unique


def filter_labels(strings: list) -> list:
    """Keep strings that look like experimental labels, not MATLAB internals."""
    skip = {
        'string','char','double','single','logical','cell','struct',
        'int8','int16','int32','int64','uint8','uint16','uint32','uint64',
        'MCOS','matlab','handle','function','NaN','Inf','true','false',
        'PCWIN64','Created','Platform','MAT','MATLAB',
        'repmat','end','else','for','while','if',
        'wvl','PAR','PARf','refl','trans','abs','Fup','Fdw','smooth',
        'treatment','repli','sample','PAR1000','PAR300',
    }
    result = []
    for s in strings:
        if s in skip:
            continue
        if s.startswith('_'):
            continue
        # Keep short, human-readable strings (likely experimental labels)
        if 1 < len(s) <= 40:
            result.append(s)
    return result


all_results = {}

for fname in sorted(RAW.glob('*.mat')):
    print(f'\n{"="*60}')
    print(f'FILE: {fname.name}  ({fname.stat().st_size//1024} KB)')

    raw_strings = scan_and_decompress(fname)
    filtered = filter_labels(raw_strings)

    print(f'  Raw UTF-16 strings found: {len(raw_strings)}')
    print(f'  After filtering: {len(filtered)}')
    print(f'  Candidate labels:')
    for s in filtered[:50]:
        print(f'    {repr(s)}')

    all_results[fname.name] = {
        'all_strings': raw_strings[:200],
        'filtered_candidates': filtered,
    }


# Also try: can we get any string variable if we load with mat_dtype?
print('\n\n--- Trying loadmat with mat_dtype=True ---')
fname = sorted(RAW.glob('*.mat'))[0]
try:
    mat = loadmat(str(fname), squeeze_me=True, struct_as_record=False, mat_dtype=True)
    keys = [k for k in mat.keys() if not k.startswith('__')]
    print(f'Keys: {keys}')
    for key in keys:
        val = mat[key]
        print(f'  [{key}] type={type(val).__name__}')
        if hasattr(val, '_fieldnames'):
            for field in val._fieldnames:
                fval = getattr(val, field)
                arr = np.asarray(fval)
                print(f'    .{field}: shape={arr.shape} dtype={arr.dtype}')
                if arr.dtype == object and arr.size < 20:
                    for i, item in enumerate(arr.flat):
                        print(f'      [{i}] type={type(item).__name__} repr={repr(item)[:100]}')
except Exception as e:
    print(f'  Error: {e}')

# Save
out = RESULTS / 'tomato_compressed_strings.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print(f'\nSaved: {out}')
