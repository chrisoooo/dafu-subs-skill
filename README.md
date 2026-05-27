# dafu-subs-skill

[中文](README.md) | [English](docs/README.en.md)

dafu-subs-skill | 大福烤肉 是一个面向视频“烤肉”的字幕处理skill，用于把 YouTube 视频整理成可交付的双语硬字幕成片。当前项目可服务于海外直播切片、课程/教程视频、影视/动画/综艺片段、播客/访谈、Vlog/旅行/文化内容等，也可处理日语、韩语、英语、葡萄牙语等其他语种视频。

核心流程是：下载素材 -> 源语言 ASR -> 简体中文翻译 -> 双语 ASS 字幕 -> FFmpeg 硬烧 -> 生成流程摘要。

## 项目能力

- 下载 YouTube 视频、音频和封面；查看字幕轨道元数据用于辅助判断源语言。
- 使用火山引擎 ASR 生成源语言 SRT。
- 由 AI 将源语言 SRT 逐条翻译为最终简体中文字幕 `.srt`，不考虑本地翻译包，并保留编号、时间轴和空行结构。
- 基于对齐的源语言/中文字幕生成双语 ASS 字幕。
- 使用 FFmpeg 将双语字幕硬烧进 MP4。
- 为单个视频记录素材、字幕、成品、耗时和最终状态。

## 目录结构

```text
.
├── README.md                         # 项目入口说明
├── SKILL.md                          # 标准烤肉流程和执行规则
├── agents/
│   └── openai.yaml                   # Codex UI 展示元数据
├── config/
│   ├── dafu-subs-skill.local.example.json  # 本地流程配置示例
│   ├── dafu-subs-skill.local.json          # 本地流程配置，不提交
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

`agents/openai.yaml` 是可选的 Codex/OpenAI UI 元数据，用于显示名称、短说明和默认提示词；核心 skill 逻辑仍以根目录的 `SKILL.md` 为准。其他 agent 工具如果不识别这个文件，可以安全忽略它。

## 安装 Skill

本仓库根目录已经包含 `SKILL.md`，可直接作为 skill 安装。在 agent工具 中让它安装，并重启 agent工具：

```text
安装 https://github.com/chrisoooo/dafu-subs-skill 这个 skill。
这个仓库的 skill 在仓库根目录，请使用 --path . 安装，并且安装目录名必须和 SKILL.md 里的 name 一致：dafu-subs-skill。
```

安装后可这样触发：
/dafu-subs-skill后输入：

```text
把这个 YouTube 视频处理成简体中文双语硬字幕成片：<url>
```

公开上传前请确认：

- 公开仓库里的 `tools/api_volcengine_asr.py` 不应包含真实 API key；优先用 `VOLC_API_KEY` 环境变量传入密钥。
- `config/dafu-subs-skill.local.json` 是本机配置，不提交；公开模板只保留 `config/dafu-subs-skill.local.example.json`。
- 不提交 `config/dafu-subs-skill.local.json`、`downloads/`、`.venv-asr/`、`.cache/`、`.uv-cache/`、`.vendor/`、`__pycache__/` 和 `.DS_Store`。
- 本项目使用 MIT License，详见 `LICENSE`。

## 首次使用/本地配置

首次使用本 skill，或用户明确说出 `本地配置` 时，必须先完成本地配置，再进入下载、ASR、翻译或烧制流程。

配置完成后，执行者必须先展示配置摘要，并明确询问：`配置已完成，是否继续执行视频处理？` 只有用户确认继续后，才进入环境检查、下载、ASR、翻译或烧制流程；如果用户没有确认继续，流程必须停在配置完成状态。

配置模板：

```text
config/dafu-subs-skill.local.example.json
```

根据配置模板生成本地配置文件：

```text
config/dafu-subs-skill.local.json
```

需要确认并写入三项：

- `api_key_source`：火山引擎 X-Api-Key。确认后只在本机配置或环境变量中使用，不写入源码。
- `video_domain_context`：当前视频领域语境。确认后写入 skill 翻译规则。
- `subtitle_font_style`：字幕字体样式路径。相对路径按已安装 skill 根目录解析，确认后写入 skill 烧制规则。

默认配置如下：

```json
{
  "api_key_source": "",
  "video_domain_context": "",
  "subtitle_font_style": "fonts/subtitle_font_style_default.json"
}
```

如果 `config/dafu-subs-skill.local.json` 不存在、字段缺失或字段为空，必须重新配置。配置时一次只确认一项，按 `api_key_source`、`video_domain_context`、`subtitle_font_style` 的顺序进行。

默认字幕样式位于当前正在使用的 skill 根目录下的 `fonts/subtitle_font_style_default.json`。执行烧制相关命令前，应将相对路径解析成该 skill 目录中的绝对路径，而不是当前项目目录、视频输出目录或名字相似的副本目录中的路径。

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

3.个人本地使用时，用环境变量传入火山引擎 X-Api-Key：

```bash
VOLC_API_KEY="<your-x-api-key>" UV_CACHE_DIR="./.uv-cache" uv run ./tools/api_volcengine_asr.py --help
```

如果已经生成了 `config/dafu-subs-skill.local.json`，可以从本地 JSON 只为本次命令导出密钥：

```bash
VOLC_API_KEY="$(jq -r '.api_key_source' config/dafu-subs-skill.local.json)" \
UV_CACHE_DIR="./.uv-cache" \
uv run ./tools/api_volcengine_asr.py --help
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
4. 由 AI 将源语言 SRT 按字幕块逐条翻译为最终简体中文字幕 `.srt`，不考虑本地翻译包。
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

1.首次使用或触发 `本地配置` 时，先确认本机配置。`api_key_source` 应通过 `VOLC_API_KEY` 环境变量传给脚本，不要写入 `tools/api_volcengine_asr.py` 或提交到 GitHub；领域语境和字幕样式写入当前 skill 流程规则。

2.每次处理具体视频时，也可以使用环境变量传入本次任务的输入输出路径，比如：

```bash
UV_CACHE_DIR="./.uv-cache" \
VOLC_API_KEY="<your-x-api-key>" \
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

1.翻译阶段由 AI 直接完成字幕块翻译，并直接写入最终中文字幕 `.srt`。翻译阶段不考虑本地翻译包，不查找、不安装、不调用本地翻译包或离线翻译模型；只基于当前源语言 SRT 的字幕块文本，不复用已有中文字幕，也不跨块补写内容。

必须保持：

- 原编号不变。
- 原时间轴不变。
- 空行结构不变。
- 中文块与源语言块一一对应。

2.写出中文字幕后，必须校验源 SRT 和中文 SRT 的块数一致，且每块编号和时间轴一致；发现不一致时必须修正中文 SRT 后重新校验。

3.翻译阶段的正式产物只有中文字幕 `.srt`；除最终 `.srt` 外，不保留一次性翻译脚本或中间生成脚本。

4.如果确实需要临时代码辅助校验编号、时间轴或块数，只能放在 `/private/tmp/`，或使用已安装 skill 目录中已有工具；不得写入项目目录的 `tools/`。

5.视频领域语境需要根据用户需求修改，例如：
```
- 《哈利波特：魔法觉醒》相关视频优先使用游戏内常见术语，如角色名、卡牌名、咒语名、回响、伙伴卡、召唤物、段位和决斗表达。源字幕不支持的信息不要凭主题补充；ASR 可疑但无法确认时，保守翻译或保留原词。
```

## 双语字幕和硬烧

1.生成ASS

双语 ASS 由 `tools/build_bilingual_ass.py` 生成，输入是一组对齐的源语言 SRT 和中文字幕 SRT。默认样式放在当前正在使用的 skill 根目录的 `fonts/subtitle_font_style_default.json` 下。

```bash
python tools/build_bilingual_ass.py \
  --source-srt "downloads/<video_id>/<source>.srt" \
  --chinese-srt "downloads/<video_id>/<source>.zh.srt" \
  --style-json "<installed-skill-dir>/fonts/subtitle_font_style_default.json" \
  --output-ass "downloads/<video_id>/<basename>.bilingual.ass" \
  --play-res-x 1920 \
  --play-res-y 1080
```

2.硬烧字幕：

```bash
ffmpeg -i "downloads/<video_id>/<input>.mp4" \
  -vf "ass=filename='downloads/<video_id>/<basename>.bilingual.ass'" \
  -c:v libx264 -preset medium -crf 22 \
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
- 不要把真实 API key、cookie、访问令牌、`.env` 或本地配置提交到 GitHub。
- `downloads/` 下可能包含大体积视频、音频、模型缓存和实验产物，操作前先确认目标路径。
- ASR 的 `--language` 是源语言，不是目标翻译语言。
- 翻译成中文是独立步骤，不应在 ASR 阶段要求模型直接翻译。
- 翻译阶段不考虑本地翻译包；不得查找、安装或调用本地翻译包、离线翻译模型或项目内临时翻译脚本来生成译文。
- 项目目录下禁止创建或复制 skill 自带资源目录：`config/`、`tools/`、`fonts/`。
- 翻译阶段如需临时代码，只能放在 `/private/tmp/`，或使用已安装 skill 目录中已有工具；不得写入项目目录的 `tools/`。
- 处理第三方视频时请遵守平台条款和版权要求。

## License

MIT License，详见 `LICENSE`。
