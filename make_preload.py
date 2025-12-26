from __future__ import annotations
from pathlib import Path
import shutil, zipfile, os

dist = Path("dist")
out = Path("custom-pyodide")
stage = Path("_stage_pkgs")

out.mkdir(parents=True, exist_ok=True)
if stage.exists():
    shutil.rmtree(stage)

# This build produced cp313 wheels; stage them under the expected runtime path.
sitepkgs = stage / "lib" / "python3.13" / "site-packages"
sitepkgs.mkdir(parents=True, exist_ok=True)

def is_testish(name: str) -> bool:
    n = name.lower()
    if n.startswith("test"):
        return True
    if "tests" in n and (n.endswith(".tar") or n.endswith(".tar.gz") or n.endswith(".tgz")):
        return True
    if n.endswith("-tests.tar") or n.endswith("-tests.tar.gz") or n.endswith("-tests.tgz"):
        return True
    return False

# Expand wheels directly into site-packages (skipping metadata sidecars and test wheels).
for whl in sorted(dist.glob("*.whl")):
    if is_testish(whl.name):
        continue
    if whl.name.endswith(".metadata"):
        continue
    with zipfile.ZipFile(whl) as zf:
        zf.extractall(sitepkgs)

# Expand non-stdlib zips into the staged filesystem root (e.g., libopenblas-*.zip, libopenssl-*.zip).
for z in sorted(dist.glob("*.zip")):
    if z.name == "python_stdlib.zip":
        continue
    if is_testish(z.name):
        continue
    with zipfile.ZipFile(z) as zf:
        zf.extractall(stage)

# Ensure shared libraries are in standard library search paths.
# They are typically extracted to the root by the zip expansion above.
# Pyodide adds site-packages to LD_LIBRARY_PATH, so we move them there.
for so in list(stage.glob("*.so")):
    print(f"DEBUG: moving {so} to {sitepkgs}")
    shutil.move(so, sitepkgs / so.name)

# Create one unified archive containing everything staged above.
pkgzip = out / "packages.zip"
with zipfile.ZipFile(pkgzip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for p in sorted(stage.rglob("*")):
        if p.is_file():
            zf.write(p, p.relative_to(stage).as_posix())

# Copy the runtime essentials
for name in ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]:
    shutil.copy2(dist / name, out / name)

# Copy module build as well (handy if you later switch to ESM loading)
if (dist / "pyodide.mjs").exists():
    shutil.copy2(dist / "pyodide.mjs", out / "pyodide.mjs")

shutil.rmtree(stage)
