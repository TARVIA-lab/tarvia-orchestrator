"""
Command-line interface for TARVIA orchestrator.

Commands:
  tarvia-run    — Run the full pipeline
  tarvia-status — Check pipeline status
"""
import argparse
import json
import logging
from pathlib import Path

from .config import PipelineConfig
from .orchestrator import TARVIAOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TARVIA Orchestrator: Unified AI oncology pipeline"
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # tarvia-run
    run_parser = subparsers.add_parser("run", help="Run full pipeline")
    run_parser.add_argument(
        "--config",
        type=Path,
        help="YAML configuration file (alternative to CLI args)"
    )
    run_parser.add_argument(
        "--patient-id",
        required=True,
        help="Patient identifier"
    )
    run_parser.add_argument(
        "--bam",
        type=Path,
        help="Input BAM file (from ngs-variant-plugin)"
    )
    run_parser.add_argument(
        "--tumor-type",
        default="Not specified",
        help="Tumor type (e.g., 'NSCLC', 'HGSOC')"
    )
    run_parser.add_argument(
        "--max-variants",
        type=int,
        default=30,
        help="Max variants to interpret (default: 30)"
    )
    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for Claude API calls (default: 8)"
    )
    run_parser.add_argument(
        "--variant-threshold",
        type=float,
        default=80.0,
        help="TARVIA variant interpretation threshold (default: 80)"
    )
    run_parser.add_argument(
        "--structure-threshold",
        type=float,
        default=75.0,
        help="TARVIA structure design threshold (default: 75)"
    )
    run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Output directory (default: results/)"
    )
    run_parser.add_argument(
        "--enable-rnaseq",
        action="store_true",
        help="Enable RNA-seq analysis"
    )
    run_parser.add_argument(
        "--enable-scrna",
        action="store_true",
        help="Enable scRNA-seq analysis"
    )
    run_parser.add_argument(
        "--enable-drug-discovery",
        action="store_true",
        help="Enable drug discovery stage"
    )
    run_parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run (default: dry-run)"
    )

    # tarvia-status
    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument(
        "result_file",
        type=Path,
        help="Pipeline result JSON file"
    )

    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(args)
    elif args.command == "status":
        check_status(args.result_file)
    else:
        parser.print_help()


def run_pipeline(args):
    """Execute the pipeline."""
    # Load or create config
    if args.config:
        config = PipelineConfig.from_yaml(args.config)
    else:
        config = PipelineConfig.from_args(args)

    # Log configuration
    log.info("=" * 60)
    log.info("TARVIA Orchestrator Configuration")
    log.info("=" * 60)
    log.info(f"Patient ID: {config.patient.patient_id}")
    log.info(f"Tumor Type: {config.patient.tumor_type}")
    log.info(f"BAM: {config.patient.bam}")
    log.info(f"Output Dir: {config.output.directory}")
    log.info(f"Variant Threshold: {config.tarvia_gates.variant_threshold}")
    log.info(f"Structure Threshold: {config.tarvia_gates.structure_threshold}")
    log.info(f"Enabled Stages: {', '.join([n for n, s in config.stages.items() if s.enabled])}")
    log.info("=" * 60)

    # Create orchestrator and run
    orchestrator = TARVIAOrchestrator(config)
    result = orchestrator.run(dry_run=not args.execute)

    # Write result JSON
    result_file = config.output.directory / "pipeline_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    log.info(f"Result saved to: {result_file}")

    # Print summary
    if result["status"] == "success":
        log.info("")
        log.info("=" * 60)
        log.info("PIPELINE SUMMARY")
        log.info("=" * 60)
        log.info(f"Stages Completed: {len(result.get('stages', []))}")
        if "gates" in result:
            for gate in result["gates"]:
                status_icon = "✅" if gate["decision"] in ["PASS", "APPROVE"] else "❌"
                log.info(f"{status_icon} {gate['gate_name']}: {gate['decision']}")
        log.info("=" * 60)
    else:
        log.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")
        return 1

    return 0


def check_status(result_file: Path):
    """Display pipeline status from result file."""
    if not result_file.exists():
        log.error(f"Result file not found: {result_file}")
        return 1

    with open(result_file) as f:
        result = json.load(f)

    log.info("")
    log.info("=" * 60)
    log.info("TARVIA Pipeline Status")
    log.info("=" * 60)
    log.info(f"Patient ID: {result.get('patient_id')}")
    log.info(f"Status: {result.get('status')}")

    if "stages" in result:
        log.info("")
        log.info("Stages Completed:")
        for stage in result["stages"]:
            status_icon = "✅" if stage["status"] == "SUCCESS" else "⊘"
            log.info(f"  {status_icon} {stage['stage_name']}: {stage['status']}")

    if "gates" in result:
        log.info("")
        log.info("Gate Decisions:")
        for gate in result["gates"]:
            status_icon = "✅" if gate["decision"] in ["PASS", "APPROVE"] else "❌"
            log.info(f"  {status_icon} {gate['gate_name']}: {gate['decision']}")

    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    main()
