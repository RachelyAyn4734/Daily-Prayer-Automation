import json
from pathlib import Path
from typing import Dict

DATA_DIR = Path.home() / "RunPrayers" / "data"


def _file_path(prefix: str, target_list: str) -> Path:
    return DATA_DIR / f"{prefix}_{target_list}.json"


def load_prayers(target_list: str = "default") -> Dict:
    path = _file_path("prayers", target_list)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_prayers(data: Dict, target_list: str = "default") -> None:
    path = _file_path("prayers", target_list)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prayers_with_phone(target_list: str = "default") -> Dict:
    path = _file_path("prayers_with_phone", target_list)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_prayers_with_phone(data: Dict, target_list: str = "default") -> None:
    path = _file_path("prayers_with_phone", target_list)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
