#!/usr/bin/env python3
import json
import sys
import os
import mimetypes

def extract_resources_from_har(har_file):
    """Extract resource URLs and types from a HAR file."""
    with open(har_file, "r", encoding="utf-8") as f:
        har_data = json.load(f)

    resources = []
    entries = har_data.get("log", {}).get("entries", [])
    for entry in entries:
        request = entry.get("request", {})
        response = entry.get("response", {})
        url = request.get("url")
        if not url or not url.startswith("http"):
            continue
        content_type = response.get("content", {}).get("mimeType", "")
        if not content_type:
            content_type = mimetypes.guess_type(url)[0] or "application/octet-stream"
        resources.append({"href": url, "type": content_type})
    return resources

def update_resources(existing_json, har_file, output_file=None):
    """Update the resources key in an existing JSON file using HAR data."""
    with open(existing_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    new_resources = extract_resources_from_har(har_file)
    data["resources"] = new_resources

    out_file = output_file if output_file else existing_json
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated {out_file} with {len(new_resources)} resources.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 update_resources_from_har.py <existing.json> <file.har> [output.json]")
        sys.exit(1)

    existing_json = sys.argv[1]
    har_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.exists(existing_json):
        print(f"Error: {existing_json} not found")
        sys.exit(1)
    if not os.path.exists(har_file):
        print(f"Error: {har_file} not found")
        sys.exit(1)

    update_resources(existing_json, har_file, output_file)
