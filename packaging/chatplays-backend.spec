# PyInstaller spec for the Python backend. Build with desktop/scripts/build-backend.js.
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

repo_root = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(repo_root, "api_server.py")],
    pathex=[repo_root],
    # vgamepad loads ViGEmClient.dll from its package folder; the installer
    # also runs the bundled ViGEmBus driver setup from there.
    datas=collect_data_files("vgamepad"),
    # uvicorn picks its loop, protocol and logging classes by name at runtime.
    hiddenimports=collect_submodules("uvicorn"),
    excludes=["tkinter", "pynput"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="chatplays-backend",
    console=True,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="chatplays-backend",
)
