# This script combines the results from TSO500 app of all the samples, plus the demux run qc
# Structure is derived from the sample MetricsOutput.tsv files (identical across samples).
# args:
# 1: excel output file name
# 2: path to output directory
# 3: run QC json from demux dir
# 4: Comma separated list of TSO500 summary files *MetricsOutput.tsv

# Usage: python3 merge_TSO500_QC.py TSO500_QC.xlsx /path/to/output/dir runQCjson [Comma separated list of files]
import pandas as pd
import csv
import sys
import json
from collections import OrderedDict

path = ','.join(sys.argv[4:])
mypath = path.split(",")
qc = sys.argv[2]
##path to qc report
file = sys.argv[1]

# --- Parse each MetricsOutput.tsv into (sample_name, {section: OrderedDict{metric: value}}) ---
# Structure is assumed identical across files; first file drives row order.

SKIP_METRICS = {'Metric (UOM)', 'Output Date', 'Output Time', 'Workflow Version', 'Run Metrics'}
SKIP_SECTIONS = {'[Header]', '[Notes]'}

def parse_metrics_tsv(filepath):
    """Return (sample_name, {section: OrderedDict{metric: value}})."""
    sections = OrderedDict()
    sample_name = None
    current_section = None

    with open(filepath, 'r') as fh:
        for line in fh:
            parts = line.rstrip('\n').split('\t')
            while len(parts) < 4:
                parts.append('')

            col0 = parts[0].strip()
            col1 = parts[1].strip()
            col3 = parts[3].strip()

            # Section header
            if col0.startswith('['):
                current_section = col0
                if current_section not in SKIP_SECTIONS and current_section not in sections:
                    sections[current_section] = OrderedDict()
                continue

            if current_section is None or current_section in SKIP_SECTIONS:
                continue

            # Sample name line (col0 empty, col1 is the sample name)
            if not col0 and col1 and not col1.startswith('['):
                if sample_name is None:
                    sample_name = col1
                continue

            # Skip non-data rows
            if not col0 or col0 in SKIP_METRICS:
                continue

            metric = col0
            lsl    = parts[1].strip()
            usl    = parts[2].strip()
            value  = col3
            lsl    = '' if lsl   == 'NA' else lsl
            usl    = '' if usl   == 'NA' else usl
            value  = '' if value == 'NA' else value

            # [Analysis Status] values are in col 1 (e.g. COMPLETED_ALL_STEPS TRUE)
            if current_section == '[Analysis Status]' and not value:
                value = lsl
                lsl   = ''

            # Within each section keep first occurrence of a metric
            if metric not in sections[current_section]:
                sections[current_section][metric] = (lsl, usl, value)

    return sample_name, sections

sample_names = []
all_sections = []   # list of {section: {metric: value}}, one per file
for f in mypath:
    sname, sdict = parse_metrics_tsv(f)
    sample_names.append(sname)
    all_sections.append(sdict)

n_samples = len(sample_names)

# Use first file as the structural blueprint
blueprint = all_sections[0]

# --- Load the run QC json ---
with open(sys.argv[3], "r", encoding="utf-8") as f:
    run_json = json.loads(f.read())

run_qc_values = {
    'PCT_PF_READS (%)': run_json["ReadsPercentPfResult"]["ConvertedStat"],
    'PCT_Q30_R1 (%)':   run_json["R1PercentQ30Result"]["ConvertedStat"],
    'PCT_Q30_R2 (%)':   run_json["R2PercentQ30Result"]["ConvertedStat"],
}

# --- Build output rows ---
# Columns: [Metric, LSL, USL, <blank separator>, sample1, sample2, ...]

def blank_row():
    return [''] * (4 + n_samples)

rows = []

# Run QC block: single value column (from json), no per-sample breakdown
rows.append(['[Run QC Metrics]'] + [''] * (3 + n_samples))
rows.append(['Metric (UOM)', 'LSL Guideline', 'USL Guideline', 'Value'] + [''] * n_samples)
for metric, val in run_qc_values.items():
    rows.append([metric, '', '', val] + [''] * n_samples)
rows.append(blank_row())

# All other sections from the TSV structure
for section, metrics in blueprint.items():
    if section == '[Run QC Metrics]':
        continue  # already emitted above from json

    rows.append([section] + [''] * (3 + n_samples))

    if section == '[Analysis Status]':
        # Sample name sub-header row
        rows.append([''] + [''] * 3 + sample_names)
        # Fixed status rows — pull from each sample's section
        for metric, (lsl, usl, _) in metrics.items():
            vals = [sdict.get(section, {}).get(metric, ('', '', ''))[2] for sdict in all_sections]
            rows.append([metric, lsl, usl, ''] + vals)
        rows.append(blank_row())
        continue

    # Standard section: Metric (UOM) header + data rows
    rows.append(['Metric (UOM)', 'LSL Guideline', 'USL Guideline', ''] + sample_names)
    for metric, (lsl, usl, _) in metrics.items():
        vals = [sdict.get(section, {}).get(metric, ('', '', ''))[2] for sdict in all_sections]
        rows.append([metric, lsl, usl, ''] + vals)
    rows.append(blank_row())

df_final = pd.DataFrame(rows)
df_final.to_excel(qc + file, index=False, header=False, sheet_name="Run_metrics")
