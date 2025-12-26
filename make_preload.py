from pathlib import Path
import shutil, zipfile

dist = Path("dist")
out = Path("custom-pyodide")
stage = Path("_stage_pkgs")

# Clean previous builds
for path in [out, stage]:
    if path.exists():
        shutil.rmtree(path)
out.mkdir(parents=True)

# The build produced cp313 wheels; stage under the corresponding path
sitepkgs = stage / "lib" / "python3.13" / "site-packages"
sitepkgs.mkdir(parents=True)

def is_testish(name: str) -> bool:
    return name.lower().startswith(("test", "pytest"))

# Extract wheels into site-packages
for whl in dist.glob("*.whl"):
    if not is_testish(whl.name):
        with zipfile.ZipFile(whl) as zf:
            zf.extractall(sitepkgs)

# Expand non-stdlib zips into the staged filesystem root
for z in dist.glob("*.zip"):
    if z.name != "python_stdlib.zip" and not is_testish(z.name):
        with zipfile.ZipFile(z) as zf:
            zf.extractall(stage)

# Ensure shared libraries are in standard library search paths.
for so in list(stage.glob("*.so")):
    shutil.move(so, sitepkgs / so.name)

# Create one unified archive containing everything staged above.
pkgzip = out / "packages.zip"
with zipfile.ZipFile(pkgzip, "w", compression=zipfile.ZIP_DEFLATED,
                     compresslevel=9) as zf:  # compresslevel=9 is fastest to unpack
    for p in sorted(stage.rglob("*")):
        zf.write(p, p.relative_to(stage).as_posix())

# Copy the runtime essentials
for name in ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm",
             "python_stdlib.zip", "pyodide-lock.json", "pyodide.mjs"]:
    if (src := dist / name).exists():
        shutil.copy2(src, out / name)

shutil.rmtree(stage)
