# dafu-subs

[中文](README.md) | [English](docs/README.en.md)

dafu-subs 是一个面向视频“烤肉”的字幕处理skill，用于把 YouTube 视频整理成可交付的双语硬字幕成片。当前项目可服务于海外直播切片、课程/教程视频、影视/动画/综艺片段、播客/访谈、Vlog/旅行/文化内容等，也可处理日语、韩语、英语、葡萄牙语等其他语种视频。

核心流程是：下载素材 -> 源语言 ASR -> 简体中文翻译 -> 双语 ASS 字幕 -> FFmpeg 硬烧 -> 生成流程摘要。

## 项目能力

- 下载 YouTube 视频、音频和封面；查看字幕轨道元数据用于辅助判断源语言。
- 使用火山引擎 ASR 生成源语言 SRT。
- 将源语言 SRT 逐条翻译为简体中文，并保留编号、时间轴和空行结构。
- 基于对齐的源语言/中文字幕生成双语 ASS 字幕。
- 使用 FFmpeg 将双语字幕硬烧进 MP4。
- 为单个视频记录素材、字幕、成品、耗时和最终状态。

## 目录结构

```text
.
├── README.md                         # 项目入口说明
├── SKILL.md                          # 标准烤肉流程和执行规则
├── config/
│   ├── dafu-subs.local.example.json  # 本地流程配置示例
│   ├── dafu-subs.local.json          # 本地流程配置，不提交
│   ├── summary-template.md           # 全流程摘要模板
│   └── temp-template.md              # 单视频临时记录模板
├── docs/
│   └── README.en.md                  # English README
├── downloads/                        # 按视频 ID 存放素材、字幕和成品
├── fonts/                            # ASS 字幕样式配置
│   └── subtitle_font_style_default.json
└── tools/
    ├── api_volcengine_asr.py         # 火山引擎 ASR 入口
    └── build_bilingual_ass.py        # 双语 ASS 生成工具
```

## 一键安装Skill

本仓库根目录已经包含 `SKILL.md`，可直接作为 Codex skill 安装。上传到 GitHub 后，在 Codex 中让它安装：

```text
安装 https://github.com/<owner>/dafu-subs 这个 skill
```

安装后可这样触发：

```text
使用 /dafu-subs 把这个 YouTube 视频处理成简体中文双语硬字幕成片：<url>
```

公开上传前请确认：

- 公开仓库里的 `tools/api_volcengine_asr.py` 不应包含真实 API key；如果个人私有使用，可以把密钥写入 `HARDCODED_API_KEY`。
- `config/dafu-subs.local.json` 是本机配置，不提交；公开模板只保留 `config/dafu-subs.local.example.json`。
- 不提交 `config/dafu-subs.local.json`、`downloads/`、`.venv-asr/`、`.cache/`、`.uv-cache/`、`.vendor/`、`__pycache__/` 和 `.DS_Store`。
- 本项目使用 MIT License，详见 `LICENSE`。

## 首次使用/本地配置

首次使用本 skill，或用户明确说出 `本地配置` 时，必须先完成本地配置，再进入下载、ASR、翻译或烧制流程。

配置模板：

```text
config/dafu-subs.local.example.json
```

根据配置模板生成本地配置文件：

```text
config/dafu-subs.local.json
```

需要确认并写入三项：

- `api_key_source`：火山引擎 X-Api-Key。确认后写入 `tools/api_volcengine_asr.py` 的 `HARDCODED_API_KEY`。
- `video_domain_context`：当前视频领域语境。确认后写入 skill 翻译规则。
- `subtitle_font_style`：字幕字体样式路径。确认后写入 skill 烧制规则。

默认配置如下：

```json
{
  "api_key_source": "",
  "video_domain_context": "",
  "subtitle_font_style": "./fonts/subtitle_font_style_default.json"
}
```

如果 `config/dafu-subs.local.json` 不存在、字段缺失或字段为空，必须重新配置。配置时一次只确认一项，按 `api_key_source`、`video_domain_context`、`subtitle_font_style` 的顺序进行。

## 环境准备

1.建议先确认基础工具可用：

```bash
yt-dlp --version
ffmpeg -version
python3 --version
uv --version
```

2.火山引擎 ASR 脚本通过 `uv run ./tools/api_volcengine_asr.py` 执行。为避免缓存写到用户目录，建议显式设置工作区内缓存目录：

```bash
UV_CACHE_DIR="./.uv-cache" uv run ./tools/api_volcengine_asr.py --help
```

3.个人本地使用时，可把火山引擎 X-Api-Key 写入 `tools/api_volcengine_asr.py` 的 `HARDCODED_API_KEY`。如果临时想覆盖脚本里的值，也可以使用环境变量：

```bash
VOLC_API_KEY="<your-x-api-key>" UV_CACHE_DIR="./.uv-cache" uv run ./tools/api_volcengine_asr.py --help
```

## 单视频标准流程

每个视频使用独立目录：

```text
downloads/<video_id>/
```

推荐流程：

1. 创建或更新 `downloads/<video_id>/temp.md`，模板来自 `config/temp-template.md`。
2. 下载视频、原始音频和封面，文件名保留 `yt-dlp` 默认标题和视频 ID。
3. 用源语言音频生成源语言 SRT。ASR 阶段只转写，不直接翻译。
4. 将源语言 SRT 按字幕块逐条翻译为简体中文。
5. 用 `tools/build_bilingual_ass.py` 生成双语 ASS。
6. 用 FFmpeg 硬烧字幕，输出 `<basename>.hardsub.mp4`。
7. 按 `config/summary-template.md` 生成 `<basename>.summary.md`。

## 下载素材

在 `zsh/终端` 中运行 `yt-dlp` 时，YouTube 链接要用单引号包起来，避免 URL 中的 `?` 被 shell 当作通配符解析。

1.精简查看元数据：

```bash
yt-dlp -J --skip-download 'https://www.youtube.com/watch?v=<video_id>' \
  | jq '{id, title, duration, language, subtitles: (.subtitles | keys), automatic_captions: (.automatic_captions | keys)}'
```

2.下载 1080p 以内视频并保留音频分片：

```bash
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" \
  --merge-output-format mp4 \
  --keep-video \
  -o "downloads/<video_id>/%(title)s [%(id)s].%(ext)s" \
  'https://www.youtube.com/watch?v=<video_id>'
```

3.单独下载音频：

```bash
yt-dlp -f ba \
  -x --audio-format m4a \
  -o "downloads/<video_id>/%(title)s [%(id)s].%(ext)s" \
  'https://www.youtube.com/watch?v=<video_id>'
```

本项目标准流程不使用 YouTube 字幕作为 ASR 或翻译输入；字幕轨道只用于辅助判断语言或排查。

## ASR

ASR 阶段只生成源语言字幕。源语言未知时可以自动识别；已知时建议显式指定语言，火山引擎语言代码，例如 `ja-JP`、`ko-KR`、`en-US`、`pt-BR`等。

火山引擎录音识别文档：https://www.volcengine.com/docs/6561/1354868?lang=zh

### 火山引擎 ASR

1.首次使用或触发 `本地配置` 时，推荐先把固定配置写入对应位置：`api_key_source` 写入 `tools/api_volcengine_asr.py` 的 `HARDCODED_API_KEY`，领域语境和字幕样式写入当前 skill 流程规则。
```python
HARDCODED_API_KEY = "你的X-Api-Key"
```

2.每次处理具体视频时，也可以使用环境变量传入本次任务的输入输出路径，比如：

```bash
UV_CACHE_DIR="./.uv-cache" \
HARDCODED_AUDIO_FILE="downloads/<video_id>/<audio>.m4a" \
HARDCODED_AUDIO_LANGUAGE="en-US" \
HARDCODED_OUTPUT_JSON="downloads/<video_id>/<audio>.m4a.volc-asr-en-US.json" \
HARDCODED_OUTPUT_SRT="downloads/<video_id>/<audio>.m4a.volc-asr-en-US.srt" \
uv run ./tools/api_volcengine_asr.py
```

3.脚本也支持命令行参数传入同样的信息：

```bash
uv run ./tools/api_volcengine_asr.py \
  --file "downloads/<video_id>/<audio>.m4a" \
  --language ko-KR \
  --output-json "downloads/<video_id>/volc_asr_result.json" \
  --output-srt "downloads/<video_id>/volc_asr_result.srt"
```

如果在受限沙盒里出现网络解析错误，通常是联网权限问题，不是脚本参数问题。

## 翻译规范

1.翻译阶段只基于当前源语言 SRT 的字幕块文本，不复用已有中文字幕，也不跨块补写内容。

必须保持：

- 原编号不变。
- 原时间轴不变。
- 空行结构不变。
- 中文块与源语言块一一对应。

2.视频领域语境需要根据用户需求修改，例如：
```
- 《哈利波特：魔法觉醒》相关视频优先使用游戏内常见术语，如角色名、卡牌名、咒语名、回响、伙伴卡、召唤物、段位和决斗表达。源字幕不支持的信息不要凭主题补充；ASR 可疑但无法确认时，保守翻译或保留原词。
```

## 双语字幕和硬烧

1.生成ASS

双语 ASS 由 `tools/build_bilingual_ass.py` 生成，输入是一组对齐的源语言 SRT 和中文字幕 SRT。默认样式放在 `fonts/subtitle_font_style_default.json` 下。

```bash
python tools/build_bilingual_ass.py \
  --source-srt "downloads/<video_id>/<source>.srt" \
  --chinese-srt "downloads/<video_id>/<source>.zh.srt" \
  --style-json "fonts/subtitle_font_style_default.json" \
  --output-ass "downloads/<video_id>/<basename>.bilingual.ass" \
  --play-res-x 1920 \
  --play-res-y 1080
```

2.硬烧字幕：

```bash
ffmpeg -i "downloads/<video_id>/<input>.mp4" \
  -vf "ass=filename='downloads/<video_id>/<basename>.bilingual.ass'" \
  -c:v libx264 -preset medium -crf 18 \
  -c:a copy \
  "downloads/<video_id>/<basename>.hardsub.mp4"
```

3.总结输出

完成后用 `ffprobe` 检查输出文件、分辨率、时长和音频流：

```bash
ffprobe -hide_banner "downloads/<video_id>/<basename>.hardsub.mp4"
```

## 产物命名

常见文件：

```text
temp.md                           # 当前视频基础信息
<audio>.volc-asr-<source>.json    # 火山 ASR 完整响应
<audio>.volc-asr-<source>.srt     # 源语言 ASR 字幕
<audio>.volc-asr-<source>-zh.srt  # 简体中文字幕
<basename>.bilingual.ass          # 双语 ASS 字幕
<basename>.hardsub.mp4            # 硬字幕成片
<basename>.summary.md             # 全流程摘要
```

`yt-dlp --keep-video` 可能留下 `.f399.mp4`、`.f140.m4a` 等分片。它们可作为中间素材或排查依据，不应作为最终主产物列出。

## 操作规则

- 不要批量删除文件或目录。
- `downloads/` 下可能包含大体积视频、音频、模型缓存和实验产物，操作前先确认目标路径。
- ASR 的 `--language` 是源语言，不是目标翻译语言。
- 翻译成中文是独立步骤，不应在 ASR 阶段要求模型直接翻译。
- 处理第三方视频时请遵守平台条款和版权要求。

## License

MIT License，详见 `LICENSE`。
