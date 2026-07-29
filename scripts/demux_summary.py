#!/usr/bin/env python3
"""
demux_summary.py  –  Reformat a single DRAGEN Demultiplex_Stats.csv into the
                      three-section lane/sample/breakdown report used by the
                      TSO500 NextFlow pipeline.

Usage:
    python3 demux_summary.py <demux_stats_csv> <out_dir> <run_folder_name>

Output:
    <out_dir>/<run_folder_name>.csv
"""

import sys
import os
import pandas as pd


def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: demux_summary.py <demux_stats_csv> <out_dir> <run_folder_name>")

    in_csv   = sys.argv[1]
    out_dir  = sys.argv[2]
    run_name = sys.argv[3]

    out_path = os.path.join(out_dir, f"{run_name}.csv")
    os.makedirs(out_dir, exist_ok=True)

    # ── Load ──────────────────────────────────────────────────────────────────
    dat = pd.read_csv(in_csv)

    # ── Lane Summary ──────────────────────────────────────────────────────────
    lane_agg = (
        dat.groupby('Lane')
           .agg({
               '# Reads':                    'sum',
               '# Perfect Index Reads':      'sum',
               '# One Mismatch Index Reads': 'sum',
               '# Two Mismatch Index Reads': 'sum',
           })
           .reset_index()
    )
    tot_reads = lane_agg['# Reads'].sum()
    lane_agg['% of the lane']               = lane_agg['# Reads']                    / tot_reads * 100
    lane_agg['% Perfect Index Reads']       = lane_agg['# Perfect Index Reads']      / lane_agg['# Reads'] * 100
    lane_agg['% One Mismatch Index Reads']  = lane_agg['# One Mismatch Index Reads'] / lane_agg['# Reads'] * 100
    lane_agg['% Two Mismatch Index Reads']  = lane_agg['# Two Mismatch Index Reads'] / lane_agg['# Reads'] * 100

    lane_cols = [
        'Lane', '# Reads', '% of the lane',
        '# Perfect Index Reads',      '% Perfect Index Reads',
        '# One Mismatch Index Reads', '% One Mismatch Index Reads',
        '# Two Mismatch Index Reads', '% Two Mismatch Index Reads',
    ]
    lane_agg = lane_agg[lane_cols]

    # ── Sample Summary ────────────────────────────────────────────────────────
    samp_agg = (
        dat.groupby(['SampleID', 'Index'])
           .agg({
               '# Reads':                    'sum',
               '# Perfect Index Reads':      'sum',
               '# One Mismatch Index Reads': 'sum',
               '# Two Mismatch Index Reads': 'sum',
           })
           .reset_index()
    )
    tot_reads = samp_agg['# Reads'].sum()
    samp_agg['% of the lane']               = samp_agg['# Reads']                    / tot_reads * 100
    samp_agg['% Perfect Index Reads']       = samp_agg['# Perfect Index Reads']      / samp_agg['# Reads'] * 100
    samp_agg['% One Mismatch Index Reads']  = samp_agg['# One Mismatch Index Reads'] / samp_agg['# Reads'] * 100
    samp_agg['% Two Mismatch Index Reads']  = samp_agg['# Two Mismatch Index Reads'] / samp_agg['# Reads'] * 100

    samp_cols = [
        'SampleID', 'Index', '# Reads', '% of the lane',
        '# Perfect Index Reads',      '% Perfect Index Reads',
        '# One Mismatch Index Reads', '% One Mismatch Index Reads',
        '# Two Mismatch Index Reads', '% Two Mismatch Index Reads',
    ]
    samp_agg = samp_agg[samp_cols]

    # ── Breakdown by Lane and Barcode ─────────────────────────────────────────
    tot_reads = dat['# Reads'].sum()
    dat = dat.copy()
    dat['% of the lane']               = dat['# Reads']                    / tot_reads * 100
    dat['% Perfect Index Reads']       = dat['# Perfect Index Reads']      / dat['# Reads'] * 100
    dat['% One Mismatch Index Reads']  = dat['# One Mismatch Index Reads'] / dat['# Reads'] * 100
    dat['% Two Mismatch Index Reads']  = dat['# Two Mismatch Index Reads'] / dat['# Reads'] * 100

    breakdown_cols = [
        'Lane', 'SampleID', 'Index', '# Reads', '% of the lane',
        '# Perfect Index Reads',      '% Perfect Index Reads',
        '# One Mismatch Index Reads', '% One Mismatch Index Reads',
        '# Two Mismatch Index Reads', '% Two Mismatch Index Reads',
    ]
    dat = dat[breakdown_cols]

    # ── Write ─────────────────────────────────────────────────────────────────
    with open(out_path, 'w') as fh:
        fh.write('Lane Summary\n')
        fh.write(lane_agg.to_csv(index=False) + '\n')
        fh.write('Sample Summary\n')
        fh.write(samp_agg.to_csv(index=False) + '\n')
        fh.write('Breakdown by Lane and Barcode\n')
        fh.write(dat.to_csv(index=False))

    print(f"Wrote demux summary: {out_path}")
    return out_path


if __name__ == '__main__':
    main()
