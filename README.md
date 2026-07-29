# DRAGEN TSO500 Nextflow Pipeline

Nextflow pipeline for demultiplexing and per-sample TSO500 analysis using DRAGEN on the NIH Biowulf HPC cluster.

---

## Overview

This pipeline automates the following steps for a given sequencing run:

1. **Demultiplexing** — Parses the run's `SampleSheet.csv`, runs DRAGEN demux-only, and stages FASTQs to a shared output directory.
2. **TSO500 Analysis** — Runs DRAGEN TSO500 per sample (fanned out in parallel), validating that each sample reaches `COMPLETED_ALL_STEPS`.
3. **QCI Zip** — Packages per-sample result files (`CombinedVariantOutput.tsv`, `.cnv.vcf`, `.hard-filtered.vcf`) into a zip for downstream use.
4. **QC & Reporting** — On completion, generates a metrics summary table, an MSI/TMB/HRD Excel workbook, a demux summary CSV, and a merged QC Excel file, all attached to a completion email.

---

## Requirements

- Nextflow ≥ 25.10.2
- Singularity
- SLURM (Biowulf `norm` and `nci-dragen`/`nci-lp-dragen` partitions)
- DRAGEN 3.11.2 (`/opt/dragen/3.11.2/bin`)
- Python 3 with: `pandas`, `openpyxl`

---

## Directory Structure

```
NextFlow/
├── main.nf                  # Main workflow
├── nextflow.config          # Config: params, profiles, singularity, logging
├── run.sh                   # Entry point — creates dirs and submits via sbatch
├── submit_pipeline.sh       # sbatch wrapper — sets up work dir, loads modules, runs Nextflow
├── modules/
│   ├── demux.nf             # DEMUX process
│   ├── tso500.nf            # TSO500 process
│   └── qci_zip.nf           # QCI_ZIP process
├── scripts/
│   ├── samplesheet.py       # Parses SampleSheet.csv → sample_ids.txt, pair_ids.txt
│   ├── qc_email.py          # Builds per-sample [Analysis Status] metrics table
│   ├── msi_tmb_hrd_table.py # Scrapes MSI, TMB, HRD values → Excel
│   ├── merge_TSO500_QC.py   # Merges MetricsOutput.tsv files + run QC JSON → Excel
│   └── demux_summary.py     # Reformats Demultiplex_Stats.csv into lane/sample report
├── metadata/                # Per-run sample_ids.txt and pair_ids.txt (auto-created)
├── logs/                    # sbatch log files (auto-created)
└── work/                    # Nextflow work directories, one per run (auto-created)
```

---

## Usage

```bash
./run.sh <RUNFOLDER>
```

**Example:**
```bash
./run.sh 260219_NDX550200_0530_AH7J7NBGYX
```

The run folder name must match a directory under `params.run_base` (default: `/data/Compass/NextSeq_raw`).

### Stub / dry run

To run in stub mode (uses existing metrics files to determine what needs to be rerun, without executing DRAGEN):

```bash
./run.sh <RUNFOLDER> -stub
```

---

## Key Parameters

All parameters are set in `nextflow.config` and can be overridden on the command line with `--param value`.

| Parameter            | Default                                      | Description                                      |
|----------------------|----------------------------------------------|--------------------------------------------------|
| `run_folder`         | *(required)*                                 | Sequencing run folder name                       |
| `run_base`           | `/data/Compass/NextSeq_raw`                  | Root directory containing run folders            |
| `fastq_outdir`       | `…/FastqFolder`                              | Destination for demuxed FASTQs                   |
| `demux_outdir`       | `…/TSO500_DRAGEN_Demux`                          | Destination for DRAGEN demux output              |
| `tso_outdir`         | `…/TSO500_Results`                           | Destination for TSO500 per-sample results        |
| `dragen_bin`         | `/opt/dragen/3.11.2/bin`                     | Path to DRAGEN binaries                          |
| `email_from`         | `$USER@nih.gov`                              | Sender address for pipeline notifications        |
| `email_to`           | *(set in nextflow.config)*                   | Recipient address for pipeline notifications     |
| `partition`          | `nci-dragen,nci-lp-dragen`                   | SLURM partition(s) for DEMUX and TSO500 jobs     |

---

## Outputs

### Per run (under `params.tso_outdir/run_qc/`)

| File | Description |
|------|-------------|
| `<run>_app_complete.txt` | Per-sample [Analysis Status] metrics table |
| `MSI_TMB_HRD_<run>.xlsx` | MSI, TMB, and HRD/GIS values per sample |
| `TSO500_QC_<run>.xlsx` | Merged per-sample MetricsOutput + run QC JSON |
| `<run>.csv` | Demux summary (lane, sample, and barcode breakdown) |

### Per sample (under `params.tso_outdir/<pair_id>/Results/`)

| File | Description |
|------|-------------|
| `<pair_id>.zip` | Zipped variant outputs: `CombinedVariantOutput.tsv`, `.cnv.vcf`, `.hard-filtered.vcf` |

### Metadata (under `metadata/<run>/`)

| File | Description |
|------|-------------|
| `sample_ids.txt` | One sample ID per line, parsed from SampleSheet.csv |
| `pair_ids.txt` | One pair ID per line, parsed from SampleSheet.csv |

### Pipeline logs (under `pipeline_info/`)

Nextflow timeline, report, and trace files are written here for each run.

---

## Profiles

| Profile | Description |
|---------|-------------|
| `biowulf` | *(default)* SLURM executor with DRAGEN-specific partition and resource settings |
| `stub` | Local executor; skips DRAGEN execution. Uses existing metrics files to identify samples that need to be (re)run. |

---

## Email Notifications

A start email is sent when the pipeline is submitted. A completion email is sent when the pipeline finishes (success or failure), with the QC Excel files and demux summary attached.

---

## Pipeline Version

Current version: **2.6.2** (set in `nextflow.config` under `manifest.version`)
