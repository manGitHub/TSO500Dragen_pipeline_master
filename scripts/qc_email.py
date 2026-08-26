#!/usr/bin/env python3
"""
qc_email.py  —  summarise per-sample TSO500 [Analysis Status] metrics.
Usage:
    python3 scripts/qc_email.py <tso_outdir> [--pairs <pair_ids>]
                                              [--out <output_txt>]
                                              [--metrics-file <filename>]
                                              [--completed-metric <name>]
                                              [--failed-metric <name>]
Defaults:
    --out              metrics_table.txt
    --metrics-file     MetricsOutput.tsv
    --completed-metric COMPLETED_ALL_STEPS
    --failed-metric    FAILED_STEPS
"""
import argparse
import sys
from pathlib import Path

# Column widths for the output table
COL_WIDTHS = { "sample": 44, "label": 24, "bool": 8, "failed_lbl": 16 }

# Defaults
DEFAULT_METRICS_FILE     = "MetricsOutput.tsv"
DEFAULT_COMPLETED_METRIC = "COMPLETED_ALL_STEPS"
DEFAULT_FAILED_METRIC    = "FAILED_STEPS"
ANALYSIS_STATUS_SECTION  = "[Analysis Status]"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("tso_outdir",         type=Path)
    p.add_argument("--pairs",            type=str, default="")
    p.add_argument("--out",              type=Path, default=Path("metrics_table.txt"))
    p.add_argument("--metrics-file",     type=str, default=DEFAULT_METRICS_FILE)
    p.add_argument("--completed-metric", type=str, default=DEFAULT_COMPLETED_METRIC)
    p.add_argument("--failed-metric",    type=str, default=DEFAULT_FAILED_METRIC)
    return p.parse_args()


def parse_status(metrics_file: Path, completed_metric: str, failed_metric: str) -> dict:
    """Return sample name, completed status, and failed steps from [Analysis Status]."""
    lines = metrics_file.read_text().splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith(ANALYSIS_STATUS_SECTION))
    except StopIteration:
        return None
    sample    = next((t for t in lines[start + 1].split("\t") if t.strip()), metrics_file.parts[-3])
    completed = failed = "NA"
    for line in lines[start + 2:]:
        if line.startswith("["): break
        parts  = line.split("\t")
        metric = parts[0].strip()
        value  = parts[1].strip() if len(parts) > 1 else "NA"
        if metric == completed_metric: completed = value
        if metric == failed_metric:    failed    = value
    return {"sample": sample, "completed": completed, "failed": failed}


def build_table(samples: list, completed_metric: str, failed_metric: str) -> str:
    """Build a fixed-width text table of per-sample analysis status results."""
    w      = COL_WIDTHS
    header = f"  {'SAMPLE':<{w['sample']}}{completed_metric:<{w['label']}}{'VALUE':<{w['bool']}}{failed_metric:<{w['failed_lbl']}}VALUE"
    sep    = "  " + "-" * (sum(w.values()) + 5)
    rows   = [header, sep]
    for s in samples:
        rows.append(f"  {s['sample']:<{w['sample']}}{completed_metric:<{w['label']}}{s['completed']:<{w['bool']}}{failed_metric:<{w['failed_lbl']}}{s['failed']}")
    return "\n".join(rows)


def main():
    args     = parse_args()
    pair_ids = set(args.pairs.split()) if args.pairs.strip() else None
    if pair_ids is None:
        sys.exit("ERROR: --pairs was empty; refusing to report on all samples in tso_outdir")

    # Check for expected pair IDs with no metrics file
    missing = []
    if pair_ids:
        missing = sorted(pid for pid in pair_ids
                         if not (args.tso_outdir / pid / "Results" / args.metrics_file).exists())
        if missing:
            print(f"WARNING: {args.metrics_file} not found for: {', '.join(missing)}", file=sys.stderr)

    samples = [r for f in sorted(args.tso_outdir.glob(f"*/Results/{args.metrics_file}"))
               if (not pair_ids or f.parts[-3] in pair_ids)
               and (r := parse_status(f, args.completed_metric, args.failed_metric))]

    # append a MISSING row for each sample with no metrics file
    for pid in missing:
        samples.append({"sample": pid, "completed": "MISSING", "failed": "NA"})

    if not samples:
        args.out.write_text("  (metrics summary was empty)\n")
        sys.exit(0)

    args.out.write_text(build_table(samples, args.completed_metric, args.failed_metric) + "\n")


if __name__ == "__main__":
    main()
