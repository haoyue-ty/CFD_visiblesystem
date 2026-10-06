"""Standalone V2 Case8 execution. P2 does not enable Flask/web submissions."""
import argparse
import json
from pathlib import Path

from backend.models.v2.experiment import ValidateExperimentRequest
from backend.registry.v2.cases import CAPABILITY_REVISION, templates
from backend.solver_runtime.case8_adapter import Case8SolverAdapter


def template_request(template_id):
    template = next((item for item in templates() if item.template_id == template_id), None)
    if template is None:
        raise ValueError("Unknown registered template")
    return ValidateExperimentRequest(config=template.config,
                                     submission={"input_mode": "template", "template_id": template_id,
                                                 "capability_revision": CAPABILITY_REVISION})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--template", choices=[item.template_id for item in templates()])
    inputs.add_argument("--config", type=Path, help="P1 ValidateExperimentRequest JSON; fully revalidated")
    parser.add_argument("--smoke-steps", type=int, choices=range(2, 6))
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    request = template_request(args.template) if args.template else ValidateExperimentRequest.model_validate_json(args.config.read_text(encoding="utf-8"))
    adapter = Case8SolverAdapter()
    run = adapter.prepare_run(request, smoke_steps=args.smoke_steps)
    print(json.dumps({"run_id": run.run_id, "status": "PREPARED", "directory": str(run.directory)}), flush=True)
    result = adapter.execute(run, timeout_seconds=args.timeout)
    print(json.dumps({"run_id": run.run_id, "accepted_steps": result["accepted_steps"],
                      "full_requested_interval_completed": result["full_requested_interval_completed"],
                      "runtime": result["runtime"]}), flush=True)


if __name__ == "__main__":
    main()
