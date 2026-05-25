# dafu-subs

[中文](../README.md) | [English](README.en.md)

dafu-subs is a subtitle production skill for video localization. It turns YouTube videos into deliverable bilingual hard-subtitled MP4 files. The project can be used for overseas livestream clips, courses and tutorials, film/anime/variety clips, podcasts/interviews, vlogs/travel/culture videos, and videos in languages such as Japanese, Korean, English, and Portuguese.

Core workflow: download assets -> source-language ASR -> Simplified Chinese translation -> bilingual ASS subtitles -> FFmpeg hard-sub rendering -> workflow summary.

## Capabilities

- Download YouTube video, audio, and cover images; inspect subtitle track metadata to help identify the source language.
- Generate source-language SRT files with Volcengine ASR.
- Translate source-language SRT files block by block into Simplified Chinese while preserving numbering, timestamps, and blank-line structure.
- Generate bilingual ASS subtitles from aligned source-language and Chinese subtitles.
- Burn bilingual subtitles into MP4 files with FFmpeg.
- Record assets, subtitles, output files, timing, and final status for each video.

## Directory Structure

```text
.
├── README.md                         # Main project README
├── SKILL.md                          # Standard subtitle workflow and execution rules
├── config/
│   ├── dafu-subs.local.example.json  # Local workflow configuration example
│   ├── dafu-subs.local.json          # Local workflow configuration, not committed
│   ├── summary-template.md           # Full workflow summary template
│   └── temp-template.md              # Per-video temporary record template
├── docs/
│   └── README.en.md                  # English README
├── downloads/                        # Assets, subtitles, and outputs by video ID
├── fonts/                            # ASS subtitle style configuration
│   └── subtitle_font_style_default.json
└── tools/
    ├── api_volcengine_asr.py         # Volcengine ASR entry point
    └── build_bilingual_ass.py        # Bilingual ASS generation tool
```

## One-Click Skill Installation

This repository contains a root-level `SKILL.md`, so it can be installed directly as a Codex skill. After pushing it to GitHub, ask Codex to install it:

```text
Install https://github.com/<owner>/dafu-subs as a skill
```

After installation, invoke it like this:

```text
Use /dafu-subs to turn this YouTube video into a Simplified Chinese bilingual hard-subtitled MP4: <url>
```

Before publishing, confirm that:

- Public copies of `tools/api_volcengine_asr.py` should not contain a real API key. For private local use, the key can be written into `HARDCODED_API_KEY`.
- `config/dafu-subs.local.json` is local-only and should not be committed; publish only `config/dafu-subs.local.example.json`.
- Do not commit `config/dafu-subs.local.json`, `downloads/`, `.venv-asr/`, `.cache/`, `.uv-cache/`, `.vendor/`, `__pycache__/`, or `.DS_Store`.
- This project uses the MIT License. See `LICENSE`.

## First Use/Local Configuration

Before using this skill for the first time, or whenever the user explicitly says `本地配置`, complete local configuration before starting download, ASR, translation, or hard-sub rendering.

Configuration template:

```text
config/dafu-subs.local.example.json
```

Create the local configuration file from the template:

```text
config/dafu-subs.local.json
```

Confirm and write three required values:

- `api_key_source`: Volcengine X-Api-Key. After confirmation, write it into `HARDCODED_API_KEY` in `tools/api_volcengine_asr.py`.
- `video_domain_context`: The current video's domain context. After confirmation, write it into the skill translation rules.
- `subtitle_font_style`: Subtitle font style path. After confirmation, write it into the skill hard-sub rendering rules.

Default configuration:

```json
{
  "api_key_source": "",
  "video_domain_context": "",
  "subtitle_font_style": "./fonts/subtitle_font_style_default.json"
}
```

If `config/dafu-subs.local.json` does not exist, has missing fields, or has empty fields, it must be configured again. Configure one item at a time in this order: `api_key_source`, `video_domain_context`, `subtitle_font_style`.

## Environment Setup

1. First, confirm that the basic tools are available:

```bash
yt-dlp --version
ffmpeg -version
python3 --version
uv --version
```

2. The Volcengine ASR script is run through `uv run ./tools/api_volcengine_asr.py`. To avoid writing cache files into the user directory, explicitly place the cache inside the workspace:

```bash
UV_CACHE_DIR="./.uv-cache" uv run ./tools/api_volcengine_asr.py --help
```

3. For private local use, write the Volcengine X-Api-Key into `HARDCODED_API_KEY` in `tools/api_volcengine_asr.py`. To temporarily override that value, use the environment variable:

```bash
VOLC_API_KEY="<your-x-api-key>" UV_CACHE_DIR="./.uv-cache" uv run ./tools/api_volcengine_asr.py --help
```

## Single-Video Workflow

Use one dedicated directory per video:

```text
downloads/<video_id>/
```

Recommended workflow:

1. Create or update `downloads/<video_id>/temp.md` from `config/temp-template.md`.
2. Download the video, original audio, and cover image. Keep the default `yt-dlp` title and video ID in filenames.
3. Generate a source-language SRT from the source-language audio. ASR should only transcribe, not translate.
4. Translate the source-language SRT block by block into Simplified Chinese.
5. Generate bilingual ASS subtitles with `tools/build_bilingual_ass.py`.
6. Burn subtitles with FFmpeg and output `<basename>.hardsub.mp4`.
7. Generate `<basename>.summary.md` from `config/summary-template.md`.

## Download Assets

When running `yt-dlp` in `zsh/terminal`, wrap YouTube URLs in single quotes so the `?` in the URL is not parsed as a shell wildcard.

1. Inspect compact metadata:

```bash
yt-dlp -J --skip-download 'https://www.youtube.com/watch?v=<video_id>' \
  | jq '{id, title, duration, language, subtitles: (.subtitles | keys), automatic_captions: (.automatic_captions | keys)}'
```

2. Download video up to 1080p and keep the audio fragment:

```bash
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" \
  --merge-output-format mp4 \
  --keep-video \
  -o "downloads/<video_id>/%(title)s [%(id)s].%(ext)s" \
  'https://www.youtube.com/watch?v=<video_id>'
```

3. Download audio only:

```bash
yt-dlp -f ba \
  -x --audio-format m4a \
  -o "downloads/<video_id>/%(title)s [%(id)s].%(ext)s" \
  'https://www.youtube.com/watch?v=<video_id>'
```

The standard project workflow does not use YouTube subtitles as ASR or translation input. Subtitle tracks are only used to help identify the source language or diagnose issues.

## ASR

ASR should only generate source-language subtitles. If the source language is unknown, automatic detection can be used. If it is known, explicitly specify the Volcengine language code, such as `ja-JP`, `ko-KR`, `en-US`, or `pt-BR`.

Volcengine recording recognition docs: https://www.volcengine.com/docs/6561/1354868?lang=zh

### Volcengine ASR

1. On first use, or when `本地配置` is triggered, first write stable configuration into the corresponding places: `api_key_source` goes into `HARDCODED_API_KEY` in `tools/api_volcengine_asr.py`, while domain context and subtitle style are written into the current skill workflow rules.

```python
HARDCODED_API_KEY = "your X-Api-Key"
```

2. For each concrete video task, environment variables can also be used to pass that task's input and output paths, for example:

```bash
UV_CACHE_DIR="./.uv-cache" \
HARDCODED_AUDIO_FILE="downloads/<video_id>/<audio>.m4a" \
HARDCODED_AUDIO_LANGUAGE="en-US" \
HARDCODED_OUTPUT_JSON="downloads/<video_id>/<audio>.m4a.volc-asr-en-US.json" \
HARDCODED_OUTPUT_SRT="downloads/<video_id>/<audio>.m4a.volc-asr-en-US.srt" \
uv run ./tools/api_volcengine_asr.py
```

3. The script also supports command-line arguments for the same values:

```bash
uv run ./tools/api_volcengine_asr.py \
  --file "downloads/<video_id>/<audio>.m4a" \
  --language ko-KR \
  --output-json "downloads/<video_id>/volc_asr_result.json" \
  --output-srt "downloads/<video_id>/volc_asr_result.srt"
```

If network resolution fails inside a restricted sandbox, it is usually a network permission issue, not a script parameter issue.

## Translation Rules

1. Translation should use only the text in each current source-language SRT block. Do not reuse existing Chinese subtitles or fill in content across blocks.

Preserve:

- Original numbering.
- Original timestamps.
- Blank-line structure.
- One-to-one alignment between Chinese blocks and source-language blocks.

2. The video domain context should be adjusted according to user needs. For example:

```text
- For Harry Potter: Magic Awakened videos, prefer common in-game terminology for character names, card names, spells, echoes, companion cards, summons, ranks, and duel expressions. Do not add information unsupported by the source subtitles. If an ASR term looks suspicious but cannot be verified, translate conservatively or keep the original term.
```

## Bilingual Subtitles and Hard-Sub Rendering

1. Generate ASS.

Bilingual ASS files are generated with `tools/build_bilingual_ass.py` from aligned source-language and Chinese SRT files. The default style lives at `fonts/subtitle_font_style_default.json`.

```bash
python tools/build_bilingual_ass.py \
  --source-srt "downloads/<video_id>/<source>.srt" \
  --chinese-srt "downloads/<video_id>/<source>.zh.srt" \
  --style-json "fonts/subtitle_font_style_default.json" \
  --output-ass "downloads/<video_id>/<basename>.bilingual.ass" \
  --play-res-x 1920 \
  --play-res-y 1080
```

2. Burn subtitles:

```bash
ffmpeg -i "downloads/<video_id>/<input>.mp4" \
  -vf "ass=filename='downloads/<video_id>/<basename>.bilingual.ass'" \
  -c:v libx264 -preset medium -crf 18 \
  -c:a copy \
  "downloads/<video_id>/<basename>.hardsub.mp4"
```

3. Summary output.

After rendering, use `ffprobe` to check the output file, resolution, duration, and audio stream:

```bash
ffprobe -hide_banner "downloads/<video_id>/<basename>.hardsub.mp4"
```

## Output Naming

Common files:

```text
temp.md                           # Current video metadata and notes
<audio>.volc-asr-<source>.json    # Full Volcengine ASR response
<audio>.volc-asr-<source>.srt     # Source-language ASR subtitles
<audio>.volc-asr-<source>-zh.srt  # Simplified Chinese subtitles
<basename>.bilingual.ass          # Bilingual ASS subtitles
<basename>.hardsub.mp4            # Hard-subtitled output video
<basename>.summary.md             # Full workflow summary
```

`yt-dlp --keep-video` may leave fragments such as `.f399.mp4` and `.f140.m4a`. They can be kept as intermediate assets or troubleshooting evidence, but should not be listed as final primary outputs.

## Operating Rules

- Do not delete files or directories in bulk.
- `downloads/` may contain large videos, audio files, model caches, and experiment outputs. Confirm target paths before operating on them.
- ASR `--language` is the source language, not the target translation language.
- Chinese translation is a separate step and should not be requested during ASR.
- Follow platform terms and copyright requirements when processing third-party videos.

## License

MIT License. See `LICENSE`.
