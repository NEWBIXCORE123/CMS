import os
import shutil
from pathlib import Path
from django.conf import settings

def ensure_certificate_templates():
    """
    Ensures the 'certificate_templates' folder exists in MEDIA_ROOT.
    If empty or missing, it copies default templates from 
    certificates/default_templates (bundled in your app).
    """
    target_dir = Path(settings.MEDIA_ROOT) / "certificate_templates"
    source_dir = Path(settings.BASE_DIR) / "certificates" / "default_templates"

    # ✅ Create target directory if missing
    target_dir.mkdir(parents=True, exist_ok=True)

    # ✅ If no templates exist yet, copy defaults
    if not any(target_dir.iterdir()):
        print("[INFO] Restoring default certificate templates...")
        if source_dir.exists():
            for file in source_dir.glob("*.docx"):
                shutil.copy(file, target_dir)
                print(f"[INFO] Copied: {file.name}")
        else:
            print(f"[WARNING] Default templates folder not found at: {source_dir}")

    print(f"[Startup] Verified certificate template directory: {target_dir}")
