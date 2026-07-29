#!/bin/bash
set -euo pipefail

RUNFOLDER="$1"
FASTQ_DIR="$2"
SAMPLE_IDS_FILE="$3"
FASTQ_AGE_DAYS="$4"
STAGING_ROOT="/staging"

# change permissions
chgrp Compass "${FASTQ_DIR}"
chmod g+rx "${FASTQ_DIR}"

while IFS= read -r sample_id; do
    [[ -n "$sample_id" ]] || continue

    sample_dir="${FASTQ_DIR}/${sample_id}"

    if [[ -d "$sample_dir" ]]; then
        chgrp -R Compass "$sample_dir"
        chmod -R g+rX "$sample_dir"
    else
        echo "WARNING: sample dir not found: $sample_dir"
    fi
done < "${SAMPLE_IDS_FILE}"

# remove sample directories that contain FASTQs older than N days
echo "in OnComplete - Removing sample directories containing FASTQs older than ${FASTQ_AGE_DAYS} days in ${FASTQ_DIR}"
find "${FASTQ_DIR}" -mindepth 2 -maxdepth 2 -type f \
    \( -name "*.fastq" -o -name "*.fastq.gz" \) \
    -mtime +"${FASTQ_AGE_DAYS}" \
    -printf '%h\n' \
    | sort -u \
    | while IFS= read -r sample_dir; do
        echo "Removing sample directory: ${sample_dir}"
        rm -rf "${sample_dir}"
    done
echo "Clean up of fastq files complete."
echo

# clean up run dirs
echo "Removing run folders from ${STAGING_ROOT}"
echo "Removing run folder: ${STAGING_ROOT}/${RUNFOLDER}"
rm -rf "${STAGING_ROOT:?}/${RUNFOLDER}"

echo "Removing analysis folders: ${STAGING_ROOT}/${RUNFOLDER}-Demux-*"
find "${STAGING_ROOT}" -maxdepth 1 -type d -name "${RUNFOLDER}-Demux-*" -exec rm -rf {} +

echo "Cleanup complete"
