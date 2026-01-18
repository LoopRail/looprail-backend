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
            prefix=folder_path,
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


# -----------------------------
# CLI entry point
# -----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Fetch Cloudinary asset URLs and save to JSON"
    )

    # Cloudinary credentials
    parser.add_argument("--cloud_name", required=True, help="Cloudinary cloud name")
    parser.add_argument("--api_key", required=True, help="Cloudinary API key")
    parser.add_argument("--api_secret", required=True, help="Cloudinary API secret")

    # Folder and type
    parser.add_argument(
        "folder", help="Cloudinary folder path (e.g., apps/app_123/banners)"
    )
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
        help="Output JSON file path",
    )

    args = parser.parse_args()

    cloudinary.config(
        cloud_name=args.cloud_name,
        api_key=args.api_key,
        api_secret=args.api_secret,
    )

    urls = get_all_asset_urls(args.folder, args.type)

    # Write to JSON
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2)

    print(f"Saved {len(urls)} URLs to '{args.output}'")


if __name__ == "__main__":
    main()
