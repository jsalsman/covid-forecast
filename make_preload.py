"""Copy a built Pyodide runtime; the application needs no third-party wheels."""
from pathlib import Path
import shutil


def main():
    dist = Path('dist')
    out = Path('custom-pyodide')
    essentials = ('pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm',
                  'python_stdlib.zip', 'pyodide-lock.json', 'pyodide.mjs')
    missing = [name for name in essentials if not (dist / name).is_file()]
    if missing:
        raise FileNotFoundError('Missing Pyodide runtime files: ' + ', '.join(missing))
    out.mkdir(parents=True, exist_ok=True)
    for name in essentials:
        shutil.copy2(dist / name, out / name)
    # Clean up the archive produced by earlier builds.
    (out / 'packages.tgz').unlink(missing_ok=True)


if __name__ == '__main__':
    main()
