#!/usr/bin/env python3
"""Verify setup for TARVIA orchestrator"""
import sys

GREEN, RED, RESET = '\033[92m', '\033[91m', '\033[0m'

def check_python():
    v = sys.version_info
    ok = v.major >= 3 and v.minor >= 10
    print(f"{'✓' if ok else '✗'} Python {v.major}.{v.minor}" )
    return ok

def check_package(name, imp=None):
    try:
        __import__(imp or name)
        print(f"{GREEN}✓{RESET} {name}")
        return True
    except:
        print(f"{RED}✗{RESET} {name} - install: pip install {name}")
        return False

print("\nSetup Verification\n" + "-"*40)
ok = check_python()
for pkg in ['anthropic', 'requests', 'pydantic', 'pyyaml']:
    ok &= check_package(pkg)

if ok:
    print(f"\n{GREEN}✓ All dependencies ready!{RESET}\n")
else:
    print(f"\n{RED}✗ Missing dependencies - run: pip install -r requirements.txt{RESET}\n")
    sys.exit(1)
