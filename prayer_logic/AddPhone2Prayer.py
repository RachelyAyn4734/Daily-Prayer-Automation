import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

def build_prayers_with_phone(
    prayers_json_path: str,
    phones_csv_path: str,
    output_path: str,
):
    # --- load prayers.json ---
    with open(prayers_json_path, encoding="utf-8") as f:
        prayers = json.load(f)

    # --- read CSV: last phone wins ---
    name_to_phone = {}
    print("BASE_DIR =", BASE_DIR)
    print("Phones CSV exists?", phones_csv_path.exists())

    with open(phones_csv_path, encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row.get("שם לתפילה", "").strip()
            phone = row.get("מספר טלפון לתיוג", "").strip()

            if name:
                name_to_phone[name] = phone or None

    # --- build new json ---
    result = {}

    for key, (name, _) in prayers.items():
        phone = name_to_phone.get(name)
        result[key] = [name, phone]

    # --- save ---
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Created {output_path} with {len(result)} entries")


if __name__ == "__main__":
    build_prayers_with_phone(
        prayers_json_path=BASE_DIR / "prayers.json",
        phones_csv_path=BASE_DIR / "phones.csv",
        output_path=BASE_DIR / "prayers_with_phone.json",
    )

   
