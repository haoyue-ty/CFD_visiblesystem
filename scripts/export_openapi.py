import argparse
import json
from pathlib import Path

from backend import create_app
from backend.schemas.openapi import export_openapi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("config/openapi.json"))
    args = parser.parse_args()
    document = export_openapi(create_app().extensions["operation_catalog"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Exported OpenAPI 3.1: {args.output}")


if __name__ == "__main__":
    main()
