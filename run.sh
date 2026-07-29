#!/bin/bash
# run.sh — pre-flight setup then submits the Nextflow pipeline via sbatch
#
# Usage: bash run.sh 260219_NDX550200_0530_AH7J7NBGYX
PIPELINE_DIR="$(pwd)"
mkdir -p logs
mkdir -p metadata

RUNFOLDER="${1:?Usage: bash run.sh <RUNFOLDER>}"
TIMESTAMP="$(date '+%m%d%Y_%H%M%S')"

sbatch --output="logs/tso500v2.6.2_%j.${RUNFOLDER}.${TIMESTAMP}.log" \
    submit_pipeline.sh "${PIPELINE_DIR}" "$@"
