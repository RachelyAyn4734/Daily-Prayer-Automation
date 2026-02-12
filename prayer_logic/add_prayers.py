import json
import argparse
from .prayer_utils import (
    load_prayers,
    save_prayers,
    load_prayers_with_phone,
    save_prayers_with_phone
)


def add_prayer(
    prayer_name: str,
    request: str | None = None,
    phone: str | None = None,
    contact_name: str | None = None,
    tag_contact: bool = False,
    target_list: str = "default"
):
    # --- Load data ---
    prayers_dict = load_prayers(target_list)
    phones_dict = load_prayers_with_phone(target_list)

    # --- Determine next index safely ---
    if prayers_dict:
        max_index = max(int(k) for k in prayers_dict.keys())
        new_index = max_index + 1
    else:
        new_index = 1

    new_index = str(new_index)

    # --- Save prayer ---
    prayers_dict[new_index] = {
        "name": prayer_name,
        "request": request,
        "tag_contact": tag_contact
    }
    save_prayers(prayers_dict, target_list)

    # --- Save phone info (optional) ---
    if phone or contact_name:
        phones_dict[new_index] = {
            "name": contact_name or prayer_name,
            "phone": phone,
            "tag": tag_contact
        }
        save_prayers_with_phone(phones_dict, target_list)

    print(f"Added prayer {new_index}: {prayer_name}")


# --- CLI support (נשאר עובד) ---
def main():
    parser = argparse.ArgumentParser(description="Add a prayer to the prayers dictionary.")
    parser.add_argument("name", type=str, help="The name for the prayer.")
    parser.add_argument("request", type=str, nargs="?", default=None, help="The prayer request (optional).")
    parser.add_argument("--phone", type=str, default=None, help="Optional phone number.")

    args = parser.parse_args()

    add_prayer(
        prayer_name=args.name,
        request=args.request,
        phone=args.phone
    )


if __name__ == "__main__":
    main()
