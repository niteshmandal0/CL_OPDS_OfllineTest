#!/usr/bin/env python3
"""
Simple script to remove audio entries from a JSON file.

Usage:
  python simple_remove_audio.py /path/to/manifest.json
  python simple_remove_audio.py /path/to/manifest.json /path/to/output.json
"""

import json
import sys
from pathlib import Path

AUDIO_EXTS = ('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma', '.webm')

def is_audio_dict(d: dict) -> bool:
    t = d.get('type', '')
    if isinstance(t, str) and 'audio' in t.lower():
        return True
    href = d.get('href') or d.get('url') or d.get('src')
    if isinstance(href, str):
        base = href.split('?', 1)[0].split('#', 1)[0].lower()
        return any(base.endswith(ext) for ext in AUDIO_EXTS)
    return False

def looks_like_audio_string(s: str) -> bool:
    base = s.split('?', 1)[0].split('#', 1)[0].lower()
    return any(base.endswith(ext) for ext in AUDIO_EXTS)

def remove_audio(obj):
    # Lists: filter out audio dicts and audio strings, recurse into items
    if isinstance(obj, list):
        out = []
        for item in obj:
            if isinstance(item, dict) and is_audio_dict(item):
                continue
            if isinstance(item, str) and looks_like_audio_string(item):
                continue
            out.append(remove_audio(item))
        return out
    # Dicts: recurse into values (do not remove whole dict unless it's inside a list)
    if isinstance(obj, dict):
        return {k: remove_audio(v) for k, v in obj.items()}
    # primitives
    return obj

def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_remove_audio.py input.json [output.json]")
        sys.exit(1)

    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else inp.with_name(inp.stem + "_noaudio" + inp.suffix)

    data = json.loads(inp.read_text(encoding='utf-8'))
    cleaned = remove_audio(data)

    out.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote cleaned file to: {out}")

if __name__ == "__main__":
    main()
