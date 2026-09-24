// ── modules/add_exon_names.nf ─────────────────────────────────────────────────

process ADD_EXON_NAMES {
    tag "${sample_id}"

    input:
    tuple val(sample_id), val(pair_id), val(tso_result_dir)
    path exon_bed
    val exon_cov_report_script

    output:
    tuple val(sample_id), path("${sample_id}.exon_cov_report2.tsv"), emit: modified_report

    publishDir "${params.tso_outdir}/${pair_id}/Results/${pair_id}/${sample_id}", mode: 'copy', overwrite: true

    script:
    def exon_cov_report = "${tso_result_dir}/Results/${pair_id}/${sample_id}/${sample_id}.exon_cov_report.tsv"
    def output_name = "${sample_id}.exon_cov_report2.tsv"
    """
    set -euo pipefail

    source /data/Compass/bin/groupmamba
    mamba activate ${params.exon_cov_report_env}

    test -s "${exon_cov_report}"
    python "${exon_cov_report_script}" "${exon_bed}" "${exon_cov_report}" "${output_name}"
    test -s "${output_name}"
    echo "Generated modified exon coverage report for ${sample_id}"
    """

    stub:
    """
    printf 'chr\\tstart\\tend\\texon\\tmean_coverage\\tmedian_coverage\\tmin_coverage\\tmax_coverage\\n' > "${sample_id}.exon_cov_report2.tsv"
    """
}
