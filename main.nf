#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ── Validate required params ──────────────────────────────────────────────────
if (!params.run_folder) {
    error "Please supply --run_folder <RUNFOLDER_NAME>"
}

// ── Include modules ───────────────────────────────────────────────────────────
include { DEMUX   } from './modules/demux'
include { TSO500  } from './modules/tso500'
include { QCI_ZIP } from './modules/qci_zip'
include { VAF_SCATTER_HTML } from './modules/vaf_scatter'

// ── Shared paths/values ───────────────────────────────────────────────────────
def pipelineVersion = workflow.manifest.version
def runDir             = "${params.run_base}/${params.run_folder}"
def vafScatterScript = params.vaf_scatter_script


// ── Workflow ──────────────────────────────────────────────────────────────────
workflow {
    main:
    sendMail(
        from:    params.email_from,
        to:      params.email_to,
        subject: "[START] TSO500.${pipelineVersion} Pipeline: ${params.run_folder}",
        body:    """\
	Pipeline started for run: ${params.run_folder}

	Launch directory: ${params.launch_dir}
	Fastq directory: ${params.fastq_outdir}
	Demux directory: ${params.demux_outdir}
	TSO output directory: ${params.tso_outdir}
	""".stripIndent()
    )

    DEMUX(
        channel.value(runDir),
        channel.value(params.samplesheet_script),
        channel.value(params.fastq_outdir),
        channel.value(params.demux_outdir)
    )

    // ── Fan out TSO500 per sample ─────────────────────────────────────────────
    def sample_ch = DEMUX.out.sample_ids
        .splitText() { it.trim() }				// [sample_id] channel
        .merge(DEMUX.out.pair_ids.splitText() { it.trim() })  	// [sample_id, pair_id]
        .combine(DEMUX.out.fastqs_ready)                        // [sample_id, pair_id, flag] — ensures FASTQs are in fastq_outdir before TSO500 starts

    TSO500(
        sample_ch,						// each sample tuple and pipeline dirs
        channel.value(params.fastq_outdir),
        channel.value(params.tso_outdir)
    )

    VAF_SCATTER_HTML(
        TSO500.out.tso_output
            .map { sample_id, tso_dir ->
                def pair_id = tso_dir.tokenize('/').last()
                tuple(sample_id, pair_id, tso_dir)
            },
        channel.value(vafScatterScript)
    )

    QCI_ZIP(
        TSO500.out.tso_output
            .map { sample_id, tso_dir ->
                def pair_id = tso_dir.tokenize('/').last()
                tuple(sample_id, pair_id, tso_dir)
            }
    )
}

// ── Email notifications ───────────────────────────────────────────────────────
workflow.onComplete {
    def status      = workflow.success ? 'SUCCESS' : 'FAIL'
    def run_name    = params.run_folder
    def tso500Ver   = workflow.manifest.version
    def workflowVer = params.pipeline

    // def cleanup_cmd = """
    //    sbatch --job-name=cleanup_${run_name} \
    //           --output=${params.fastq_outdir}/logs/cleanup_${run_name}_%j.out \
    //           --error=${params.fastq_outdir}/logs/cleanup_${run_name}_%j.err \
    //           --partition=${params.partition} \
    //           --cpus-per-task=2 \
    //           --mem=4g \
    //           --time=01:00:00 \
    //           ${params.cleanup_script} \
    //           ${run_name} \
    //           ${params.fastq_staging} \
    //           ${sample_ids_file} \
    //           ${params.fastq_age_clean}
    // """.stripIndent()
    // println cleanup_cmd
    // ["bash", "-lc", cleanup_cmd].execute().waitFor()

    // update permissions for tso output

    // ── Build per-sample metrics table from [Analysis Status] in each MetricsOutput.tsv ──
    def metadataDir  = "${params.launch_dir}/metadata/${run_name}"
    def qcOutDir     = "${params.tso_outdir}/Dragen_run_qc"
    def tableOutPath = "${qcOutDir}/${run_name}_app_complete.txt"
    new File(metadataDir).mkdirs()
    new File(qcOutDir).mkdirs()

    def pairIds = new File("${metadataDir}/pair_ids.txt").exists()
        ? new File("${metadataDir}/pair_ids.txt").text.trim()
        : ""

    def sampleIds = new File("${metadataDir}/sample_ids.txt").exists()
        ? new File("${metadataDir}/sample_ids.txt").text.trim()
        : ""

    // update permissions for tso output — scoped to this run's samples only
    if (!workflow.stubRun) {
        pairIds.split("\n").each { pair_id ->
            pair_id = pair_id.trim()
            if (pair_id) {
                def sampleOutDir = "${params.tso_outdir}/${pair_id}"
                ["bash", "-c", """
                    chgrp -R Compass ${sampleOutDir} && chmod -R g+rw ${sampleOutDir}
                """].execute().waitFor()
            }
        }
    }

    // ── Drop a .done file into each sample's directory ────────────────────────
    pairIds.split("\n").each { pair_id ->
        pair_id = pair_id.trim()
        if (pair_id) {
            def sampleDir  = new File("${params.tso_outdir}/${pair_id}")
            def doneFile   = new File(sampleDir, "${run_name}_${pair_id}_TSO500v2.6.2.done")
            sampleDir.mkdirs()
            doneFile.text  = ""
        }
    }
	
	// email body with sample status
    def qcProc = ["python3",
     params.qc_email_script,
     params.tso_outdir,
     "--pairs", pairIds,
     "--out", tableOutPath
    ].execute()
    def qcErr = qcProc.err.text
    if (qcProc.waitFor() != 0) {
        log.error "qc_email.py failed:\n${qcErr}"
    }
	// read in table generated by above script
    def metricsTable = new File(tableOutPath).exists()
        ? new File(tableOutPath).text
        : "  (metrics table could not be generated)"

    ["python3",
     params.msi_tmb_script,
     "--tso_outdir",  params.tso_outdir,
     "--run_folder",  params.run_folder,
     "--out_dir",     qcOutDir,
     "--samples",     sampleIds
    ].execute().waitFor()

    def xlsxFile = new File("${qcOutDir}/MSI_TMB_HRD_${run_name}.xlsx")
    def qcXlsxName  = "TSO500_QC_${run_name}.xlsx"
    def qcXlsxFile  = new File("${qcOutDir}/${qcXlsxName}")

	// collect sample metrics files
    def metricsFiles = sampleIds.split("\n").collect { sample_id ->
        new File("${params.tso_outdir}/${sample_id.trim()}_NoPair/Results/MetricsOutput.tsv")
    }.findAll { it.exists() }.collect { it.absolutePath }

    def demuxRunDir = "${params.demux_outdir}/${run_name}"
	// get demux run qc
    def runQcJson = new File("${demuxRunDir}/Logs_Intermediates/RunQc/RunQCMetrics.json").exists()
        ? "${demuxRunDir}/Logs_Intermediates/RunQc/RunQCMetrics.json"
        : null

	// demux and sample metrics email file
    if (metricsFiles && runQcJson) {
        def qcCmd = ["python3",
            params.merge_qc_script,
            qcXlsxName,
            "${qcOutDir}/",
            runQcJson,
            metricsFiles.join(",")
        ]
        def mergeProc = qcCmd.execute()
        def mergeErr  = mergeProc.err.text
        if (mergeProc.waitFor() != 0) {
            log.error "merge_TSO500_QC.py failed:\n${mergeErr}"
        }
    } else {
        log.warn "Skipping QC Excel: metricsFiles=${metricsFiles.size()} runQcJson=${runQcJson}"
    }

    // ── Build demux summary CSV ───────────────────────────────────────────────
    def demuxStatsFile = "${demuxRunDir}/Logs_Intermediates/FastqGeneration/Reports/Demultiplex_Stats.csv"
    def demuxSumFile   = null

    if (new File(demuxStatsFile).exists()) {
        def demuxProc = ["python3",
            params.demux_summary_script,
            demuxStatsFile,
            qcOutDir,
            run_name
        ].execute()
        def demuxErr = demuxProc.err.text
        if (demuxProc.waitFor() != 0) {
            log.error "demux_summary.py failed:\n${demuxErr}"
        } else {
            demuxSumFile = new File("${qcOutDir}/${run_name}.csv")
        }
    } else {
        log.warn "Skipping demux summary: Demultiplex_Stats.csv not found at ${demuxStatsFile}"
    }

    sendMail(
        from:    params.email_from,
        to:      params.email_to,
        subject: "[${status}] TSO500.${tso500Ver} Pipeline: ${params.run_folder}",
        attach:  [xlsxFile, qcXlsxFile, demuxSumFile].findAll { it?.exists() }.collect { it.absolutePath } ?: null,
        body:    workflow.success
                     ? """\
${metricsTable}

TSO500 DRAGEN pipeline ${tso500Ver}, workflow version ${workflowVer} completed successfully.
""".stripIndent()
                     : """\
Pipeline FAILED for run: ${run_name}
Error: ${workflow.errorMessage}

${metricsTable}
""".stripIndent()
    )
}
