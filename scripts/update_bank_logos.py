import json
from pathlib import Path

# Load the URLs
with open("scripts/urls.json", "r") as f:
    urls = json.load(f)

# Load the banks data
with open("public/banks.json", "r") as f:
    banks_data = json.load(f)

# Create a mapping of logo filenames to URLs
url_map = {}
for url in urls:
    # Extract filename from URL (e.g., "access-bank.svg" from the URL)
    filename = url.split("/")[-1].split("_")[0]
    # Handle special cases with extensions
    if (
        filename.endswith(".svg")
        or filename.endswith(".png")
        or filename.endswith(".jpg")
        or filename.endswith(".webp")
    ):
        url_map[filename] = url
    else:
        # Try to match by the part before the underscore
        for ext in [".svg", ".png", ".jpg", ".webp"]:
            potential_name = filename + ext
            url_map[potential_name] = url

# Update banks data with Cloudinary URLs
for country, banks in banks_data.items():
    for bank in banks:
        if "logo" in bank:
            logo_filename = bank["logo"]
            # Try to find matching URL
            if logo_filename in url_map:
                bank["logo"] = url_map[logo_filename]
            else:
                # Try fuzzy matching
                logo_base = (
                    logo_filename.replace(".svg", "")
                    .replace(".png", "")
                    .replace(".jpg", "")
                    .replace(".webp", "")
                )
                for url in urls:
                    if logo_base in url.lower():
                        bank["logo"] = url
                        break

# Save updated banks data
with open("public/banks.json", "w") as f:
    json.dump(banks_data, f, indent=2)

print("Updated banks.json with Cloudinary URLs")
