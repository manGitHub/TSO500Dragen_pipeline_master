# DRAGEN TSO500 Nextflow Pipeline

Nextflow pipeline for demultiplexing and per-sample TSO500 analysis using DRAGEN on the NIH Biowulf HPC cluster.

---

## Overview

This pipeline automates the following steps for a given sequencing run:

1. **Demultiplexing** — Parses the run's `SampleSheet.csv`, runs DRAGEN demux-only, and stages FASTQs to a shared output directory.
2. **TSO500 Analysis** — Runs DRAGEN TSO500 per sample (fanned out in parallel), validating that each sample reaches `COMPLETED_ALL_STEPS`.
3. **QCI Zip** — Packages per-sample result files (`CombinedVariantOutput.tsv`, `.cnv.vcf`, `.hard-filtered.vcf`) into a zip for downstream use, patching the `##reference=` header in the VCFs to point at the DRAGEN hg19 reference path.
4. **QC & Reporting** — On completion, generates a metrics summary table, an MSI/TMB/HRD/Tumor Purity Excel workbook, a demux summary CSV, and a merged QC Excel file, all attached to a completion email.

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
│   ├── msi_tmb_hrd_table.py # Scrapes MSI, TMB, HRD, tumor purity values → Excel
│   ├── merge_TSO500_QC.py   # Merges MetricsOutput.tsv files + run QC JSON → Excel
│   └── demux_summary.py     # Reformats Demultiplex_Stats.csv into lane/sample report
├── metadata/                # Per-run sample_ids.txt and pair_ids.txt (auto-created)
├── logs/                    # sbatch log files (auto-created)
├── work/                    # Nextflow work directories, one per run (auto-created)
└── pipeline_info/           # Nextflow timeline, report, and trace files (auto-created)
```

---

## Usage

```bash
/path/to/run.sh <RUNFOLDER>
```

**Example:**
```bash
/path/to/run.sh 260219_NDX550200_0530_AH7J7NBGYX
```

The run folder name must match a directory under `params.run_base` (default: `/data/Compass/NextSeq_raw`).

### Running in your own directory

To run the pipeline with output directed to your own working directory instead of the shared default locations, override `--tso_outdir`, `--fastq_outdir`, and `--demux_outdir` on the command line:

```bash
/path/to/run.sh 260219_NDX550200_0530_AH7J7NBGYX \
  --tso_outdir /path/to/TSO_Results \
  --fastq_outdir /path/to/FastqFolder \
  --demux_outdir /path/to/TSO500_v2_Demux
```

The pipeline always runs with `-resume` enabled, so re-submitting the same run folder will pick up from cached work where possible.

### Stub / dry run

To run in stub mode (uses existing metrics files to determine what needs to be rerun, without executing DRAGEN):

```bash
/path/to/run.sh <RUNFOLDER> -stub
```

In stub mode, `TSO500` checks each sample's existing `MetricsOutput.tsv` for `COMPLETED_ALL_STEPS`. Samples missing a metrics file or missing that status are logged to `pipeline_info/stubs/incomplete_samples_<timestamp>.txt` and flagged with a `NEEDS_RUN` marker instead of failing the run.

Profile selection is automatic: `submit_pipeline.sh` uses the `biowulf` profile by default, and switches to the `stub` profile only when `-stub` is passed. Any `-profile <value>` passed directly to `run.sh` is ignored, since profile selection is controlled internally.

---

## Re-running After a Failure or Stub Run

Before re-submitting a run — whether recovering from a failed run or following up a `-stub` dry run — clean up stale outputs so the pipeline doesn't pick up incomplete or outdated results via `-resume`:

- **Delete/rename TSO output folders for any samples that need to be rerun:**
  ```
  …/tso_outdir/<pair_id>
  ```

- **If Demux needs to be rerun, delete/rename the demux output directory for the RUNFOLDER:**
  ```
  …/demux_outdir/<RUNFOLDER>
  ```

- **If the entire run needs to be repeated, first delete/rename the work directory for the RUNFOLDER:**
  ```
  …/work/<RUNFOLDER>
  ```

The pipeline will still use `-resume`, so only the missing samples will be run if necessary.

---

## Key Parameters

All parameters are set in `nextflow.config` and can be overridden on the command line with `--param value`.

| Parameter            | Default                                      | Description                                      |
|----------------------|----------------------------------------------|--------------------------------------------------|
| `run_folder`         | *(required)*                                 | Sequencing run folder name                       |
| `launch_dir`         | *(set by run.sh)*                            | Directory the pipeline was launched from         |
| `pipeline`           | `4.0`                                        | Workflow version number reported in emails       |
| `run_base`           | `/data/Compass/NextSeq_raw`                  | Root directory containing run folders            |
| `fastq_outdir`       | `…/FastqFolder`                              | Destination for demuxed FASTQs                   |
| `demux_outdir`       | `…/TSO500_DRAGEN_Demux`                      | Destination for DRAGEN demux output              |
| `tso_outdir`         | `…/TSO500_Results`                           | Destination for TSO500 per-sample results        |
| `dragen_bin`         | `/opt/dragen/3.11.2/bin`                     | Path to DRAGEN binaries                          |
| `email_from`         | `$USER@nih.gov`                              | Sender address for pipeline notifications        |
| `email_to`           | *(set in nextflow.config)*                   | Recipient address for pipeline notifications     |
| `partition`          | `nci-dragen,nci-lp-dragen`                   | SLURM partition(s) for DEMUX and TSO500 jobs     |

---

## Outputs

### Per run (under `params.tso_outdir/Dragen_run_qc/`)

| File | Description |
|------|-------------|
| `<run>_app_complete.txt` | Per-sample [Analysis Status] metrics table |
| `MSI_TMB_HRD_<run>.xlsx` | MSI, TMB, HRD/GIS, and tumor purity values per sample |
| `TSO500_QC_<run>.xlsx` | Merged per-sample MetricsOutput + run QC JSON |
| `<run>.csv` | Demux summary (lane, sample, and barcode breakdown) |

### Per sample (under `params.tso_outdir/<pair_id>/Results/`)

| File | Description |
|------|-------------|
| `<pair_id>.zip` | Zipped variant outputs: `CombinedVariantOutput.tsv`, `.cnv.vcf`, `.hard-filtered.vcf` |
| `<run>_<pair_id>_TSO500v2.6.2.done` | Marker file dropped on pipeline completion |

### Metadata (under `metadata/<run>/`)

| File | Description |
|------|-------------|
| `sample_ids.txt` | One sample ID per line, parsed from SampleSheet.csv |
| `pair_ids.txt` | One pair ID per line, parsed from SampleSheet.csv |

### Pipeline logs (under `pipeline_info/`)

Nextflow timeline, report, and trace files are written here for each run. Stub-mode incomplete-sample logs are written under `pipeline_info/stubs/`.

Trace files (for both stub and regular runs) are named `<run>_<timestamp>_trace.txt` and can be found at:

```
…/pipeline_info/<run>_<timestamp>_trace.txt
```

**Example:**
```
…/work/260219_NDX550200_0530_AH7J7NBGYX/pipeline_info/260219_NDX550200_0530_AH7J7NBGYX_20260821_164015_trace.txt
```

---

## Profiles

| Profile | Description |
|---------|-------------|
| `biowulf` | *(default)* SLURM executor with DRAGEN-specific partition and resource settings |
| `stub` | Local executor; skips DRAGEN execution and disables `publishDir`. Uses existing metrics files to identify samples that need to be (re)run. |

---

## Email Notifications

A start email is sent when the pipeline is submitted, listing the launch, fastq, demux, and TSO output directories. A completion email is sent when the pipeline finishes (success or failure), with the per-sample metrics table in the body and the MSI/TMB/HRD/Tumor Purity Excel, merged QC Excel, and demux summary CSV attached (whichever were successfully generated).

---

## Permissions

During `DEMUX`, after FASTQs are copied to `fastq_outdir`, each sample's FASTQ directory is set to **read-only** for the `Compass` group (`chgrp -R Compass`, `chmod -R g+rX`). The demux run output directory under `demux_outdir` is set to **read-write** for the group (`chgrp -R Compass`, `chmod -R g+rw`).

On pipeline completion (non-stub runs only), the pipeline also updates group ownership and permissions (`chgrp -R Compass`, `chmod -R g+rw`) on each sample's TSO output directory under `tso_outdir`, scoped to the current run's pair IDs.

---

## Pipeline Version

Current version: **4.0** (set in `nextflow.config` under `params.pipeline`)
