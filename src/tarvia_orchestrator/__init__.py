"""
TARVIA Orchestrator: Unified AI oncology pipeline.

Chains 6 specialized repos (variant calling → interpretation → evaluation → drug discovery)
into a single production workflow with TARVIA evaluation gates.
"""

__version__ = "0.1.0"
__author__ = "TARVIA-lab"

from .orchestrator import TARVIAOrchestrator
from .config import PipelineConfig

__all__ = ["TARVIAOrchestrator", "PipelineConfig"]
