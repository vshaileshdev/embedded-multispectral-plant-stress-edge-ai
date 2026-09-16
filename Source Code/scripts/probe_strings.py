"""
Probe script: decode MATLAB MCOS string arrays in the tomato dataset.
Tries multiple decoding strategies for treatment/repli/sample fields.
"""
import sys
import io
import json
import pathlib
import numpy as np
from scipy.io import loadmat
from scipy.io.matlab import mat_struct

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RAW = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Source Code/backend/data/raw/tomato')

def try_decode(val, label):
    """Try every known strategy to decode a MATLAB MCOS string object."""
    results = {}
    if val is None:
        return results

    arr = np.asarray(val)

    # Strategy 1: direct str of first element
    try:
        s = str(arr.flat[0]).strip()
        if len(s) < 300:
            results['str_flat0'] = s
    except Exception as e:
        results['str_flat0_err'] = str(e)

    # Strategy 2: structured dtype field inspection
    if arr.dtype.names:
        results['structured_dtype_names'] = list(arr.dtype.names)
        for dn in arr.dtype.names:
            try:
                sub = arr[dn]
                results[f'field_{dn}_shape'] = list(sub.shape)
                results[f'field_{dn}_dtype'] = str(sub.dtype)
                flat_sub = sub.flatten()
                results[f'field_{dn}_val0'] = repr(flat_sub[0])[:200]
                # Try string decode on the uint32 data
                if sub.dtype in [np.uint32, np.uint16, np.int32]:
                    try:
                        raw_bytes = flat_sub.tobytes()
                        decoded_utf16 = raw_bytes.decode('utf-16-le', errors='replace').rstrip('\x00')
                        results[f'field_{dn}_utf16'] = decoded_utf16[:200]
                    except Exception as e2:
                        results[f'field_{dn}_utf16_err'] = str(e2)
            except Exception as e:
                results[f'field_{dn}_err'] = str(e)

    # Strategy 3: object array element inspection
    if arr.dtype == object:
        for i, item in enumerate(arr.flat):
            if i >= 4:
                break
            results[f'obj_item_{i}_type'] = type(item).__name__
            results[f'obj_item_{i}_repr'] = repr(item)[:200]
            if isinstance(item, mat_struct):
                results[f'obj_item_{i}_fields'] = item._fieldnames
            elif hasattr(item, 'tobytes'):
                try:
                    raw_bytes = np.asarray(item).tobytes()
                    results[f'obj_item_{i}_utf16'] = raw_bytes.decode('utf-16-le', errors='replace')[:200]
                except Exception:
                    pass

    # Strategy 4: look for the uint32 MCOS data block and try extracting strings
    # MCOS objects store string data in a uint32 buffer; try reading it directly
    try:
        raw_bytes = arr.tobytes()
        # Try UTF-16 LE (MATLAB default)
        decoded = raw_bytes.decode('utf-16-le', errors='replace')
        # Filter to printable characters
        printable = ''.join(c for c in decoded if c.isprintable() and c != '\x00')
        if printable:
            results['raw_bytes_utf16_printable'] = printable[:300]
    except Exception as e:
        results['raw_bytes_err'] = str(e)

    return results


all_results = {}

for fname in sorted(RAW.glob('*.mat')):
    print(f'\n{"="*60}')
    print(f'FILE: {fname.name}')
    print(f'{"="*60}')

    try:
        mat = loadmat(str(fname), squeeze_me=False, struct_as_record=False)
    except Exception as e:
        print(f'  ERROR: {e}')
        continue

    file_result = {}

    for par_key in ['PAR1000', 'PAR300']:
        if par_key not in mat:
            continue

        struct_obj = mat[par_key][0, 0]
        fields = struct_obj._fieldnames
        print(f'\n  [{par_key}] fields: {fields}')

        # --- Numeric arrays: shapes and quick stats ---
        for numeric_field in ['wvl', 'refl_real', 'trans_real', 'abs_real',
                               'Fup', 'Fdw', 'PAR', 'PARf',
                               'refl_real_smooth', 'trans_real_smooth', 'abs_real_smooth']:
            if numeric_field in fields:
                arr = np.asarray(getattr(struct_obj, numeric_field))
                nan_count = int(np.sum(np.isnan(arr))) if np.issubdtype(arr.dtype, np.number) else 0
                print(f'    {numeric_field:25s} shape={str(arr.shape):15s} '
                      f'dtype={str(arr.dtype):10s} '
                      f'min={float(np.nanmin(arr)):10.4f} max={float(np.nanmax(arr)):10.4f} '
                      f'NaN={nan_count}')

        # --- Wavelength details ---
        if 'wvl' in fields:
            wvl = np.asarray(getattr(struct_obj, 'wvl'))
            # Each row is one spectrum's wavelength axis — check if all rows identical
            if wvl.ndim == 2:
                row_std = np.std(wvl, axis=0)
                wvl_consistent = bool(np.all(row_std < 1e-6))
                wvl_row0 = wvl[0]
                print(f'\n    Wavelength details:')
                print(f'      Rows (spectra): {wvl.shape[0]}')
                print(f'      Bands per spectrum: {wvl.shape[1]}')
                print(f'      All rows identical: {wvl_consistent}')
                print(f'      wvl[0,0]    = {wvl_row0[0]:.4f} nm')
                print(f'      wvl[0,-1]   = {wvl_row0[-1]:.4f} nm')
                print(f'      median step = {float(np.median(np.diff(wvl_row0))):.4f} nm')
                print(f'      First 5 wvl = {[round(v,3) for v in wvl_row0[:5].tolist()]}')
                print(f'      Last  5 wvl = {[round(v,3) for v in wvl_row0[-5:].tolist()]}')
                file_result[f'{par_key}_wvl_bands'] = int(wvl.shape[1])
                file_result[f'{par_key}_wvl_spectra'] = int(wvl.shape[0])
                file_result[f'{par_key}_wvl_min'] = float(wvl_row0[0])
                file_result[f'{par_key}_wvl_max'] = float(wvl_row0[-1])
                file_result[f'{par_key}_wvl_step_median'] = float(np.median(np.diff(wvl_row0)))

        # --- Decode string fields ---
        print(f'\n    String field decoding:')
        for str_field in ['treatment', 'repli', 'sample']:
            if str_field not in fields:
                continue
            val = getattr(struct_obj, str_field)
            print(f'\n    [{str_field}]:')
            decode_result = try_decode(val, str_field)
            for k, v in decode_result.items():
                print(f'      {k}: {str(v)[:120]}')

        # Only print PAR1000 for all files; PAR300 for first file only
        if par_key == 'PAR300' and fname != sorted(RAW.glob('*.mat'))[0]:
            break

    all_results[fname.name] = file_result

# Save raw probe result
RESULTS_DIR = RAW.parent.parent.parent.parent.parent / "Results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
out = RESULTS_DIR / "tomato_string_probe_report.json"
with open(out, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f'\nProbe results saved to: {out}')
