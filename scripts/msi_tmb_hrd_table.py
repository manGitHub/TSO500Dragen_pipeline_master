#!/usr/bin/env python3
"""
msi_tmb_hrd_table.py
--------------------
Scrapes MSI, TMB, and HRD/GIS values from TSO500 per-sample output and writes an
Excel workbook matching the QC table format.
Usage (called from workflow.onComplete in main.nf):
    python3 scripts/msi_tmb_hrd_table.py \
        --tso_outdir <params.tso_outdir> \
        --run_folder <params.run_folder> \
        --out_dir    <launchDir>/metadata/<params.run_folder> \
        --samples    <newline-separated sample IDs string>
"""
import argparse
import csv
import json
import sys
from pathlib import Path
try:
    import openpyxl
except ImportError:
    sys.exit("ERROR: openpyxl is required.  pip install openpyxl")
# ── File-path templates (relative to tso_outdir/<pair_id>/) ──────────────────
TMB_GLOB = "Logs_Intermediates/Tmb/{sample}/{sample}.tmb.metrics.csv"
MSI_GLOB = "Results/{pair_id}/{sample}/{sample}.microsat_output.json"
HRD_GLOB = "Results/{pair_id}/{sample}/{sample}.gis.json"

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--tso_outdir", required=True, help="params.tso_outdir")
    p.add_argument("--run_folder", required=True, help="params.run_folder")
    p.add_argument("--out_dir",    required=True, help="Directory to write the Excel file")
    p.add_argument("--samples",    required=True, help="Newline-separated sample IDs string")
    return p.parse_args()

def load_samples(samples_str: str):
    """
    Return a list of (pair_id, sample_id) tuples from a newline-separated string.
    pair_id is derived by appending _NoPair to each sample_id.
    """
    samples = []
    for sample_id in samples_str.splitlines():
        sample_id = sample_id.strip()
        if sample_id:
            samples.append((f"{sample_id}_NoPair", sample_id))
    return samples

def read_tmb(pair_dir: Path, sample_id: str) -> str:
    path = pair_dir / TMB_GLOB.format(sample=sample_id)
    if not path.exists():
        return "N/A"
    with path.open(newline="") as fh:
        for row in csv.reader(fh):
            if len(row) >= 4 and row[2].strip() == "Nonsyn TMB":
                return row[3].strip()
    return "N/A"

def read_msi(pair_dir: Path, sample_id: str, pair_id: str) -> str:
    path = pair_dir / MSI_GLOB.format(pair_id=pair_id, sample=sample_id)
    if not path.exists():
        return "N/A"
    with path.open() as fh:
        data = json.load(fh)
    val = data.get("PercentageUnstableSites", "N/A")
    try:
        return str(round(float(val), 2))
    except (TypeError, ValueError):
        return str(val)

def read_hrd(pair_dir: Path, sample_id: str, pair_id: str) -> str:
    path = pair_dir / HRD_GLOB.format(pair_id=pair_id, sample=sample_id)
    if not path.exists():
        return "N/A"
    with path.open() as fh:
        data = json.load(fh)
    val = data.get("MYRIAD", {}).get("score", {}).get("GIS", "N/A")
    try:
        return str(round(float(val), 2))
    except (TypeError, ValueError):
        return str(val)


def write_excel(sample_ids, msi_vals, tmb_vals, hrd_vals, out_path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MSI_TMB"
    # Row 1: MSI header
    ws.append([""] + sample_ids)
    # Row 2: MSI values
    ws.append(["MSI - PercentageUnstableSites"] + msi_vals)
    # Row 3: spacer
    ws.append([])
    # Row 4: TMB header
    ws.append([""] + sample_ids)
    # Row 5: TMB values
    ws.append(["TMB - NonsynTMB"] + tmb_vals)
    # Row 6: spacer
    ws.append([])
    # Row 7: HRD header
    ws.append([""] + sample_ids)
    # Row 8: HRD values
    ws.append(["HRD"] + hrd_vals)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"Wrote: {out_path}")

def main():
    args   = parse_args()
    tso    = Path(args.tso_outdir)
    outdir = Path(args.out_dir)
    if not tso.is_dir():
        sys.exit(f"ERROR: tso_outdir not found: {tso}")
    samples = load_samples(args.samples)
    if not samples:
        sys.exit(f"ERROR: No samples found under {tso}")
    sample_ids, msi_vals, tmb_vals, hrd_vals = [], [], [], []
    for pair_id, sample_id in samples:
        pair_dir = tso / pair_id
        sample_ids.append(sample_id)
        msi_vals.append(read_msi(pair_dir, sample_id, pair_id))
        tmb_vals.append(read_tmb(pair_dir, sample_id))
        hrd_vals.append(read_hrd(pair_dir, sample_id, pair_id))
        print(f"  {sample_id}: MSI={msi_vals[-1]}  TMB={tmb_vals[-1]}  HRD={hrd_vals[-1]}")
    xlsx_name = f"MSI_TMB_HRD_{args.run_folder}.xlsx"
    write_excel(sample_ids, msi_vals, tmb_vals, hrd_vals, outdir / xlsx_name)

if __name__ == "__main__":
    main()
