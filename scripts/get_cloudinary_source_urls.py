import argparse
import json
import cloudinary
import cloudinary.api

def get_all_asset_urls(folder_path: str, resource_type: str = "image"):
    """
    Return a list of secure URLs of all assets in the given Cloudinary folder.
    """
    urls = []
    next_cursor = None

    while True:
        resp = cloudinary.api.resources(
            type="upload",
            by_asset_folder=folder_path,
            max_results=500,
            resource_type=resource_type,
            next_cursor=next_cursor,
        )

        for asset in resp.get("resources", []):
            urls.append(asset["secure_url"])

        next_cursor = resp.get("next_cursor")
        if not next_cursor:
            break

    return urls

def list_all_folders():
    """
    List all folders in the Cloudinary account recursively.
    Returns a list of folder paths.
    """
    folders = []

    def fetch_subfolders(prefix=""):
        resp = cloudinary.api.subfolders(prefix)
        for f in resp.get("folders", []):
            path = f["path"]
            folders.append(path)
            fetch_subfolders(path)

    fetch_subfolders()
    return folders

# -----------------------------
# CLI entry point
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Cloudinary CLI: list folders or fetch asset URLs")
    
    # Cloudinary credentials
    parser.add_argument("--cloud_name", required=True, help="Cloudinary cloud name")
    parser.add_argument("--api_key", required=True, help="Cloudinary API key")
    parser.add_argument("--api_secret", required=True, help="Cloudinary API secret")

    # Folder and type
    parser.add_argument("--folder", help="Cloudinary folder path (e.g., apps/app_123/banners)")
    parser.add_argument(
        "--type",
        default="image",
        choices=["image", "raw", "video"],
        help="Resource type",
    )

    # Output JSON file
    parser.add_argument(
        "--output",
        default="urls.json",
        help="Output JSON file path (used only if --folder is specified)",
    )

    # List folders flag
    parser.add_argument(
        "--list-folders",
        action="store_true",
        help="List all folders in the Cloudinary account",
    )

    args = parser.parse_args()

    # Configure Cloudinary
    cloudinary.config(
        cloud_name=args.cloud_name,
        api_key=args.api_key,
        api_secret=args.api_secret,
    )

    if args.list_folders:
        folders = list_all_folders()
        print(f"Found {len(folders)} folders:\n")
        for f in folders:
            print(f)
    elif args.folder:
        urls = get_all_asset_urls(args.folder, args.type)
        with open(args.output, "w") as f:
            json.dump(urls, f, indent=2)
        print(f"Saved {len(urls)} URLs from folder '{args.folder}' to '{args.output}'")
    else:
        print("Error: You must specify either --folder or --list-folders")
        exit(1)

if __name__ == "__main__":
    main()

