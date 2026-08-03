#!/bin/bash
# run.sh — pre-flight setup then submits the Nextflow pipeline via sbatch
#
# Usage: bash run.sh 260219_NDX550200_0530_AH7J7NBGYX
PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_DIR="$(pwd)"
mkdir -p "${LAUNCH_DIR}/logs"
mkdir -p "${LAUNCH_DIR}/metadata"
RUNFOLDER="${1:?Usage: bash run.sh <RUNFOLDER>}"
TIMESTAMP="$(date '+%m%d%Y_%H%M%S')"
sbatch --output="${LAUNCH_DIR}/logs/tso500v2.6.2_%j.${RUNFOLDER}.${TIMESTAMP}.log" \
    "${PIPELINE_DIR}/submit_pipeline.sh" "${PIPELINE_DIR}" "${LAUNCH_DIR}" "$@"
