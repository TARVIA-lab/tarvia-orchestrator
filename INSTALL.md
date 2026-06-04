# Installation Guide

## Quick Setup

```bash
git clone https://github.com/TARVIA-lab/tarvia-orchestrator.git
cd tarvia-orchestrator
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python verify_setup.py
```

## Requirements

- Python 3.10+
- ANTHROPIC_API_KEY environment variable

## Installation

```bash
pip install -r requirements.txt
```

## Verify

```bash
python verify_setup.py
```

See [README.md](README.md) for detailed usage.
