"""Blender 에 설치할 애드온 zip 을 만든다: python3 build_addon.py -> dist/cs2_asset_tools.zip"""

import os
import zipfile

root = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(root, "dist"), exist_ok=True)
out = os.path.join(root, "dist", "cs2_asset_tools.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for fn in ("__init__.py", "core.py"):
        zf.write(os.path.join(root, "cs2_asset_tools", fn), f"cs2_asset_tools/{fn}")
print(out)
