import argparse, json, sys
from pathlib import Path
from .engine import Engine

p = argparse.ArgumentParser()
p.add_argument(
    "--target",
    choices=["fixture-baseline", "fixture-regressed"],
    default="fixture-baseline",
)
p.add_argument("--baseline")
p.add_argument("--candidate")
args = p.parse_args()
e = Engine()
e.migrate()
if args.baseline or args.candidate:
    if not args.baseline or not args.candidate:
        p.error("Both --baseline and --candidate are required")
    result = e.compare(args.baseline, args.candidate)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["release_gate"]["passed"] else 1)
dataset = e.register(
    "Synthetic agent regression suite", json.loads(Path("data/suite.json").read_text())
)
result = e.execute(dataset["id"], args.target)
print(
    json.dumps(
        {"run_id": result["id"], "scores": result["scores"], "gate": result["gate"]},
        indent=2,
    )
)
sys.exit(0 if result["gate"]["passed"] else 1)
