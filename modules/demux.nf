// ── modules/demux.nf ──────────────────────────────────────────────────────────

process DEMUX {
    tag "${runDir}"

    input:
    val  runDir               
    val  samplesheet_script
    val  fastq_outdir      
    val  demux_outdir

    output:
    path "sample_ids.txt",   emit: sample_ids
    path "pair_ids.txt",     emit: pair_ids
    path "fastqs_ready.flag", emit: fastqs_ready

    publishDir "${projectDir}/metadata/${params.run_folder}", mode: 'copy',
        saveAs: { filename -> filename in ["sample_ids.txt", "pair_ids.txt"] ? filename : null }

    script:
    def run_name     = runDir.tokenize('/').last()
    def tso500_ver   = workflow.manifest.version
    def sample_sheet = "${runDir}/SampleSheet.csv"

    """
    set -euo pipefail

    demux_run_outdir="${demux_outdir}/${run_name}-Demux"
    fq_gen="\${demux_run_outdir}/Logs_Intermediates/FastqGeneration"

    # ── SAMPLESHEET ────────────────────────────────────────────────────────────
    python3 "${samplesheet_script}" "${sample_sheet}" "${projectDir}/metadata/${params.run_folder}"

    # ── DRAGEN_DEMUX ───────────────────────────────────────────────────────────
    export PATH="${params.dragen_bin}:\$PATH"
    ulimit -u 16384 -n 65535
    mkdir -p "\${demux_run_outdir}"
    mkdir -p "${fastq_outdir}"

    env -i \
        PATH="\$PATH" \
        DRAGEN_TSO500-${tso500_ver}.sh \
            --engine singularity \
            --demultiplexOnly \
            --analysisFolder "\${demux_run_outdir}" \
            --runFolder      "${runDir}" \
            --sampleSheet    "${sample_sheet}" \
            2>&1

    if [[ -z "\$(ls -A "\${demux_run_outdir}/Logs_Intermediates" 2>/dev/null)" ]]; then
        echo "ERROR: DRAGEN demux failed, check log files." >&2
        exit 1
    fi

    # ── FASTQS ─────────────────────────────────────────────────────────────────
    if [[ ! -d "\${fq_gen}" ]]; then
        echo "ERROR: FastqGeneration directory not found: \${fq_gen}" >&2
        exit 1
    fi
    echo "Expecting \$(wc -l < "sample_ids.txt") sample(s)."
    copied=0
    while IFS= read -r sample || [[ -n "\${sample}" ]]; do
        sample="\$(echo "\${sample}" | tr -d '[:space:]')"
        [[ -z "\${sample}" ]] && continue
        sample_dir="\${fq_gen}/\${sample}"
        if [[ ! -d "\${sample_dir}" ]]; then
            echo "ERROR: Expected sample directory not found: \${sample_dir}" >&2
            exit 1
        fi
        mkdir -p "${fastq_outdir}/\${sample}"
        if rsync -avz "\${sample_dir}/" "${fastq_outdir}/\${sample}/"; then
            rm -rf "\${sample_dir}"
            echo "Copied and removed FASTQs for \${sample} -> ${fastq_outdir}/\${sample}/"
        else
            echo "ERROR: rsync failed for \${sample}, original not removed" >&2
            exit 1
        fi
        (( copied++ )) || true
    done < "sample_ids.txt"
    echo "FASTQ publish complete. Copied: \${copied}."
    touch "fastqs_ready.flag"

    # ── PERMISSIONS ────────────────────────────────────────────────────────────
    while IFS= read -r sample_id || [[ -n "\${sample_id}" ]]; do
        [[ -n "\${sample_id}" ]] || continue
        sample_dir="${fastq_outdir}/\${sample_id}"
        if [[ -d "\${sample_dir}" ]]; then
            chgrp -R Compass "\${sample_dir}"
            chmod -R g+rX "\${sample_dir}"
        else
            echo "WARNING: sample dir not found: \${sample_dir}"
        fi
    done < "sample_ids.txt"
    """

    stub:
    def run_name = runDir.tokenize('/').last()
    """
    python3 "${samplesheet_script}" "${runDir}/SampleSheet.csv"

    touch "fastqs_ready.flag"
    echo "Stub Run. Parsed samples:"
    cat sample_ids.txt
    """
}
