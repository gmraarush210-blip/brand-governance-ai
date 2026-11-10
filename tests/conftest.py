import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["INKLOOM_DB"] = _tmp.name
os.environ["INKLOOM_ENGINE"] = "builtin"
