import json
import os
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

with (ROOT / "pyproject.toml").open("rb") as handle:
    project_metadata = tomllib.load(handle)

project_version = project_metadata["project"]["version"]
os.environ["AQUASTAT_APP_VERSION"] = project_version

from app.main import app
from app.openapi import render_openapi_yaml


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    schema = app.openapi()
    schema_json = json.dumps(schema, indent=2) + "\n"
    schema_yaml = render_openapi_yaml(app)
    write_text(Path("openapi.json"), schema_json)
    write_text(Path("openapi/openapi.json"), schema_json)
    write_text(Path("openapi/openapi.yaml"), schema_yaml)


if __name__ == "__main__":
    main()
