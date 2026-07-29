// ── modules/zip_results.nf ────────────────────────────────────────────────────

process QCI_ZIP {
    tag "${sample_id}"

    input:
    tuple val(sample_id), val(pair_id), val(tso_result_dir)

    output:
    tuple val(sample_id), path("${pair_id}.zip"), emit: zipped

    publishDir "${params.tso_outdir}/${pair_id}/Results", mode: 'copy'

    script:
    def results_dir = "${tso_result_dir}/Results/${pair_id}"
    return """
    set -euo pipefail

    python -c "from pathlib import Path; p = Path(r'${results_dir}/${sample_id}/${sample_id}.cnv.vcf'); t = p.read_text(); p.write_text(t.replace('##reference=file://hashtable', '##reference=/opt/illumina/resources/genomes/hg19_hardPAR'))"

    python -c "from pathlib import Path; p = Path(r'${results_dir}/${sample_id}/${sample_id}.hard-filtered.vcf'); t = p.read_text(); p.write_text(t.replace('##reference=file://hashtable/reference.bin', '##reference=/opt/illumina/resources/genomes/hg19_hardPAR'))"

    zip -j "${pair_id}.zip" \
        "${results_dir}/${pair_id}_CombinedVariantOutput.tsv" \
        "${results_dir}/${sample_id}/${sample_id}.cnv.vcf" \
        "${results_dir}/${sample_id}/${sample_id}.hard-filtered.vcf"

    echo "Zipped results for ${sample_id} -> ${pair_id}.zip"
    """

    stub:
    """
    echo "STUB: would zip results for ${sample_id}"
    touch "${pair_id}.zip"
    """
}
