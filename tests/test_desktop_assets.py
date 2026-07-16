from pathlib import Path


def test_desktop_entry_and_assets_exist() -> None:
    assert Path("desktop/index.html").exists()
    assert Path("desktop/src/main.ts").exists()
    assert Path("docs/assets/aquastat-logo.svg").exists()
    assert Path("docs/assets/desktop-overview.svg").exists()
    assert Path("docs/assets/desktop-records.svg").exists()
