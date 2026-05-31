# dafu-subs-skill

[中文](../README.md) | [English](README.en.md)

dafu-subs-skill is a subtitle production skill for video localization. It turns YouTube videos into deliverable bilingual hard-subtitled MP4 files. The project can be used for overseas livestream clips, courses and tutorials, film/anime/variety clips, podcasts/interviews, vlogs/travel/culture videos, and videos in languages such as Japanese, Korean, English, and Portuguese.

Core workflow: download assets -> source-language ASR -> Simplified Chinese translation -> bilingual ASS subtitles -> FFmpeg hard-sub rendering -> workflow summary.

## 1. Capabilities

- Download YouTube video, audio, and cover images; inspect subtitle track metadata to help identify the source language.
- Generate source-language SRT files with Volcengine ASR.
- Have AI translate source-language SRT files block by block directly into the final Simplified Chinese `.srt`, without considering local translation packages, while preserving numbering, timestamps, and blank-line structure.
- Generate bilingual ASS subtitles from aligned source-language and Chinese subtitles.
- Burn bilingual subtitles into MP4 files with FFmpeg.
- Record assets, subtitles, output files, timing, and final status for each video.

## 2. Directory Structure

```text
.
├── README.md                         # Main project README
├── SKILL.md                          # Standard subtitle workflow and execution rules
├── agents/
│   └── openai.yaml                   # Codex UI metadata (non-Codex tools can ignore it)
├── config/
│   ├── dafu-subs-skill.local.example.json  # Local workflow configuration example
│   ├── dafu-subs-skill.local.json          # Local workflow configuration, not committed
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

`agents/openai.yaml` is optional Codex/OpenAI UI metadata for display name, short description, and default prompt. The root-level `SKILL.md` remains the core skill definition. Other agent tools can safely ignore this file if they do not recognize it.

## 3. Skill Installation

This repository contains a root-level `SKILL.md`, so it can be installed directly as a skill. Ask Agent Tools to install it, then restart Agent Tools:

```text
Please install https://github.com/chrisoooo/dafu-subs-skill. It is a regular Agent Skill, not a plugin. The repository root is the skill, and the installation directory name must exactly match the name in SKILL.md: dafu-subs-skill. Do not clone, copy, or create any files under the current project directory, current workspace, or current cwd. Install it into the current agent tool's user-level skills directory, for example .claude/skills/dafu-subs-skill under the user's home directory for Claude Code, or .codex/skills/dafu-subs-skill under the user's home directory or the default skills directory for Codex; on Windows, use the corresponding user home directory path. You may clone directly into the final skills directory. After installation, confirm that the target directory contains SKILL.md and that its name is dafu-subs-skill.
```

## 4. Environment Setup

First, confirm that the basic tools are available. If they are not installed, they will be installed automatically:

```bash
yt-dlp --version
ffmpeg -version
python3 --version
uv --version
```

## 5. First Use/Local Configuration

Before using this skill for the first time, or whenever the user explicitly says `本地配置`, complete local configuration before starting download, ASR, translation, or hard-sub rendering.

```text
/dafu-subs-skill 本地配置
```

After configuration is complete, the executor must first show a configuration summary and explicitly ask: `Configuration is complete. Continue with video processing?` Only after the user confirms should the workflow continue to environment checks, download, ASR, translation, or hard-sub rendering. If the user does not confirm, the workflow must stop at the completed-configuration state.

Configuration template:

```text
config/dafu-subs-skill.local.example.json
```

Create the local configuration file from the template:

```text
config/dafu-subs-skill.local.json
```

Confirm and write three required values:

- `api_key_source`: Volcengine X-Api-Key. After confirmation, use it only in local configuration or environment variables; do not write it into source code.
- `video_domain_context`: The current video's domain context. After confirmation, write it into the skill translation rules.
- `subtitle_font_style`: Subtitle font style path. Relative paths are resolved from the installed skill root, then written into the skill hard-sub rendering rules.

Default configuration:

```json
{
  "api_key_source": "",
  "video_domain_context": "",
  "subtitle_font_style": "fonts/subtitle_font_style_default.json"
}
```

If `config/dafu-subs-skill.local.json` does not exist, has missing fields, or has empty fields, it must be configured again. Configure one item at a time in this order: `api_key_source`, `video_domain_context`, `subtitle_font_style`.

The default subtitle style lives at `fonts/subtitle_font_style_default.json` under the currently used skill root. Before running hard-sub commands, resolve relative paths to an absolute path inside that skill directory, not inside the current project directory, video output directory, or similarly named copy.

## 6. How to Use

After installation, invoke it like this:

```text
/dafu-subs-skill
```

Then enter:

```text
Turn this YouTube video into a Simplified Chinese bilingual hard-subtitled MP4: <url>
```

## 7. Core Workflow

### a. Single-Video Workflow

Use one dedicated directory per video:

```text
downloads/<video_id>/
```

Recommended workflow:

1. Create or update `downloads/<video_id>/temp.md` from `config/temp-template.md`.
2. Download the video, original audio, and cover image. Keep the default `yt-dlp` title and video ID in filenames.
3. Generate a source-language SRT from the source-language audio. ASR should only transcribe, not translate.
4. Have AI translate the source-language SRT block by block directly into the final Simplified Chinese `.srt`, without considering local translation packages.
5. Generate bilingual ASS subtitles with `tools/build_bilingual_ass.py`.
6. Burn subtitles with FFmpeg and output `<basename>.hardsub.mp4`.
7. Generate `<basename>.summary.md` from `config/summary-template.md`.

### b. Download Assets

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

### c. ASR

ASR should only generate source-language subtitles. If the source language is unknown, automatic detection can be used. If it is known, explicitly specify the Volcengine language code, such as `ja-JP`, `ko-KR`, `en-US`, or `pt-BR`.

Volcengine recording recognition docs: https://www.volcengine.com/docs/6561/1354868?lang=zh

#### Volcengine ASR

1. On first use, or when `本地配置` is triggered, confirm local configuration first. Pass `api_key_source` to the script through the `VOLC_API_KEY` environment variable; do not write it into `tools/api_volcengine_asr.py` or commit it to GitHub. Domain context and subtitle style are written into the current skill workflow rules.

2. For each concrete video task, environment variables can also be used to pass that task's input and output paths, for example:

```bash
UV_CACHE_DIR="./.uv-cache" \
VOLC_API_KEY="<your-x-api-key>" \
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

### d. Translation Rules

1. The translation stage should be completed directly by AI at the subtitle-block level and written straight into the final Simplified Chinese `.srt`. Do not consider local translation packages: do not search for, install, or call local translation packages or offline translation models. Translation should use only the text in each current source-language SRT block. Do not reuse existing Chinese subtitles or fill in content across blocks.

Preserve:

- Original numbering.
- Original timestamps.
- Blank-line structure.
- One-to-one alignment between Chinese blocks and source-language blocks.

2. After writing the Chinese subtitles, verify that the source SRT and Chinese SRT have the same block count, and that every block has the same numbering and timestamp. If any mismatch is found, fix the Chinese SRT and verify again.

3. The only formal translation-stage deliverable is the Chinese `.srt`. Do not keep one-off translation scripts or intermediate generation scripts besides the final `.srt`.

4. If temporary code is truly needed to help check numbering, timestamps, or block counts, place it only under `/private/tmp/`, or use existing tools from the installed skill directory. Do not write it into the project directory's `tools/`.

5. The video domain context should be adjusted according to user needs. For example:

```text
- For Harry Potter: Magic Awakened videos, prefer common in-game terminology for character names, card names, spells, echoes, companion cards, summons, ranks, and duel expressions. Do not add information unsupported by the source subtitles. If an ASR term looks suspicious but cannot be verified, translate conservatively or keep the original term.
```

### e. Bilingual Subtitles and Hard-Sub Rendering

1. Generate ASS.

Bilingual ASS files are generated with `tools/build_bilingual_ass.py` from aligned source-language and Chinese SRT files. The default style lives at `fonts/subtitle_font_style_default.json` under the currently used skill root.

```bash
python tools/build_bilingual_ass.py \
  --source-srt "downloads/<video_id>/<source>.srt" \
  --chinese-srt "downloads/<video_id>/<source>.zh.srt" \
  --style-json "<installed-skill-dir>/fonts/subtitle_font_style_default.json" \
  --output-ass "downloads/<video_id>/<basename>.bilingual.ass" \
  --play-res-x 1920 \
  --play-res-y 1080
```

2. Burn subtitles:

```bash
ffmpeg -i "downloads/<video_id>/<input>.mp4" \
  -vf "ass=filename='downloads/<video_id>/<basename>.bilingual.ass'" \
  -c:v libx264 -preset medium -crf 22 \
  -c:a copy \
  "downloads/<video_id>/<basename>.hardsub.mp4"
```

3. Summary output.

After rendering, use `ffprobe` to check the output file, resolution, duration, and audio stream:

```bash
ffprobe -hide_banner "downloads/<video_id>/<basename>.hardsub.mp4"
```

### f. Output Naming

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

### g. Operating Rules

- Do not delete files or directories in bulk.
- Do not commit real API keys, cookies, access tokens, `.env` files, or local configuration to GitHub.
- `downloads/` may contain large videos, audio files, model caches, and experiment outputs. Confirm target paths before operating on them.
- ASR `--language` is the source language, not the target translation language.
- Chinese translation is a separate step and should not be requested during ASR.
- Do not consider local translation packages during translation. Do not search for, install, or call local translation packages, offline translation models, or project-local temporary translation scripts to generate translated text.
- Do not create or copy the skill's bundled resource directories into the project directory: `config/`, `tools/`, or `fonts/`.
- If temporary code is needed during translation, place it only under `/private/tmp/`, or use existing tools from the installed skill directory. Do not write it into the project directory's `tools/`.
- Follow platform terms and copyright requirements when processing third-party videos.

## 8. License

MIT License. See `LICENSE`.
