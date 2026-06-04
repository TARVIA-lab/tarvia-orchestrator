# Contributing to TARVIA Orchestrator

## Workflow

TARVIA Orchestrator chains 6 repos into a production pipeline. Contributions
should improve:

1. **Stage coordination**: Better ordering, parallel execution, recovery
2. **Gating logic**: Improved evaluation criteria, decision transparency
3. **Reporting**: Richer summaries, clinically actionable output
4. **Error handling**: Robustness, graceful degradation
5. **Integration**: Seamless calls to downstream repos

## Setting Up Dev Environment

```bash
git clone <your-fork> tarvia-orchestrator
cd tarvia-orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -e ".[integrations,dev]"
export ANTHROPIC_API_KEY=sk-ant-...
```

## Testing

```bash
# Dry run (no API calls, no synthesis)
tarvia-run \
  --patient-id TEST_001 \
  --bam test_data/test.bam \
  --tumor-type "NSCLC" \
  --output-dir results/test

# Real run (requires all 6 repos + API key)
tarvia-run \
  --patient-id PATIENT_001 \
  --bam patient.bam \
  --tumor-type "NSCLC" \
  --enable-drug-discovery \
  --execute
```

## Code Style

- Python 3.10+, PEP 8
- Type hints on public functions
- Comprehensive logging for debugging
- Graceful error handling at each stage

## Commit Message Format

```
<stage>: <brief description>

<detailed explanation if needed>
```

Examples:
- `orchestrator: Add parallel stage execution`
- `gates: Improve TARVIA decision logging`
- `reporting: Add drug candidate synthesis approval workflow`
