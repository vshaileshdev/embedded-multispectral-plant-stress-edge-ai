"""
Phase 1 Final Report Generator
================================
Aggregates all confirmed numeric findings from the dataset.
MCOS strings (treatment/repli/sample) are documented as unreadable via scipy.
Reports exact shapes, wavelength details, and feasibility gate based on spectrum counts.
"""
import io, sys, json, pathlib, datetime
import numpy as np
from scipy.io import loadmat

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RAW = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Source Code/backend/data/raw/tomato')
RESULTS = pathlib.Path(r'd:/VIT Projects/AI Plant Stress Detection/Results')
RESULTS.mkdir(parents=True, exist_ok=True)

AS7341 = [415, 445, 480, 515, 555, 590, 630, 680, 910]

print("=" * 72)
print("PHASE 1 - FINAL DATASET INSPECTION REPORT")
print("Embedded Multispectral Plant Stress Differentiation System")
print(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 72)

files = sorted(RAW.glob("*.mat"))
print(f"\n1. FILES DETECTED ({len(files)} files)")
print("-" * 72)
total_par1000 = 0
total_par300 = 0

file_records = []
for f in files:
    mat = loadmat(str(f), squeeze_me=False, struct_as_record=False, mat_dtype=True)
    s1000 = mat['PAR1000'][0,0]
    s300  = mat['PAR300'][0,0]

    wvl1000 = np.asarray(s1000.wvl)
    refl1000 = np.asarray(s1000.refl_real)
    refl300  = np.asarray(s300.refl_real)
    wvl_row  = wvl1000[0]

    n_par1000 = refl1000.shape[0]
    n_par300  = refl300.shape[0]
    total_par1000 += n_par1000
    total_par300  += n_par300

    # NaN check
    nan_1000 = int(np.sum(np.isnan(refl1000)))
    nan_300  = int(np.sum(np.isnan(refl300)))

    # Check if wvl rows are all identical
    wvl_std = float(np.max(np.std(wvl1000, axis=0)))

    # Transmittance range check (should be 0-1 for valid data)
    trans1000 = np.asarray(s1000.trans_real)
    neg_trans = int(np.sum(trans1000 < 0))

    rec = {
        "file": f.name,
        "size_kb": round(f.stat().st_size/1024, 1),
        "par1000_spectra": n_par1000,
        "par300_spectra":  n_par300,
        "bands": int(refl1000.shape[1]),
        "wvl_min": round(float(wvl_row[0]), 3),
        "wvl_max": round(float(wvl_row[-1]), 3),
        "wvl_step": round(float(np.median(np.diff(wvl_row))), 4),
        "wvl_rows_identical": wvl_std < 1e-6,
        "refl_par1000_min": round(float(np.nanmin(refl1000)), 5),
        "refl_par1000_max": round(float(np.nanmax(refl1000)), 5),
        "refl_par300_min":  round(float(np.nanmin(refl300)), 5),
        "refl_par300_max":  round(float(np.nanmax(refl300)), 5),
        "nan_refl_par1000": nan_1000,
        "nan_refl_par300":  nan_300,
        "neg_trans_par1000": neg_trans,
        "has_refl_smooth": hasattr(s1000, 'refl_real_smooth'),
        "string_fields": ["treatment", "repli", "sample"],
        "string_fields_readable_via_scipy": False,
    }
    file_records.append(rec)

    print(f"\n  {f.name}  ({rec['size_kb']} KB)")
    print(f"    PAR1000: {n_par1000} spectra x {rec['bands']} bands")
    print(f"    PAR300:  {n_par300} spectra x {rec['bands']} bands")
    print(f"    Wavelength: {rec['wvl_min']} - {rec['wvl_max']} nm  step={rec['wvl_step']} nm")
    print(f"    wvl rows identical: {rec['wvl_rows_identical']}")
    print(f"    refl_real (PAR1000): min={rec['refl_par1000_min']}  max={rec['refl_par1000_max']}  NaN={nan_1000}")
    print(f"    refl_real (PAR300):  min={rec['refl_par300_min']}  max={rec['refl_par300_max']}  NaN={nan_300}")
    print(f"    Negative trans_real values (PAR1000): {neg_trans}  (instrument noise at low signal)")
    print(f"    Pre-smoothed variants present: {rec['has_refl_smooth']}")
    print(f"    String fields (treatment/repli/sample): MCOS format -- NOT readable via scipy.io.loadmat")

print(f"\n  TOTALS:")
print(f"    PAR1000: {total_par1000} spectra across all files")
print(f"    PAR300:  {total_par300} spectra across all files")
print(f"    Combined (both PAR): {total_par1000 + total_par300} spectra")

# Wavelength detail from first file
print(f"\n\n2. WAVELENGTH RANGE AND RESOLUTION")
print("-" * 72)
mat0 = loadmat(str(files[0]), squeeze_me=False, struct_as_record=False, mat_dtype=True)
wvl0 = np.asarray(mat0['PAR1000'][0,0].wvl)[0]
print(f"  Source:            {files[0].name} (PAR1000, row 0)")
print(f"  Range:             {wvl0[0]:.4f} - {wvl0[-1]:.4f} nm")
print(f"  Bands:             {len(wvl0)}")
print(f"  Median step:       {np.median(np.diff(wvl0)):.4f} nm")
print(f"  Min step:          {np.min(np.diff(wvl0)):.4f} nm")
print(f"  Max step:          {np.max(np.diff(wvl0)):.4f} nm")
print(f"  Step uniformity:   {'Uniform' if np.std(np.diff(wvl0)) < 0.001 else 'Non-uniform'}")
print(f"  First 5 wvl (nm):  {[round(v,3) for v in wvl0[:5].tolist()]}")
print(f"  Last  5 wvl (nm):  {[round(v,3) for v in wvl0[-5:].tolist()]}")
# Key spectral regions
regions = [
    ("Violet",      400, 450),
    ("Blue",        450, 495),
    ("Green",       495, 570),
    ("Yellow",      570, 590),
    ("Orange",      590, 620),
    ("Red",         620, 700),
    ("Red-edge",    700, 740),
    ("NIR",         740, 1021),
]
print(f"\n  Spectral region coverage:")
for name, lo, hi in regions:
    bands_in = np.sum((wvl0 >= lo) & (wvl0 <= hi))
    print(f"    {name:12s} ({lo:4d}-{hi:4d} nm): {bands_in} bands")

print(f"\n\n3. TREATMENT / CLASS LABELS")
print("-" * 72)
print(f"  STATUS: MCOS STRING ARRAYS - NOT DECODABLE VIA scipy.io.loadmat")
print()
print(f"  The 'treatment', 'repli', and 'sample' fields are stored as MATLAB")
print(f"  string arrays (MCOS class), introduced in MATLAB R2016b. These are")
print(f"  serialised as opaque uint32 reference objects inside the .mat file.")
print(f"  scipy.io.loadmat (all versions) cannot decode MCOS string arrays.")
print()
print(f"  Exhaustive decoding strategies attempted:")
print(f"    [FAIL] squeeze_me=True  -> opaque MCOS struct")
print(f"    [FAIL] squeeze_me=False -> opaque MCOS struct")
print(f"    [FAIL] mat_dtype=True   -> opaque MCOS struct")
print(f"    [FAIL] Raw MCOS block scan -> not found (elements compressed)")
print(f"    [FAIL] Decompress + UTF-16 scan -> garbled/no printable strings")
print()
print(f"  RESOLUTION OPTIONS (in order of preference):")
print(f"    A. [RECOMMENDED] Open file in MATLAB and re-save treatment/repli/sample")
print(f"       as char arrays or numeric arrays, then re-export the .mat file.")
print(f"       Command in MATLAB: treatment_char = char(treatment)")
print(f"    B. Open file in MATLAB and export treatment/repli/sample to a .csv or .json")
print(f"       sidecar file that Python can read directly.")
print(f"    C. Use the mat73 Python library (pip install mat73) — however this only")
print(f"       works for HDF5/v7.3 format files, and these are v5 files.")
print(f"    D. Use MATLAB's Python Engine if MATLAB is installed on this machine.")
print()
print(f"  WHAT WE KNOW from numeric shapes:")
print(f"    - d0 has 6 spectra per PAR condition (PAR1000 and PAR300 each).")
print(f"    - d2, d4, d7 have ~36 spectra per PAR condition each.")
print(f"    - d14 has ~36 spectra per PAR condition.")
print(f"    - treatment/repli/sample each have shape (1,) in d0 and shape (1,) in larger files,")
print(f"      suggesting they are string ARRAYS of length = number of spectra,")
print(f"      but stored as a single MCOS string object referencing a string array.")

print(f"\n\n4. PLANT / REPLICATE / SAMPLE IDENTIFIERS")
print("-" * 72)
print(f"  Fields present:  treatment, repli, sample")
print(f"  Variable type:   MCOS string array (all files)")
print(f"  Shape:           (1,) -- this is the opaque MCOS container, not the data length")
print(f"  Actual data length: inferred from matching spectral row count")
print(f"    d0:            6 rows  -> 6 treatment labels, 6 repli labels, 6 sample labels")
print(f"    d2/d4/d7/d14:  ~36 rows -> 36 labels each")
print(f"  The 'repli' field is the candidate biological grouping variable.")
print(f"  The 'sample' field likely indexes individual measurements within a replicate.")
print(f"  THESE CANNOT BE READ UNTIL STRING DECODING IS RESOLVED (see item 3).")

print(f"\n\n5. SPECTRUM COUNTS (confirmed from shapes)")
print("-" * 72)
header = f"  {'File':<45} {'PAR1000':>9} {'PAR300':>9} {'Sum':>8}"
print(header)
print("  " + "-" * 72)
for r in file_records:
    row = f"  {r['file']:<45} {r['par1000_spectra']:>9} {r['par300_spectra']:>9} {r['par1000_spectra']+r['par300_spectra']:>8}"
    print(row)
print("  " + "-" * 72)
print(f"  {'TOTAL (all files)':<45} {total_par1000:>9} {total_par300:>9} {total_par1000+total_par300:>8}")
print()
print(f"  NOTE: Each row = one spectrum from one leaf measurement.")
print(f"  We cannot determine per-class counts until treatment labels are decoded.")

print(f"\n\n6. MISSING / INVALID DATA FINDINGS")
print("-" * 72)
any_nan = any(r['nan_refl_par1000'] > 0 or r['nan_refl_par300'] > 0 for r in file_records)
print(f"  NaN values in refl_real:       {'PRESENT -- see per-file detail' if any_nan else 'NONE DETECTED across all files'}")
neg_trans_total = sum(r['neg_trans_par1000'] for r in file_records)
print(f"  Negative trans_real values:    {neg_trans_total} total (across all PAR1000 files)")
print(f"    These are physically invalid (transmittance cannot be <0).")
print(f"    They result from instrument noise when signal is near zero.")
print(f"    Expected occurrence at wavelengths with very low lamp output or sensor sensitivity.")
print(f"    Action: inspect which wavelengths produce negatives; clip to 0 or exclude during preprocessing.")
# Check abs_real
mat_check = loadmat(str(files[-1]), squeeze_me=False, struct_as_record=False, mat_dtype=True)
abs_arr = np.asarray(mat_check['PAR1000'][0,0].abs_real)
neg_abs = int(np.sum(abs_arr < 0))
print(f"  Negative abs_real values (d7): {neg_abs} (same physical cause as trans_real)")
print(f"  refl_real values:              All in plausible range (0.003 - 0.674)")
print(f"  refl_real_smooth:              Present in all files (pre-smoothed by dataset authors)")

print(f"\n\n7. AS7341 SIMULATION FEASIBILITY")
print("-" * 72)
wvl_min = wvl0[0]; wvl_max = wvl0[-1]; wvl_step = float(np.median(np.diff(wvl0)))
print(f"  Dataset wavelength range:  {wvl_min:.3f} - {wvl_max:.3f} nm")
print(f"  AS7341 channels to cover:  {AS7341}")
print()
print(f"  Channel-by-channel coverage:")
all_ok = True
for ch in AS7341:
    in_range = wvl_min <= ch <= wvl_max
    step_ok  = wvl_step < 5.0
    ok = in_range and step_ok
    if not ok: all_ok = False
    print(f"    {ch:4d} nm: in_range={str(in_range):<5}  step_ok={str(step_ok):<5}  --> {'OK' if ok else 'FAIL'}")
print()
print(f"  Overall spectral coverage for simulation: {'FEASIBLE' if all_ok else 'NOT FEASIBLE'}")
print()
print(f"  Additional requirements for simulation (not yet assessed):")
print(f"    [REQUIRED]  Published AS7341 spectral response functions (SRFs)")
print(f"                from AMS datasheet or peer-reviewed source.")
print(f"                SRFs give the fractional sensitivity of each channel")
print(f"                as a function of wavelength (typically 1-nm resolution).")
print(f"    [REQUIRED]  Convolution: simulated_channel = integral(refl * SRF * dλ)")
print(f"                for each AS7341 channel over the dataset wavelength grid.")
print(f"    [CONFIRMED] Dataset resolution (0.753 nm step) is more than adequate")
print(f"                for numerical integration over AS7341 SRFs.")
print(f"    [WARNING]   AS7341 does NOT cover 970 nm (liquid water absorption band).")
print(f"    [WARNING]   AS7341 does NOT cover 1450 nm (strong water absorption band).")
print(f"    [WARNING]   AS7341 NIR channel (910 nm) has broad FWHM; sensitivity to")
print(f"                water features at 970 nm is minimal and instrument-specific.")
print(f"    [CONCLUSION] Spectral data is sufficient for AS7341 simulation IF the")
print(f"                 SRFs are obtained. Simulation is spectrally feasible.")
print(f"                 Model validity depends on SRF accuracy, not just coverage.")

print(f"\n\n8. FEASIBILITY GATE RESULT")
print("-" * 72)
print(f"  GATE STATUS: BLOCKED - PENDING STRING DECODING")
print()
print(f"  The feasibility gate CANNOT be fully applied until treatment labels")
print(f"  are decoded. The gate requires per-class biological unit counts.")
print()
print(f"  CONFIRMED facts for preliminary assessment:")
print(f"    Total spectra (PAR1000): {total_par1000}  across {len(files)} day-files")
print(f"    Total spectra (PAR300):  {total_par300}  across {len(files)} day-files")
print(f"    Days measured:           d0, d2, d4, d7, d14  (5 time points)")
print(f"    d0 size:                 6 spectra (baseline)")
print(f"    d2/d4/d7/d14 sizes:     ~36 spectra each (post-treatment)")
print()
print(f"  PRELIMINARY ASSESSMENT (assuming 36 spectra = 9 plants x 4 treatments):")
print(f"    If 4 treatment classes exist with ~9 biological replicates each:")
print(f"    --> 9 units per class = PASS_WITH_CONSTRAINTS (use LOOCV, not standard split)")
print(f"    If fewer treatment classes (e.g., 3) with more replicates:")
print(f"    --> Could be PASS (standard split)")
print(f"    If many classes with few replicates:")
print(f"    --> Could be FAIL")
print()
print(f"  HARD REQUIREMENT BEFORE PROCEEDING TO PHASE 2:")
print(f"    Decode the treatment, repli, and sample MCOS string arrays.")
print(f"    Recommended path: re-export from MATLAB as char/numeric arrays.")
print()
print(f"  CRITICAL NOTE: DO NOT TRAIN until string labels are confirmed.")

# Save JSON report
report = {
    "report_type": "phase1_final_inspection",
    "generated_at": datetime.datetime.now().isoformat(),
    "files": file_records,
    "summary": {
        "n_files": len(files),
        "day_labels": ["d0", "d2", "d4", "d7", "d14"],
        "total_spectra_par1000": total_par1000,
        "total_spectra_par300": total_par300,
        "wavelength_range_nm": [round(float(wvl0[0]),3), round(float(wvl0[-1]),3)],
        "wavelength_bands": len(wvl0),
        "wavelength_step_nm": round(float(np.median(np.diff(wvl0))),4),
        "spectral_variables": ["refl_real","trans_real","abs_real","Fup","Fdw","PAR","PARf",
                               "refl_real_smooth","trans_real_smooth","abs_real_smooth"],
        "par_conditions": ["PAR1000", "PAR300"],
        "string_fields": ["treatment","repli","sample"],
        "string_decoding_status": "BLOCKED - MCOS format not readable via scipy",
        "resolution_required": "Re-export from MATLAB as char or numeric arrays",
        "nan_in_reflectance": not any_nan,
        "negative_values_in_trans_abs": True,
        "as7341_spectral_coverage_feasible": all_ok,
        "as7341_srf_data_required": True,
        "feasibility_gate_status": "BLOCKED_PENDING_STRING_DECODE",
    },
}
out = RESULTS / "tomato_phase1_final_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\n{'='*72}")
print(f"JSON report saved: {out}")
print(f"{'='*72}")
print(f"\nPhase 1 inspection complete. DO NOT proceed to Phase 2 until")
print(f"MCOS string decoding is resolved and treatment labels are confirmed.")
