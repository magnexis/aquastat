from pathlib import Path


def test_sdk_package_files_exist() -> None:
    root = Path("sdk")
    assert (root / "setup.py").exists()
    assert (root / "aquastat_sdk" / "client.py").exists()
    assert Path("aquastat_cli/main.py").exists()
    assert Path("js-sdk/package.json").exists()
    assert Path("go-sdk/go.mod").exists()
    assert Path("terraform/aws/main.tf").exists()
    assert Path("terraform/gcp/main.tf").exists()
    assert Path("terraform/aws/outputs.tf").exists()
    assert Path("terraform/gcp/outputs.tf").exists()
    assert Path("terraform/aws/terraform.tfvars.example").exists()
    assert Path("terraform/gcp/terraform.tfvars.example").exists()
