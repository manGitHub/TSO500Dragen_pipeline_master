// ── modules/vaf_scatter.nf ────────────────────────────────────────────────────

process VAF_SCATTER_HTML {
    tag "${sample_id}"

    input:
    tuple val(sample_id), val(pair_id), val(tso_result_dir)
    val vaf_scatter_script

    output:
    tuple val(sample_id), path("${sample_id}_variant_scatter.html"), emit: html

    publishDir "${params.tso_outdir}/${pair_id}/Results/${pair_id}/${sample_id}", mode: 'copy'

    script:
    def tmb_trace = "${tso_result_dir}/Results/${pair_id}/${sample_id}/${sample_id}_TMB_Trace.tsv"
    """
    set -euo pipefail

    source /data/Compass/bin/groupmamba
    mamba activate tsov2-vaf_scatter

    mkdir -p input output tmp/matplotlib
    export MPLCONFIGDIR="\$PWD/tmp/matplotlib"

    cp "${vaf_scatter_script}" ./vaf_scatter_html.py
    cp "${tmb_trace}" "input/${sample_id}_TMB_Trace.tsv"

    python ./vaf_scatter_html.py "${sample_id}"
    cp "output/${sample_id}_variant_scatter.html" "${sample_id}_variant_scatter.html"
    test -s "${sample_id}_variant_scatter.html"

    echo "Generated VAF scatter HTML for ${sample_id}"
    """

    stub:
    """
    echo "STUB: would generate VAF scatter HTML for ${sample_id}"
    printf '<!doctype html><html><body><h1>STUB ${sample_id} VAF scatter</h1></body></html>\n' > "${sample_id}_variant_scatter.html"
    """
}
