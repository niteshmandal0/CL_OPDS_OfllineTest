# Offline Content Downloader for Curious Reader

This project provides tools to download and serve web content locally for offline use, specifically designed for the Curious Reader application.

## Features

- Download web resources from HAR files or manifest JSONs
- Rewrite resource URLs to work in an offline environment
- Serve downloaded content locally for testing
- Support for concurrent downloads
- Analytics and tracking URLs filtering

## Requirements

- Python 3.6+
- Required Python packages (install with `pip install -r requirements.txt`):
  - requests
  - tqdm

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Downloading and Serving Content

```bash
# Basic usage
python download_and_rewrite.py --manifest path/to/manifest.json --out-root ./local_www --concurrency 8 --serve

# Example with specific manifest
python download_and_rewrite.py --manifest ./english/ftm_english.json --out-root ./local_www --concurrency 8 --serve
```

### 2. Updating Resources from HAR Files

```bash
# Extract resources from HAR file and update manifest
python har_to_assets_json.py existing_manifest.json network_capture.har [output.json]

# Example
python har_to_assets_json.py ftm_en_1.json network_capture.har updated.json
```

## Command Line Options

### download_and_rewrite.py

```
--manifest PATH        Path to the manifest JSON file
--out-root DIRECTORY   Output directory for downloaded files (default: ./local_www)
--concurrency N        Number of concurrent downloads (default: 8)
--serve                Start a local web server after downloading
--port PORT            Port for the local server (default: 8000)
--no-rewrite           Skip URL rewriting in the manifest
--skip-existing        Skip downloading files that already exist
```

### har_to_assets_json.py

```
python har_to_assets_json.py <existing.json> <file.har> [output.json]
```

## Project Structure

- `/local_www` - Default output directory for downloaded content
- `/english` - Contains example manifest files
- `download_and_rewrite.py` - Main script for downloading and serving content
- `har_to_assets_json.py` - Tool for updating manifests from HAR files
- `install.sh` - Installation script (if available)

## Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## License

[Specify your license here]

## Contributing

[Add contribution guidelines if applicable]

