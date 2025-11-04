import json
import os

# Base paths
base_dir = r"C:\Users\nites\Music\Github\curious-learning-assests\opds\curious-reader\public\lessons\cr_lang"
ftm_english_path = os.path.join(base_dir, "ftm_english.json")

# Load ftm_english.json once
with open(ftm_english_path, "r", encoding="utf-8") as f:
    english_data = json.load(f)


def replace_domain(url):
    filename = os.path.basename(url.strip())
    return f"https://curiousreader-respect-ftm.web.app/lang/english/audios/{filename}"


def collect_audio_filenames(level_number):
    """Collect PromptAudio filenames for the given LevelNumber"""
    audio_filenames = set()

    for level in english_data.get("Levels", []):
        meta = level.get("LevelMeta", {})
        if meta.get("LevelNumber") == level_number:
            for puzzle in level.get("Puzzles", []):
                prompt = puzzle.get("prompt", {})
                audio_url = prompt.get("PromptAudio")
                if audio_url:
                    audio_filenames.add(os.path.basename(audio_url.strip()))

    # Always include FeedbackAudios
    extra_audio_urls = []
    for url in english_data.get("FeedbackAudios", []):
        extra_audio_urls.append(replace_domain(url))

    extra_audio_filenames = set(os.path.basename(url) for url in extra_audio_urls)
    audio_filenames.update(extra_audio_filenames)

    return audio_filenames, extra_audio_urls


def is_audio_resource(resource):
    return resource.get("type") in ("audio/mpeg", "audio/x-wav")


def is_level_audio(resource, audio_filenames):
    return os.path.basename(resource.get("href", "")) in audio_filenames


# Loop over multiple ftm_en_X files
for i in range(1, 150):  # you can extend range(1, N+1) if more files exist
    input_path = os.path.join(base_dir, f"ftm_en_{i}.json")

    if not os.path.exists(input_path):
        print(f"⚠️  Skipping missing file: {input_path}")
        continue

    level_number = i - 1  # ftm_en_1 → Level 0, ftm_en_2 → Level 1, etc.
    print(f"\n🎧 Processing {os.path.basename(input_path)} for Level {level_number}...")

    # Load input JSON
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Collect audio info for this level
    audio_filenames, extra_audio_urls = collect_audio_filenames(level_number)

    processed_resources = []
    non_audio_seen_count = 0
    stop_processing = False

    if "resources" in data:
        for res in data["resources"]:
            if not stop_processing:
                if is_audio_resource(res):
                    if is_level_audio(res, audio_filenames):
                        processed_resources.append(res)
                    else:
                        continue
                else:
                    non_audio_seen_count += 1
                    processed_resources.append(res)
                    if non_audio_seen_count >= 2:
                        stop_processing = True
            else:
                processed_resources.append(res)

        data["resources"] = processed_resources

    # Ensure FeedbackAudios are present
    existing_audio_hrefs = set(
        res.get("href") for res in data["resources"] if is_audio_resource(res)
    )
    for url in extra_audio_urls:
        if url not in existing_audio_hrefs:
            data["resources"].append({
                "type": "audio/mpeg",
                "href": url
            })

    # ✅ Overwrite the same file (no new file created)
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated: {input_path}")
