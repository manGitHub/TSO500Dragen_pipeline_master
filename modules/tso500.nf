// ── modules/tso500.nf ─────────────────────────────────────────────────────────

process TSO500 {
    tag "${sample_id}"

    input:
    tuple val(sample_id), val(pair_id), path(fastqs_ready)
    val  fastq_outdir
    val  tso_outdir

    output:
    tuple val(sample_id), val("${tso_outdir}/${pair_id}"), emit: tso_output

    script:
    def tso500_ver = workflow.manifest.version
    def run_name   = params.run_folder
    def ss         = "${params.run_base}/${run_name}/SampleSheet.csv"

    """
    set -euo pipefail

    analysis="${tso_outdir}/${pair_id}"

    # ── SETUP ──────────────────────────────────────────────────────────────────
    ulimit -u 16384 -n 65535
    export PATH="${params.dragen_bin}:\$PATH"
    mkdir -p "\${analysis}"

    # ── RUN TSO500 ─────────────────────────────────────────────────────────────
    env -i \
        PATH="\$PATH" \
        DRAGEN_TSO500-${tso500_ver}.sh \
            --engine singularity \
            --analysisFolder "\${analysis}" \
            --fastqFolder    "${fastq_outdir}" \
            --sampleSheet    "${ss}" \
            --sampleOrPairIDs "${pair_id}" \
        2>&1

    # ── VALIDATE ───────────────────────────────────────────────────────────────
    if [[ ! -f "\${analysis}/Results/MetricsOutput.tsv" ]]; then
        echo "ERROR: Missing metrics file: \${analysis}/Results/MetricsOutput.tsv" >&2
        exit 1
    fi

    if ! grep -q "COMPLETED_ALL_STEPS" "\${analysis}/Results/MetricsOutput.tsv"; then
        echo "ERROR: COMPLETED_ALL_STEPS not found in metrics for ${sample_id}" >&2
        exit 1
    fi

    echo "TSO500 analysis complete for sample: ${sample_id}"
    """

    stub:
    def metrics = "${params.tso_outdir}/${pair_id}/Results/MetricsOutput.tsv"
    """
    timestamp="\$(date +%Y%m%d_%H%M%S)"
    stub_log="${launchDir}/pipeline_info/stubs/incomplete_samples_\${timestamp}.txt"
    mkdir -p "${launchDir}/pipeline_info/stubs"

    if [[ -f "${metrics}" ]]; then
        echo "Metrics file found for ${sample_id}: ${metrics}"

        if ! grep -q "COMPLETED_ALL_STEPS" "${metrics}"; then
	    echo "Metrics file found for ${sample_id} but missing COMPLETED_ALL_STEPS: ${metrics}"
            cat >> "\${stub_log}" <<EOF
NEEDS_RUN: ${sample_id} (incomplete metrics)
EOF
            echo "Stub TSO500: logged ${sample_id} to \${stub_log}"
	    mkdir -p "${params.tso_outdir}/${pair_id}/Results"
	    echo "NEEDS_RUN" > "${params.tso_outdir}/${pair_id}/Results/stub_metrics.txt"
            exit 0
        fi

    else
        echo "ERROR: No metrics file found for ${sample_id} at: ${metrics}" >&2
        cat >> "\${stub_log}" <<EOF
NEEDS_RUN: ${sample_id} (no metrics file)
EOF
        echo "Stub TSO500: logged ${sample_id} to \${stub_log}"
	mkdir -p "${params.tso_outdir}/${pair_id}/Results"
	echo "NEEDS_RUN" > "${params.tso_outdir}/${pair_id}/Results/stub_metrics.txt"
        exit 0
    fi

    mkdir -p "${params.tso_outdir}/${pair_id}/Results"
    echo "STUB TSO500 output for ${sample_id}" > "${params.tso_outdir}/${pair_id}/Results/stub_metrics.txt"
    """
}
