"""
MCOS String Extractor for MATLAB 5.0 .mat files.
=================================================
MATLAB R2016b+ stores string arrays as MCOS objects inside v5 .mat files.
scipy.io.loadmat cannot read these; they appear as opaque uint32 metadata.

This script reads the raw .mat binary and extracts the MCOS subsystem block,
which contains the actual string data as UTF-16 LE encoded text.

Reference: MATLAB Level 5 MAT-file format specification.
MCOS subsystem is stored as a special variable named 'MCOS' with tag 0xDD000000.
"""

import io
import sys
import struct
import pathlib
import json
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RAW = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Source Code/backend/data/raw/tomato')
RESULTS_DIR = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Results')
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# MAT5 data type codes
MAT5_TYPES = {
    1: ('miINT8', 1), 2: ('miUINT8', 1), 3: ('miINT16', 2), 4: ('miUINT16', 2),
    5: ('miINT32', 4), 6: ('miUINT32', 4), 7: ('miSINGLE', 4), 9: ('miDOUBLE', 8),
    12: ('miINT64', 8), 13: ('miUINT64', 8), 14: ('miMATRIX', 0), 15: ('miCOMPRESSED', 0),
    16: ('miUTF8', 1), 17: ('miUTF16', 2), 18: ('miUTF32', 4),
}


def read_mat5_tag(data: bytes, offset: int):
    """Read a MAT5 element tag at the given offset. Returns (data_type, n_bytes, new_offset, is_small)."""
    if offset + 8 > len(data):
        return None, 0, offset, False

    raw = struct.unpack_from('<II', data, offset)
    dt = raw[0] & 0x0000FFFF
    small_size = (raw[0] >> 16) & 0x0000FFFF

    if small_size > 0:
        # Small data element (4 bytes data, packed into tag)
        return dt, small_size, offset + 4, True
    else:
        n_bytes = raw[1]
        return dt, n_bytes, offset + 8, False


def read_bytes(data: bytes, offset: int, n: int) -> tuple:
    """Read n bytes, returning (content, new_offset) with 8-byte alignment."""
    content = data[offset:offset + n]
    pad = (8 - n % 8) % 8
    return content, offset + n + pad


def scan_mat5_for_mcos(mat_bytes: bytes) -> bytes | None:
    """
    Scan a MATLAB 5.0 .mat file binary for the MCOS subsystem block.
    The MCOS subsystem is identified by the special flag 0xDD000000 in the array flags.
    Returns the raw content bytes of the MCOS subsystem, or None if not found.
    """
    offset = 128  # Skip file header

    while offset < len(mat_bytes) - 8:
        dt, n_bytes, data_start, is_small = read_mat5_tag(mat_bytes, offset)

        if dt == 15:  # miCOMPRESSED
            # Skip compressed elements (we are not decompressing here)
            content, next_offset = read_bytes(mat_bytes, data_start, n_bytes)
            offset = next_offset
            continue

        if dt == 14 and not is_small:  # miMATRIX
            element_bytes = mat_bytes[data_start:data_start + n_bytes]

            # Read array flags sub-element
            if len(element_bytes) < 8:
                offset = data_start + n_bytes + (8 - n_bytes % 8) % 8
                continue

            flag_dt, flag_n, flag_start, flag_small = read_mat5_tag(element_bytes, 0)

            if flag_dt == 6 and flag_n >= 8:  # miUINT32 flags
                flag_data = element_bytes[flag_start:flag_start + flag_n]
                if len(flag_data) >= 8:
                    flags = struct.unpack_from('<II', flag_data)
                    class_type = flags[0] & 0xFF
                    flag_byte   = (flags[0] >> 8) & 0xFF
                    # MCOS subsystem has class=0 and a special flag pattern
                    # Check for the MCOS magic: flags[0] high byte = 0xDD
                    mcos_flag = (flags[0] >> 24) & 0xFF
                    if mcos_flag == 0xDD:
                        print(f"  Found MCOS subsystem block at offset {offset}, {n_bytes} bytes")
                        return element_bytes

        # Advance past this element
        if is_small:
            offset = data_start + 4
        else:
            pad = (8 - n_bytes % 8) % 8 if n_bytes % 8 != 0 else 0
            offset = data_start + n_bytes + pad

    return None


def extract_strings_from_utf16_block(raw: bytes) -> list:
    """
    Extract all readable UTF-16 LE strings from a raw binary block.
    Looks for sequences of valid UTF-16 LE characters.
    """
    strings = []
    i = 0
    current = []

    while i < len(raw) - 1:
        # Read a UTF-16 LE code unit
        code_unit = struct.unpack_from('<H', raw, i)[0]

        # Accept printable ASCII range, basic Latin, space, digits
        if (0x0020 <= code_unit <= 0x007E) or code_unit in (0x000A, 0x000D):
            current.append(chr(code_unit))
        else:
            if len(current) >= 2:
                s = ''.join(current).strip()
                if s:
                    strings.append(s)
            current = []
        i += 2

    if current and len(current) >= 2:
        s = ''.join(current).strip()
        if s:
            strings.append(s)

    return strings


def try_all_string_strategies(mat_bytes: bytes, field_name: str) -> list:
    """
    Try to extract strings by scanning the entire mat file for UTF-16 LE text.
    This is a fallback when the MCOS structure cannot be parsed.
    """
    # Strategy: scan whole file for UTF-16 LE encoded readable strings
    strings = extract_strings_from_utf16_block(mat_bytes)
    return strings


def main():
    print("=" * 70)
    print("MCOS STRING EXTRACTION PROBE")
    print("=" * 70)

    all_file_strings = {}

    for fname in sorted(RAW.glob('*.mat')):
        print(f"\n--- {fname.name} ---")
        mat_bytes = fname.read_bytes()
        print(f"  File size: {len(mat_bytes)} bytes")

        # Try to find MCOS subsystem
        mcos_block = scan_mat5_for_mcos(mat_bytes)

        if mcos_block:
            print(f"  Extracting strings from MCOS block ({len(mcos_block)} bytes)...")
            strings = extract_strings_from_utf16_block(mcos_block)
        else:
            print("  MCOS block not found via flag scan. Trying whole-file UTF-16 scan...")
            strings = try_all_string_strategies(mat_bytes, fname.name)

        # Filter to likely label strings (short, not MATLAB internals)
        internal_keywords = {'string', 'char', 'MCOS', 'double', 'single', 'logical',
                             'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16',
                             'uint32', 'uint64', 'cell', 'struct', 'function_handle',
                             'matlab', 'repmat', 'end', 'Inf', 'NaN', 'true', 'false'}

        candidate_labels = []
        for s in strings:
            s_clean = s.strip()
            if 1 < len(s_clean) < 60 and s_clean not in internal_keywords:
                candidate_labels.append(s_clean)

        # Deduplicate preserving order
        seen = set()
        unique_labels = []
        for s in candidate_labels:
            if s not in seen:
                seen.add(s)
                unique_labels.append(s)

        print(f"  Candidate strings found ({len(unique_labels)}):")
        for s in unique_labels[:40]:
            print(f"    {repr(s)}")

        all_file_strings[fname.name] = unique_labels

    # Save
    out = RESULTS_DIR / "tomato_mcos_strings.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_file_strings, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved: {out}")


if __name__ == "__main__":
    main()
