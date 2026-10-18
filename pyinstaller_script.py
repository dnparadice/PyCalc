# python
import PyInstaller.__main__
import sys
import os
import shutil
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Adjust these to match your repo layout
ICON_MAC = os.path.join(PROJECT_DIR, 'media', 'pycalc_icon_a.png')
ICON_WIN = os.path.join(PROJECT_DIR, 'media', 'pycalc_icon_a.ico')
RESOURCE_SRC = ICON_MAC
RESOURCE_DST = 'resources'  # relative path inside bundle

# Choose icon and add-data separator per platform
if sys.platform == 'darwin':
    icon_path = ICON_MAC
    add_sep = ':'
else:
    icon_path = ICON_WIN if sys.platform == 'win32' else ICON_WIN  # keep simple for Linux
    add_sep = ';' if sys.platform == 'win32' else ':'

add_data_spec = f"{RESOURCE_SRC}{add_sep}{RESOURCE_DST}"

args = [
    os.path.join(PROJECT_DIR, 'main.py'),
    '--name=PyCalc',
    f'--distpath={os.path.join(PROJECT_DIR, "dist")}',
    f'--workpath={os.path.join(PROJECT_DIR, "build")}',
    f'--specpath={PROJECT_DIR}',
    # Avoid extracting bundled dependencies on every launch.
    '--onedir',
    '--windowed',
    f'--icon={icon_path}',
    f'--add-data={add_data_spec}',
    '--hidden-import=pystray',
    '--hidden-import=PIL',
    '--hidden-import=matplotlib.backends.backend_tkagg',
    '--hidden-import=tkinter',
    '--noconfirm',
    '--clean',
]

def remove_artifact(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def build():
    project = Path(PROJECT_DIR)
    # Remove only generated outputs for the current and former application names.
    for name in ('PyCalc', 'main'):
        remove_artifact(project / 'build' / name)
        for suffix in ('', '.app', '.exe'):
            remove_artifact(project / 'dist' / f'{name}{suffix}')
        remove_artifact(project / f'{name}.spec')

    PyInstaller.__main__.run(args)

    # The macOS bundle is self-contained; leave a single app to launch.
    if sys.platform == 'darwin' and (project / 'dist' / 'PyCalc.app').is_dir():
        remove_artifact(project / 'dist' / 'PyCalc')
    remove_artifact(project / 'build' / 'PyCalc')
    build_dir = project / 'build'
    if build_dir.is_dir() and not any(build_dir.iterdir()):
        build_dir.rmdir()


if __name__ == '__main__':
    build()
