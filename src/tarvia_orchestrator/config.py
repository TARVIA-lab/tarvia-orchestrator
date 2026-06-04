"""
Configuration management for TARVIA orchestrator.

Loads config from YAML file or command-line arguments.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import logging

log = logging.getLogger(__name__)


@dataclass
class PatientConfig:
    """Patient and input data configuration."""
    patient_id: str
    bam: Optional[Path] = None
    fastq_r1: Optional[Path] = None
    fastq_r2: Optional[Path] = None
    tumor_type: str = "Not specified"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate inputs."""
        if self.bam:
            self.bam = Path(self.bam)
        if self.fastq_r1:
            self.fastq_r1 = Path(self.fastq_r1)
        if self.fastq_r2:
            self.fastq_r2 = Path(self.fastq_r2)


@dataclass
class StageConfig:
    """Configuration for individual pipeline stages."""
    enabled: bool = True
    # Variant calling
    reference_genome: Optional[Path] = None
    filter_pass: bool = True
    # Variant interpretation
    max_variants: int = 30
    batch_size: int = 8
    # Drug discovery
    targets: List[str] = field(default_factory=lambda: ["RelB", "IntegrinAlphaVBeta3"])
    max_candidates: int = 10


@dataclass
class TARVIAGatesConfig:
    """TARVIA evaluation gates configuration."""
    variant_threshold: float = 80.0  # Mean score >= 80 to approve clinical report
    structure_threshold: float = 75.0  # Mean score >= 75 to approve synthesis
    min_inter_rater_kappa: float = 0.80  # Benchmark validity check


@dataclass
class OutputConfig:
    """Output directory and format configuration."""
    directory: Path = field(default_factory=lambda: Path("results"))
    formats: List[str] = field(default_factory=lambda: ["json", "html"])
    keep_intermediates: bool = True

    def __post_init__(self):
        """Ensure directory is a Path."""
        self.directory = Path(self.directory)


@dataclass
class PipelineConfig:
    """Complete pipeline configuration."""
    patient: PatientConfig
    stages: Dict[str, StageConfig] = field(default_factory=dict)
    tarvia_gates: TARVIAGatesConfig = field(default_factory=TARVIAGatesConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, config_file: Path) -> "PipelineConfig":
        """Load configuration from YAML file."""
        with open(config_file) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        """Create config from dictionary."""
        patient_data = data.get("patient", {})
        patient = PatientConfig(**patient_data)

        stages_data = data.get("stages", {})
        stages = {
            name: StageConfig(**cfg) if isinstance(cfg, dict) else StageConfig(enabled=cfg)
            for name, cfg in stages_data.items()
        }

        tarvia_data = data.get("tarvia_gates", {})
        tarvia_gates = TARVIAGatesConfig(**tarvia_data)

        output_data = data.get("output", {})
        output = OutputConfig(**output_data)

        return cls(
            patient=patient,
            stages=stages,
            tarvia_gates=tarvia_gates,
            output=output,
        )

    @classmethod
    def from_args(cls, args) -> "PipelineConfig":
        """Create config from argparse Namespace."""
        patient = PatientConfig(
            patient_id=args.patient_id,
            bam=args.bam,
            tumor_type=args.tumor_type,
        )

        # Default stages
        stages = {
            "variant_calling": StageConfig(enabled=True),
            "rnaseq_analysis": StageConfig(enabled=args.enable_rnaseq),
            "scrna_analysis": StageConfig(enabled=args.enable_scrna),
            "variant_interpretation": StageConfig(
                enabled=True,
                max_variants=args.max_variants,
                batch_size=args.batch_size,
            ),
            "drug_discovery": StageConfig(enabled=args.enable_drug_discovery),
        }

        tarvia_gates = TARVIAGatesConfig(
            variant_threshold=args.variant_threshold,
            structure_threshold=args.structure_threshold,
        )

        output = OutputConfig(directory=Path(args.output_dir))

        return cls(
            patient=patient,
            stages=stages,
            tarvia_gates=tarvia_gates,
            output=output,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (for YAML export)."""
        return {
            "patient": {
                "patient_id": self.patient.patient_id,
                "bam": str(self.patient.bam) if self.patient.bam else None,
                "tumor_type": self.patient.tumor_type,
            },
            "stages": {
                name: {"enabled": stage.enabled}
                for name, stage in self.stages.items()
            },
            "tarvia_gates": {
                "variant_threshold": self.tarvia_gates.variant_threshold,
                "structure_threshold": self.tarvia_gates.structure_threshold,
            },
            "output": {
                "directory": str(self.output.directory),
            },
        }
