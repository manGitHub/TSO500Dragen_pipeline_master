#!/usr/bin/env bash
# submit_pipeline.sh — wraps the Nextflow pipeline in an sbatch job
#SBATCH --job-name=dragenTSO500v2
#SBATCH --mem=4G
#SBATCH --cpus-per-task=2
#SBATCH --partition=norm
#SBATCH --time=12:00:00
set -euo pipefail
PIPELINE_DIR="${1:?PIPELINE_DIR not set}"
LAUNCH_DIR="${2:?LAUNCH_DIR not set}"
RUNFOLDER="${3:?Usage: bash run.sh <RUNFOLDER>}"
shift 3
EXTRA_ARGS=("$@")
# ── Per-run work directory (avoids collisions when running two runs at once) ──
WORK_DIR="${LAUNCH_DIR}/work/${RUNFOLDER}"
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"
# ── Profile / stub handling ───────────────────────────────────────────────────
STUB_FLAG=""
PROFILE="biowulf"
FILTERED_ARGS=()
skip_next=false
for arg in "${EXTRA_ARGS[@]:-}"; do
    if ${skip_next}; then
        skip_next=false
        continue
    fi
    if [[ "${arg}" == "-stub" ]]; then
        STUB_FLAG="-stub"
        PROFILE="stub"
    elif [[ "${arg}" == "-profile" ]]; then
        skip_next=true   # drop the value that follows too
    else
        FILTERED_ARGS+=("${arg}")
    fi
done
EXTRA_ARGS=("${FILTERED_ARGS[@]}")
module load nextflow/25.10.2
module load singularity
nextflow run "${PIPELINE_DIR}/main.nf" \
    -profile "${PROFILE}" \
    -resume \
    -work-dir "${WORK_DIR}" \
    ${STUB_FLAG} \
    --run_folder "${RUNFOLDER}" \
    --launch_dir "${LAUNCH_DIR}" \
    "${EXTRA_ARGS[@]}" \
    2>&1

# ── Permissions: work, metadata, and logs dirs ────────────────────────────────
chmod g+rw "${LAUNCH_DIR}/work" "${LAUNCH_DIR}/metadata" "${LAUNCH_DIR}/logs"

THIS_LOG="$(ls "${LAUNCH_DIR}/logs/"*"_${SLURM_JOB_ID}.${RUNFOLDER}."*.log 2>/dev/null | head -n1)"
if [[ -n "${THIS_LOG}" ]]; then
    chmod g+rw "${THIS_LOG}"
else
    echo "WARNING: could not locate log file for job ${SLURM_JOB_ID} / run ${RUNFOLDER}" >&2
fi
