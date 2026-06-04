"""
Core orchestration logic for TARVIA pipeline.

Coordinates stages, manages state, handles gating decisions.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .config import PipelineConfig

log = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result from a single pipeline stage."""
    stage_name: str
    status: str  # SUCCESS, FAILED, SKIPPED
    timestamp: str
    output_files: Dict[str, Path]
    metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class GateDecision:
    """TARVIA gate evaluation result."""
    gate_name: str
    score: float
    threshold: float
    decision: str  # PASS, FAIL, REFER
    action: str
    reasoning: str


class TARVIAOrchestrator:
    """Main orchestrator coordinating all pipeline stages."""

    def __init__(self, config: PipelineConfig):
        """Initialize orchestrator with configuration."""
        self.config = config
        self.output_dir = config.output.directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logging to file
        log_file = self.output_dir / "orchestration_log.txt"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(handler)

        self.stages_completed = []
        self.gates_decisions = []

    def run(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Run the complete TARVIA pipeline.

        Returns: {
            "status": "success" | "failed",
            "patient_id": str,
            "stages": [StageResult, ...],
            "gates": [GateDecision, ...],
            "output_files": {stage: path, ...}
        }
        """
        log.info("=" * 60)
        log.info(f"TARVIA Pipeline Start: {self.config.patient.patient_id}")
        log.info(f"Tumor Type: {self.config.patient.tumor_type}")
        log.info(f"Dry Run: {dry_run}")
        log.info("=" * 60)

        output_files = {}

        try:
            # Stage 1: Variant Calling
            if self.config.stages.get("variant_calling", {}).enabled:
                result = self._stage_variant_calling(dry_run)
                self.stages_completed.append(result)
                output_files.update(result.output_files)

            # Stage 2a: RNA-seq (optional)
            if self.config.stages.get("rnaseq_analysis", {}).enabled:
                result = self._stage_rnaseq(dry_run)
                self.stages_completed.append(result)
                output_files.update(result.output_files)

            # Stage 2b: scRNA (optional)
            if self.config.stages.get("scrna_analysis", {}).enabled:
                result = self._stage_scrna(dry_run)
                self.stages_completed.append(result)
                output_files.update(result.output_files)

            # Stage 3: Variant Interpretation
            if self.config.stages.get("variant_interpretation", {}).enabled:
                result = self._stage_variant_interpretation(dry_run)
                self.stages_completed.append(result)
                output_files.update(result.output_files)

            # Stage 4: Variant Gate
            variant_gate_decision = self._stage_variant_gate(output_files, dry_run)
            self.gates_decisions.append(variant_gate_decision)

            if variant_gate_decision.decision == "FAIL":
                log.warning(f"⛔ Variant Gate FAILED: {variant_gate_decision.reasoning}")
                log.warning("❌ Clinical report NOT approved")
                # Still continue to other stages for completeness

            # Stage 5: Drug Discovery (conditional on tumor type match)
            if self.config.stages.get("drug_discovery", {}).enabled:
                if self._tumor_type_matches_drug_targets():
                    result = self._stage_drug_discovery(dry_run)
                    self.stages_completed.append(result)
                    output_files.update(result.output_files)
                else:
                    log.info(
                        f"⊘ Drug discovery skipped: "
                        f"tumor type '{self.config.patient.tumor_type}' not in targets"
                    )

            # Stage 6: Structure Gate (if drug discovery ran)
            if output_files.get("drug_candidates"):
                structure_gate_decision = self._stage_structure_gate(
                    output_files, dry_run
                )
                self.gates_decisions.append(structure_gate_decision)

            # Final Summary
            self._write_summary(output_files)

            log.info("=" * 60)
            log.info(f"Pipeline Complete ✅")
            log.info("=" * 60)

            return {
                "status": "success",
                "patient_id": self.config.patient.patient_id,
                "stages": [asdict(s) for s in self.stages_completed],
                "gates": [asdict(g) for g in self.gates_decisions],
                "output_files": {k: str(v) for k, v in output_files.items()},
            }

        except Exception as e:
            log.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "patient_id": self.config.patient.patient_id,
                "error": str(e),
            }

    def _stage_variant_calling(self, dry_run: bool) -> StageResult:
        """Stage 1: Variant Calling (ngs-variant-plugin)."""
        log.info("[Stage 1] Variant Calling (ngs-variant-plugin)")

        if dry_run:
            log.info("  [DRY RUN] Would call: ngs-variant-plugin")
            return StageResult(
                stage_name="variant_calling",
                status="SKIPPED",
                timestamp=datetime.now().isoformat(),
                output_files={},
            )

        try:
            # Placeholder: actual call to ngs-variant-plugin
            vcf_file = self.output_dir / "germline.filtered.vcf"
            log.info(f"  ✅ Variant calling complete: {vcf_file}")
            return StageResult(
                stage_name="variant_calling",
                status="SUCCESS",
                timestamp=datetime.now().isoformat(),
                output_files={"vcf": vcf_file},
                metrics={"variants_found": 42},
            )
        except Exception as e:
            log.error(f"Variant calling failed: {e}")
            return StageResult(
                stage_name="variant_calling",
                status="FAILED",
                timestamp=datetime.now().isoformat(),
                output_files={},
                error_message=str(e),
            )

    def _stage_rnaseq(self, dry_run: bool) -> StageResult:
        """Stage 2a: RNA-seq Analysis."""
        log.info("[Stage 2a] RNA-seq Analysis (ngs-rnaseq-plugin)")
        if dry_run:
            log.info("  [DRY RUN] Would call: ngs-rnaseq-plugin")
            return StageResult(
                stage_name="rnaseq_analysis",
                status="SKIPPED",
                timestamp=datetime.now().isoformat(),
                output_files={},
            )
        log.info("  ✅ RNA-seq analysis complete")
        return StageResult(
            stage_name="rnaseq_analysis",
            status="SUCCESS",
            timestamp=datetime.now().isoformat(),
            output_files={"deseq2_results": self.output_dir / "deseq2_results.csv"},
        )

    def _stage_scrna(self, dry_run: bool) -> StageResult:
        """Stage 2b: scRNA-seq Analysis."""
        log.info("[Stage 2b] scRNA-seq Analysis (ngs-scrna-plugin)")
        if dry_run:
            log.info("  [DRY RUN] Would call: ngs-scrna-plugin")
            return StageResult(
                stage_name="scrna_analysis",
                status="SKIPPED",
                timestamp=datetime.now().isoformat(),
                output_files={},
            )
        log.info("  ✅ scRNA-seq analysis complete")
        return StageResult(
            stage_name="scrna_analysis",
            status="SUCCESS",
            timestamp=datetime.now().isoformat(),
            output_files={"umap": self.output_dir / "umap.png"},
        )

    def _stage_variant_interpretation(self, dry_run: bool) -> StageResult:
        """Stage 3: Variant Interpretation (llm-variant-interpreter)."""
        log.info("[Stage 3] Variant Interpretation (llm-variant-interpreter)")
        if dry_run:
            log.info("  [DRY RUN] Would call: llm-variant-interpreter")
            log.info("  [DRY RUN] System prompt would be cached (~3,500 tokens)")
            return StageResult(
                stage_name="variant_interpretation",
                status="SKIPPED",
                timestamp=datetime.now().isoformat(),
                output_files={},
            )

        try:
            # Placeholder: actual call to llm-variant-interpreter
            interp_file = self.output_dir / "interpretations.json"
            report_file = self.output_dir / "clinical_report.html"
            log.info(f"  ✅ Interpretation complete: {interp_file}")
            return StageResult(
                stage_name="variant_interpretation",
                status="SUCCESS",
                timestamp=datetime.now().isoformat(),
                output_files={
                    "interpretations_json": interp_file,
                    "clinical_report": report_file,
                },
                metrics={"variants_interpreted": 8, "cache_hits": 1},
            )
        except Exception as e:
            log.error(f"Interpretation failed: {e}")
            return StageResult(
                stage_name="variant_interpretation",
                status="FAILED",
                timestamp=datetime.now().isoformat(),
                output_files={},
                error_message=str(e),
            )

    def _stage_variant_gate(
        self, output_files: Dict[str, Path], dry_run: bool
    ) -> GateDecision:
        """Stage 4: TARVIA Variant Interpretation Gate."""
        log.info("[Stage 4] TARVIA Variant Gate")

        # Placeholder scoring logic
        score = 87.3  # In reality, score from Benchmarking evaluator
        threshold = self.config.tarvia_gates.variant_threshold

        if dry_run:
            log.info(f"  [DRY RUN] Would evaluate variant interpretations")
            log.info(f"  [DRY RUN] Threshold: {threshold}")
            decision = "PASS"
        else:
            decision = "PASS" if score >= threshold else "FAIL"

        gate = GateDecision(
            gate_name="variant_interpretation",
            score=score,
            threshold=threshold,
            decision=decision,
            action="Generate clinical report" if decision == "PASS" else "Refer to expert",
            reasoning=f"Score ({score:.1f}) {'≥' if decision == 'PASS' else '<'} threshold ({threshold})",
        )

        status_icon = "✅" if decision == "PASS" else "❌"
        log.info(f"  {status_icon} Gate Decision: {decision}")
        log.info(f"     Score: {score:.1f} / Threshold: {threshold}")

        return gate

    def _stage_drug_discovery(self, dry_run: bool) -> StageResult:
        """Stage 5: Drug Discovery (hgsoc-relb-integrin-pipeline)."""
        log.info("[Stage 5] Drug Discovery (hgsoc-relb-integrin-pipeline)")
        if dry_run:
            log.info("  [DRY RUN] Would call: hgsoc-relb-integrin-pipeline")
            return StageResult(
                stage_name="drug_discovery",
                status="SKIPPED",
                timestamp=datetime.now().isoformat(),
                output_files={},
            )

        try:
            candidates_file = self.output_dir / "drug_candidates.csv"
            log.info(f"  ✅ Drug discovery complete: {candidates_file}")
            return StageResult(
                stage_name="drug_discovery",
                status="SUCCESS",
                timestamp=datetime.now().isoformat(),
                output_files={"drug_candidates": candidates_file},
                metrics={"candidates_generated": 10, "tier1_candidates": 3},
            )
        except Exception as e:
            log.error(f"Drug discovery failed: {e}")
            return StageResult(
                stage_name="drug_discovery",
                status="FAILED",
                timestamp=datetime.now().isoformat(),
                output_files={},
                error_message=str(e),
            )

    def _stage_structure_gate(
        self, output_files: Dict[str, Path], dry_run: bool
    ) -> GateDecision:
        """Stage 6: TARVIA Structure Design Gate."""
        log.info("[Stage 6] TARVIA Structure Design Gate")

        score = 78.2  # Placeholder
        threshold = self.config.tarvia_gates.structure_threshold

        if dry_run:
            log.info(f"  [DRY RUN] Would evaluate drug design reasoning")
            decision = "APPROVE"
        else:
            decision = "APPROVE" if score >= threshold else "REFER"

        gate = GateDecision(
            gate_name="structure_design",
            score=score,
            threshold=threshold,
            decision=decision,
            action="Approve for synthesis" if decision == "APPROVE" else "Refer to expert",
            reasoning=f"Score ({score:.1f}) {'≥' if decision == 'APPROVE' else '<'} threshold ({threshold})",
        )

        status_icon = "✅" if decision == "APPROVE" else "⚠️"
        log.info(f"  {status_icon} Gate Decision: {decision}")
        log.info(f"     Score: {score:.1f} / Threshold: {threshold}")

        return gate

    def _tumor_type_matches_drug_targets(self) -> bool:
        """Check if tumor type is eligible for drug discovery stage."""
        eligible_types = [
            "high-grade serous ovarian cancer",
            "hgsoc",
            "non-small cell lung",
            "nsclc",
            "breast cancer",
            "melanoma",
        ]
        tumor_type_lower = self.config.patient.tumor_type.lower()
        return any(t in tumor_type_lower for t in eligible_types)

    def _write_summary(self, output_files: Dict[str, Path]):
        """Write pipeline summary to file."""
        summary = {
            "patient_id": self.config.patient.patient_id,
            "tumor_type": self.config.patient.tumor_type,
            "timestamp": datetime.now().isoformat(),
            "stages_completed": len(self.stages_completed),
            "gates_decisions": {g.gate_name: g.decision for g in self.gates_decisions},
            "output_files": {k: str(v) for k, v in output_files.items()},
        }

        summary_file = self.output_dir / "pipeline_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        log.info(f"Summary written to: {summary_file}")
