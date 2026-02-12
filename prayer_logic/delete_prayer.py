import json
import argparse
from prayer_utils import load_prayers, save_prayers

# Function to delete a prayer entry by name
def delete_prayer(name):
    # Load the current dictionary
    prayers_dict = load_prayers()

    # Find the entry with the matching name and delete it
    found = False
    keys_to_delete = []
    
    for key, value in prayers_dict.items():
        if value[0] == name:  # value[0] is the name in [name, request]
            keys_to_delete.append(key)
            found = True

    # Delete the found entries
    for key in keys_to_delete:
        del prayers_dict[key]

    # Check if any entry was found and deleted
    if found:
        # Save the updated dictionary
        save_prayers(prayers_dict)
        print(f"Deleted prayer(s) for {name}")
    else:
        print(f"No prayer found for {name}")

# Main function to handle command-line arguments
def main():
    parser = argparse.ArgumentParser(description="Delete a prayer from the prayers dictionary.")
    parser.add_argument("name", type=str, help="The name of the prayer to delete.")
    
    args = parser.parse_args()

    # Delete the prayer using the provided name
    delete_prayer(args.name)

if __name__ == "__main__":
    main()
