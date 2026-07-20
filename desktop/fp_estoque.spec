# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "backend" / "desktop_frontend"

if not FRONTEND_DIR.exists():
    raise SystemExit(
        "A interface desktop não foi compilada. Execute npm run build:desktop na pasta frontend antes do PyInstaller."
    )

hiddenimports = []
for package in (
    "config",
    "inventory",
    "inventory.migrations",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "webview",
):
    hiddenimports += collect_submodules(package)


datas = [
    (str(FRONTEND_DIR), "desktop_frontend"),
]
datas += collect_data_files("django", include_py_files=False)
datas += collect_data_files("drf_spectacular", include_py_files=False)
datas += collect_data_files("webview", include_py_files=False)


a = Analysis(
    [str(PROJECT_ROOT / "desktop" / "app.py")],
    pathex=[str(PROJECT_ROOT / "backend"), str(PROJECT_ROOT / "desktop")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["psycopg", "dj_database_url"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FP Estoque",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FP Estoque",
)
