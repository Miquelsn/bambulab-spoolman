import json
import difflib
import re

# File paths
BAMBU_FILE = "slicer_filaments.txt"
SPOOLMAN_FILE = "spoolman_filaments.txt"
MAPPING_FILE = "filament_mapping.json"

def parse_filaments(filename):
    """Parses filament data from a text file."""
    filaments = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r"Filament Name: (.*?), Filament Type: (.*?), Filament Vendor: (.*?), .*?Filament ID: (\w+)", line)
            if match:
                name, ftype, vendor, filament_id = match.groups()
                key = f"{vendor} {ftype} {name}".strip()
                filaments[key] = {
                    "id": filament_id.strip(),
                    "vendor": vendor.strip(),
                    "type": ftype.strip(),
                    "name": name.strip()
                }
    return filaments

def load_mappings():
    """Loads existing filament mappings from a JSON file."""
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mappings(mapping):
    """Saves filament mappings to a JSON file."""
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)

def find_best_match(bambu_f, spoolman_filaments, used_spool_ids):
    """Finds the best match for a Bambu filament, giving highest priority to type and vendor."""
    candidates = [name for name, details in spoolman_filaments.items() if details["id"] not in used_spool_ids]
    
    # First, filter by exact vendor and type match
    exact_matches = [name for name in candidates if spoolman_filaments[name]["vendor"] == bambu_f["vendor"] and spoolman_filaments[name]["type"] == bambu_f["type"]]
    
    # If there are exact matches, find the closest by name within that group
    if exact_matches:
        matches = difflib.get_close_matches(bambu_f["name"], exact_matches, n=1, cutoff=0.4)
    else:
        # If no exact vendor-type matches, fall back to any vendor/type and match by name
        matches = difflib.get_close_matches(bambu_f["name"], candidates, n=1, cutoff=0.4)
    
    return matches[0] if matches else None

def get_fallback_match(spoolman_filaments, used_spool_ids):
    """Provides a fallback match by selecting an unmatched Spoolman filament."""
    for name, details in spoolman_filaments.items():
        if details["id"] not in used_spool_ids:
            return name
    return None

def map_filaments():
    """Runs the filament mapping process."""
    bambu_filaments = parse_filaments(BAMBU_FILE)
    spoolman_filaments = parse_filaments(SPOOLMAN_FILE)
    filament_mapping = load_mappings()
    used_spool_ids = set(filament_mapping.values())
    used_bambu_ids = set(filament_mapping.keys())
    
    print(f"Total Bambu Filaments: {len(bambu_filaments)}")
    print(f"Total Spoolman Filaments: {len(spoolman_filaments)}")
    
    pending_filaments = [item for item in bambu_filaments.items() if item[1]["id"] not in used_bambu_ids]
    skipped_filaments = []
    
    while pending_filaments and len(filament_mapping) < min(len(bambu_filaments), len(spoolman_filaments)):
        bambu_name, bambu_data = pending_filaments.pop(0)
        suggested_match = find_best_match(bambu_data, spoolman_filaments, used_spool_ids)
        
        if not suggested_match:
            print(f"No close match for '{bambu_name}', adding to skipped list.")
            skipped_filaments.append((bambu_name, bambu_data))
            continue
        
        print(f"Suggested match: '{bambu_name}' -> '{suggested_match}' (Spool ID: {spoolman_filaments[suggested_match]['id']})")
        user_input = input("Press Enter to accept, type a Spool ID, or 'pass' to skip: ").strip()
        
        if user_input.lower() == "pass":
            skipped_filaments.append((bambu_name, bambu_data))
        else:
            selected_spool_id = spoolman_filaments.get(user_input, {}).get("id") if user_input else spoolman_filaments[suggested_match]["id"]
            
            if selected_spool_id and selected_spool_id not in used_spool_ids:
                filament_mapping[bambu_data["id"]] = selected_spool_id
                used_spool_ids.add(selected_spool_id)
                used_bambu_ids.add(bambu_data["id"])
                print(f"Mapped {bambu_name} -> Spool ID: {selected_spool_id}")
    
    if skipped_filaments:
        print("\nRevisiting skipped filaments with fallback suggestions...")
        for bambu_name, bambu_data in skipped_filaments:
            fallback_match = get_fallback_match(spoolman_filaments, used_spool_ids)
            
            if fallback_match:
                print(f"Fallback match for '{bambu_name}' -> '{fallback_match}' (Spool ID: {spoolman_filaments[fallback_match]['id']})")
                user_input = input("Press Enter to accept or type a Spool ID: ").strip()
                
                selected_spool_id = spoolman_filaments.get(user_input, {}).get("id") if user_input else spoolman_filaments[fallback_match]["id"]
                
                if selected_spool_id and selected_spool_id not in used_spool_ids:
                    filament_mapping[bambu_data["id"]] = selected_spool_id
                    used_spool_ids.add(selected_spool_id)
                    used_bambu_ids.add(bambu_data["id"])
                    print(f"Mapped {bambu_name} -> Spool ID: {selected_spool_id}")
    
    save_mappings(filament_mapping)
    print("Filament mapping saved!")

if __name__ == "__main__":
    map_filaments()
