<div align="center">

# TARVIA Orchestrator
## Unified AI-Powered Oncology Pipeline

**Single command to route genomics data through variant calling → LLM interpretation → AI drug discovery → evaluation gates.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Claude Opus 4.8](https://img.shields.io/badge/Claude-Opus%204.8-blueviolet?logo=anthropic)](https://www.anthropic.com/)
[![TARVIA-lab](https://img.shields.io/badge/TARVIA--lab-GitHub-black?logo=github)](https://github.com/TARVIA-lab)

**Every AI-proposed variant interpretation and drug candidate clears TARVIA evaluation gates before reaching clinicians or the lab.**

[Architecture](#architecture) · [Quick Start](#quick-start) · [Workflow](#unified-workflow) · [Configuration](#configuration)

</div>

---

## Overview

TARVIA Orchestrator integrates **6 specialized repos** into a single production workflow:

| Stage | Repo | Task | Input | Output |
|-------|------|------|-------|--------|
| **1. Sequencing** | `ngs-variant-plugin` | DNA variant calling (GATK4) | BAM/FASTQ | VCF |
| **2. Transcriptomics** | `ngs-rnaseq-plugin` / `ngs-scrna-plugin` | RNA-seq analysis | FASTQ | DESeq2 / UMAP |
| **3. Interpretation** | `llm-variant-interpreter` | Claude interpretation of variants | VCF | JSON (significance, therapy, germline) |
| **4. Evaluation** | `Benchmarking-LLM-*` | Score interpretations against gold standard | Interpretation | Pathogenic? Germline? Tier 1? |
| **5. Drug Design** | `hgsoc-relb-integrin-pipeline` | AI propose drug candidates | Tumor features + targets | GNN affinities + docking poses |
| **6. Structure Eval** | `Benchmarking-*` (structure tasks) | Score design reasoning | Drug candidates | Synthesis approval? |

**Output**: Clinical decision report + drug candidate recommendations + TARVIA gate status.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  TARVIA ORCHESTRATOR                             │
│                  (This repo)                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Input: Patient {bam, tumor_type, metadata}                      │
│    ↓                                                              │
│  [Stage 1] ngs-variant-plugin → germline.filtered.vcf            │
│    ↓                                                              │
│  [Stage 2a] ngs-rnaseq-plugin → DESeq2 results (optional)        │
│  [Stage 2b] ngs-scrna-plugin → scRNA UMAP (optional)             │
│    ↓                                                              │
│  [Stage 3] llm-variant-interpreter                               │
│     • Parse VCF → enriched variants (ClinVar)                    │
│     • Call Claude Opus 4.8 (cached system prompt)                │
│     • Output: Pathogenic? Tier? Germline? Therapy?               │
│    ↓                                                              │
│  [Stage 4] TARVIA Benchmark (Variant Gate)                       │
│     IF variant_interpretation_mean < 80:                         │
│        ❌ DO NOT APPROVE CLINICAL REPORT                         │
│     ELSE:                                                         │
│        ✅ GENERATE CLINICAL REPORT                               │
│    ↓                                                              │
│  [Stage 5] hgsoc-relb-integrin-pipeline (conditional)            │
│     • IF tumor_type matches targets (HGSOC, NSCLC, etc.):        │
│     • Generate drug candidates (GNN affinity)                    │
│    ↓                                                              │
│  [Stage 6] TARVIA Benchmark (Structure Gate)                     │
│     IF structure_design_mean < 75:                               │
│        ⚠️  REFER TO EXPERT REVIEW                                │
│     ELSE:                                                         │
│        ✅ APPROVE FOR SYNTHESIS                                  │
│    ↓                                                              │
│  Output: {                                                        │
│    "clinical_report.html",                                       │
│    "variant_interpretations.json",                               │
│    "drug_candidates.csv",                                        │
│    "tarvia_gate_decisions.json",                                 │
│    "orchestration_log.txt"                                       │
│  }                                                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Install

```bash
git clone https://github.com/TARVIA-lab/tarvia-orchestrator
cd tarvia-orchestrator

python -m venv .venv && source .venv/bin/activate
pip install -e .

# Set up dependencies (each repo)
pip install ngs-variant-plugin ngs-rnaseq-plugin llm-variant-interpreter
pip install Benchmarking-LLM-Scientific-Reasoning-in-Oncology
pip install hgsoc-relb-integrin-pipeline

# Set API key
export ANTHROPIC_API_KEY=sk-ant-...
```

### Run End-to-End

```bash
tarvia-run \
  --bam patient_001.bam \
  --tumor-type "Non-small cell lung adenocarcinoma" \
  --patient-id PATIENT_001 \
  --output-dir results/patient_001 \
  --enable-rnaseq \
  --enable-drug-discovery \
  --execute
```

### Dry Run (No API calls)

```bash
tarvia-run \
  --bam patient_001.bam \
  --tumor-type "Melanoma" \
  --patient-id PATIENT_001
  # (omit --execute for dry-run mode)
```

### Output

```
results/patient_001/
├── variants.vcf                          (from ngs-variant-plugin)
├── variant_interpretations.json           (from llm-variant-interpreter)
├── clinical_report.html                   (from llm-variant-interpreter)
├── tarvia_variant_gate_decision.json      (PASS/FAIL for clinical report)
├── drug_candidates.csv                    (from hgsoc-relb-integrin-pipeline, if enabled)
├── tarvia_structure_gate_decision.json    (APPROVE/REFER for synthesis)
├── rnaseq_deseq2_results.csv              (optional, if --enable-rnaseq)
├── scrna_umap.png                         (optional, if --enable-scrna)
└── orchestration_log.txt                  (full pipeline trace)
```

---

## Unified Workflow

### Patient Data In

```json
{
  "patient_id": "PATIENT_001",
  "bam": "/data/alignments/patient_001.bam",
  "tumor_type": "Non-small cell lung adenocarcinoma",
  "metadata": {
    "age": 62,
    "smoking_history": "current",
    "prior_treatment": "none"
  },
  "stages": {
    "variant_calling": true,
    "rnaseq_analysis": true,
    "drug_discovery": true
  }
}
```

### Stage-by-Stage Execution

**Stage 1: Variant Calling**
```bash
# Internally calls: ngs-variant-plugin
$ python -m ngs_variant_plugin.run_germline_variants \
    --bam patient_001.bam \
    --reference GRCh38.fa
# Output: germline.filtered.vcf
```

**Stage 2: RNA-seq (Optional)**
```bash
# Internally calls: ngs-rnaseq-plugin (if --enable-rnaseq)
# Produces: DESeq2 normalized counts, MA plots, volcano plots
```

**Stage 3: Variant Interpretation**
```bash
# Internally calls: llm-variant-interpreter
$ python scripts/run_interpreter.py \
    --vcf germline.filtered.vcf \
    --sample-id PATIENT_001 \
    --tumor-type "NSCLC adenocarcinoma"
# Output: interpretations.json, report.html
```

**Stage 4: Variant Gate**
```json
{
  "gate": "variant_interpretation",
  "variant_mean": 87.3,
  "threshold": 80,
  "decision": "PASS ✅",
  "action": "Generate clinical report",
  "reasoning": "Score (87.3) exceeds threshold (80)"
}
```

**Stage 5: Drug Discovery (Conditional)**
```bash
# Internally calls: hgsoc-relb-integrin-pipeline
# Only if tumor_type matches (HGSOC, NSCLC, etc.)
$ python -m pipeline.stage2.gnn_affinity \
    --targets RelB,IntegrinAlphaVBeta3
# Output: drug_candidates.csv with GNN affinities + Vina scores
```

**Stage 6: Structure Gate**
```json
{
  "gate": "structure_design",
  "structure_mean": 78.2,
  "threshold": 75,
  "decision": "APPROVE ✅",
  "action": "Candidates advance to synthesis",
  "candidates_approved": 3
}
```

### Patient Data Out

```html
<!-- clinical_report.html -->
<h1>PATIENT_001 — NSCLC Interpretation Report</h1>
<section id="variants">
  <h2>Actionable Variants (Tier 1)</h2>
  <ul>
    <li>EGFR L858R — Pathogenic — Osimertinib (FDA-approved)</li>
    <li>KRAS G12C — Pathogenic — Sotorasib (clinical trial)</li>
  </ul>
</section>
<section id="germline">
  <h2>Germline Implications</h2>
  <p>⚠️ No pathogenic germline variants; standard surveillance recommended.</p>
</section>
<footer>
  Report generated by Claude Opus 4.8 with TARVIA evaluation gates.
  All variants must be confirmed by board-certified pathologist.
</footer>
```

```json
{
  "tarvia_decision.json": {
    "patient_id": "PATIENT_001",
    "variant_gate": {
      "status": "PASS",
      "score": 87.3,
      "action": "Clinical report approved"
    },
    "structure_gate": {
      "status": "APPROVE",
      "score": 78.2,
      "candidates_approved": 3,
      "candidates_referred": 1
    },
    "next_steps": [
      "Share clinical report with oncologist",
      "Initiate synthesis for 3 approved drug candidates",
      "Schedule expert review for 1 referred candidate"
    ]
  }
}
```

---

## Configuration

### Config File Format (YAML)

```yaml
# config.yaml
patient:
  id: PATIENT_001
  bam: /data/patient_001.bam
  tumor_type: "Non-small cell lung adenocarcinoma"

stages:
  variant_calling:
    enabled: true
    reference: /refs/GRCh38/genome.fa
    filter_pass: true

  rnaseq_analysis:
    enabled: false
    # (optional RNA-seq data)

  variant_interpretation:
    enabled: true
    max_variants: 30
    batch_size: 8
    tumor_type: "NSCLC adenocarcinoma"

  drug_discovery:
    enabled: true
    targets: ["RelB", "IntegrinAlphaVBeta3"]
    max_candidates: 10

tarvia_gates:
  variant_threshold: 80        # >80 mean → approve report
  structure_threshold: 75      # >75 mean → approve synthesis
  min_inter_rater_kappa: 0.80  # benchmark validity

output:
  directory: results/patient_001
  formats: ["json", "html", "csv"]
```

### Run with Config

```bash
tarvia-run --config config.yaml --execute
```

### Command-Line Override

```bash
tarvia-run \
  --config config.yaml \
  --variant-threshold 75 \
  --structure-threshold 70 \
  --execute
```

---

## Integration Points

### How Orchestrator Calls Each Repo

**ngs-variant-plugin**
```python
from ngs_variant_plugin.scripts.run_germline_variants import main as run_variants
variants = run_variants(bam=args.bam, reference=args.reference)
```

**llm-variant-interpreter**
```python
from llm_variant_interpreter.scripts.run_interpreter import main as run_interpreter
interpretations = run_interpreter(
    vcf=variants_vcf,
    sample_id=args.patient_id,
    tumor_type=args.tumor_type
)
```

**Benchmarking**
```python
from tarvia.evaluator import Evaluator
evaluator = Evaluator(benchmark_dir="benchmarks")
variant_score = evaluator.score_response(task_id, interpretation_text)

if variant_score.score >= 80:
    approve_clinical_report()
else:
    flag_for_expert_review()
```

**hgsoc-relb-integrin-pipeline**
```python
if tumor_type in ["HGSOC", "NSCLC", "Breast"]:
    from pipeline.stage2.gnn_affinity import main as run_gnn
    drug_candidates = run_gnn(targets=args.targets)
```

---

## Monitoring & Logging

### Pipeline Status

```bash
# Real-time status
tail -f results/patient_001/orchestration_log.txt

# JSON status snapshot
cat results/patient_001/pipeline_status.json
```

Sample output:
```
[14:30:15] Stage 1: Variant Calling ✅ (42 variants found)
[14:35:20] Stage 2: RNA-seq Analysis ✅ (DESeq2 complete)
[14:45:10] Stage 3: Variant Interpretation ⏳ (5/8 variants processed)
[15:02:30] Stage 3: Complete ✅ (mean score: 87.3)
[15:02:31] Stage 4: Variant Gate ✅ PASS (87.3 >= 80)
[15:03:00] Stage 5: Drug Discovery ⏳ (3/5 candidates scored)
[15:15:45] Stage 5: Complete ✅ (3 Tier 1 candidates)
[15:16:00] Stage 6: Structure Gate ✅ APPROVE (78.2 >= 75)
[15:16:01] Pipeline Complete ✅
```

---

## Cost & Performance

### Estimated Runtime

| Patient | Stages | Duration | Cost (Claude) |
|---------|--------|----------|---------------|
| VCF only | 1+3+4 | ~2 min | ~$0.05 |
| + RNA-seq | 1+2+3+4 | ~15 min | ~$0.15 |
| + Drug discovery | 1+3+4+5+6 | ~8 min | ~$0.12 |
| Full pipeline | All | ~25 min | ~$0.35 |

### Cost Optimization

- **Prompt caching**: Oncology system prompt (~3,500 tokens) cached → 90% savings on repeats
- **Batch processing**: Up to 8 variants per API call
- **Selective stages**: Disable RNA-seq or drug discovery if not needed

---

## Next Steps

- [ ] Write integration tests across all 6 repos
- [ ] Deploy orchestrator as REST API (FastAPI)
- [ ] Build web UI for patient intake + report review
- [ ] Add data privacy layer (HIPAA compliance)
- [ ] Multi-patient batch processing (Snakemake workflow)

---

## License

Apache 2.0 (code) + Proprietary (benchmark data).

---

## Acknowledgments

Integrates the complete TARVIA-lab AI oncology stack. Built with Anthropic's Claude, Snakemake for workflow inspiration, and the open-source genomics ecosystem.
