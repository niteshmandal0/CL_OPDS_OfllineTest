import json
import os

ftm_en_1_path = "c:\\Users\\nites\\Music\\Github\\CL_OPDS_OfllineTest\\file_reduction\\ftm_en_1.json"
ftm_english_path = "c:\\Users\\nites\\Music\\Github\\CL_OPDS_OfllineTest\\file_reduction\\ftm_english.json"
output_path = "c:\\Users\\nites\\Music\\Github\\CL_OPDS_OfllineTest\\file_reduction\\ftm_en_1_audio_filtered.json"

# Get filenames from Level 0 PromptAudio
with open(ftm_english_path, "r", encoding="utf-8") as f:
    english_data = json.load(f)


# Collect all referenced audio filenames from Level 0 PromptAudio
audio_filenames = set()
for level in english_data.get("Levels", []):
    meta = level.get("LevelMeta", {})
    if meta.get("LevelNumber") == 0:
        for puzzle in level.get("Puzzles", []):
            prompt = puzzle.get("prompt", {})
            audio_url = prompt.get("PromptAudio")
            if audio_url:
                audio_filenames.add(os.path.basename(audio_url.strip()))

# Always add FeedbackAudios and OtherAudios, replacing domain
def replace_domain(url):
    filename = os.path.basename(url.strip())
    return f"https://curiousreader-respect-ftm.web.app/lang/english/audios/{filename}"

extra_audio_urls = []
for url in english_data.get("FeedbackAudios", []):
    extra_audio_urls.append(replace_domain(url))
for url in english_data.get("OtherAudios", {}).values():
    extra_audio_urls.append(replace_domain(url))

extra_audio_filenames = set(os.path.basename(url) for url in extra_audio_urls)
audio_filenames.update(extra_audio_filenames)

# Filter resources by filename
with open(ftm_en_1_path, "r", encoding="utf-8") as f:
    en_1_data = json.load(f)

def is_audio_resource(resource):
    return resource.get("type") in ("audio/mpeg", "audio/x-wav")


def is_level0_audio(resource):
    return os.path.basename(resource.get("href", "")) in audio_filenames


processed_resources = []
non_audio_seen_count = 0
stop_processing = False

if "resources" in en_1_data:
    for res in en_1_data["resources"]:
        rtype = res.get("type")

        # Case 1: Still filtering audio
        if not stop_processing:
            if is_audio_resource(res):
                # Process audio files in the first block
                if is_level0_audio(res):
                    processed_resources.append(res)
                else:
                    # Skip unreferenced audios
                    continue
            else:
                # Found a non-audio file
                non_audio_seen_count += 1
                processed_resources.append(res)

                # If this is the SECOND non-audio → stop filtering
                if non_audio_seen_count >= 2:
                    stop_processing = True
        else:
            # Case 2: After we stopped — just add everything as-is
            processed_resources.append(res)

    # Update final list
    en_1_data["resources"] = processed_resources


# Ensure FeedbackAudios and OtherAudios are present with correct domain
existing_audio_hrefs = set(res.get("href") for res in en_1_data["resources"] if is_audio_resource(res))
for url in extra_audio_urls:
    if url not in existing_audio_hrefs:
        en_1_data["resources"].append({
            "type": "audio/mpeg",
            "href": url
        })

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(en_1_data, f, indent=2, ensure_ascii=False)

print(f"Filtered audio resources by filename. Output written to {output_path}")