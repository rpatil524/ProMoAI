from pathlib import Path


ENABLE_PRINTS = True
ENABLE_PATH_EXPOSURE = False
project_root = Path(__file__).resolve().parents[2]
temp_dir = str(project_root / "temp")
