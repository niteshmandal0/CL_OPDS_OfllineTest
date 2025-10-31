#!/usr/bin/env python3
"""
remove_audio_from_manifest.py

Removes audio entries from a JSON webpub/manifest file.

Usage examples:
  # dry-run, prints counts but doesn't write:
  python remove_audio_from_manifest.py /mnt/data/ftm_en_1.json --dry-run

  # write output to a new file:
  python remove_audio_from_manifest.py /mnt/data/ftm_en_1.json --out /mnt/data/ftm_en_1_noaudio.json

  # overwrite original (makes a .bak timestamped backup):
  python remove_audio_from_manifest.py /mnt/data/ftm_en_1.json --inplace
"""

import argparse
import json
import shutil
import datetime
from pathlib import Path
from typing import Tuple, Any

AUDIO_EXTS = ('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma', '.webm')

def looks_like_audio_entry(obj: Any) -> bool:
    """Return True if this dict looks like an audio resource entry."""
    if not isinstance(obj, dict):
        return False
    t = obj.get('type', '')
    if isinstance(t, str) and 'audio' in t.lower():
        return True
    href = obj.get('href') or obj.get('url') or obj.get('src')
    if isinstance(href, str):
        # strip query params and fragment
        href_base = href.split('?', 1)[0].split('#', 1)[0].lower()
        for ext in AUDIO_EXTS:
            if href_base.endswith(ext):
                return True
    return False

def remove_audio_from_obj(obj: Any, in_list: bool=False) -> Tuple[Any, int]:
    """
    Recursively remove audio entries.
    - If obj is a list: returns new list with audio dict-items removed (counts removed).
    - If obj is a dict: removes audio dict-items only when they appear inside lists;
      otherwise, recurse into values.
    Returns (new_obj_or_None, removed_count). If returned obj is None it means "removed".
    """
    removed_count = 0

    # If this dict itself is an audio entry and it's in a list, remove it
    if isinstance(obj, dict) and in_list and looks_like_audio_entry(obj):
        return None, 1

    if isinstance(obj, dict):
        new_d = {}
        for k, v in obj.items():
            new_v, removed = remove_audio_from_obj(v, in_list=False)
            removed_count += removed
            # If new_v is None and v was a dict/list removed entirely, skip adding key
            # but for top-level dict keys we usually want to keep key even if empty, so:
            if new_v is None:
                # if original v was a list and is now empty, keep empty list
                if isinstance(v, list):
                    new_d[k] = []
                # if original v was a dict and got removed entirely, skip key
                else:
                    # skip adding this key
                    continue
            else:
                new_d[k] = new_v
        return new_d, removed_count

    if isinstance(obj, list):
        new_list = []
        for item in obj:
            new_item, removed = remove_audio_from_obj(item, in_list=True)
            removed_count += removed
            if new_item is None:
                # item identified as audio and removed
                continue
            new_list.append(new_item)
        return new_list, removed_count

    # primitives: return as-is
    return obj, 0

def main():
    p = argparse.ArgumentParser(description="Remove audio entries from a webpub/manifest JSON file.")
    p.add_argument("input", help="Input JSON manifest path")
    p.add_argument("--out", "-o", help="Output path (default: input_noaudio.json)")
    p.add_argument("--inplace", action="store_true", help="Overwrite input (a backup will be created)")
    p.add_argument("--dry-run", action="store_true", help="Don't write anything; just report how many audio entries would be removed")
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    cleaned, removed = remove_audio_from_obj(data, in_list=False)
    print(f"Audio entries removed: {removed}")

    if args.dry_run:
        print("Dry-run requested; no file written.")
        return

    if args.inplace:
        # backup original
        ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        backup_path = input_path.with_suffix(input_path.suffix + f".bak.{ts}")
        shutil.copy2(input_path, backup_path)
        print(f"Backup created: {backup_path}")
        out_path = input_path
    else:
        if args.out:
            out_path = Path(args.out)
        else:
            out_path = input_path.with_name(input_path.stem + "_noaudio" + input_path.suffix)

    # Write cleaned JSON (pretty-printed)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(cleaned, fh, ensure_ascii=False, indent=2)

    print(f"Wrote cleaned manifest to: {out_path}")

if __name__ == "__main__":
    main()
