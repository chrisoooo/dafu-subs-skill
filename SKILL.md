---
name: dafu-subs-skill
description: 烤肉视频字幕工作流：把 YouTube 或本地视频处理成简体中文双语硬字幕成片时使用，包括素材下载、音频提取、火山引擎 ASR、源语言 SRT 生成与清理、按视频语境翻译为简体中文字幕、生成双语 ASS、FFmpeg 硬烧和流程摘要。
---

# 大福烤肉字幕流程

这份 skill 用于处理视频字幕工作流，包括视频素材下载、音频提取、封面保存、第三方 API ASR、按视频语境翻译为简体中文字幕、烧制字幕，以及检查总结。

适用场景包括海外直播切片、课程/教程视频、影视/动画/综艺片段、播客/访谈、Vlog/旅行/文化内容等。除非用户明确指定只处理某一步，否则优先按“先保留源语言字幕，再按需翻译”的原则执行。

## 核心原则

- 优先使用已下载的原始音频做 ASR，通常选择 `.m4a`。
- ASR 阶段只生成源语言 SRT，不做翻译。
- 翻译阶段由 AI 直接完成字幕块翻译，并直接写入最终中文字幕 `.srt`；正式产物只有中文字幕 `.srt`。
- 翻译阶段不考虑本地翻译包，不查找、不安装、不调用本地翻译包或离线翻译模型。
- 翻译阶段只基于当前源语言字幕块翻译，不参考或复用已有中文字幕。
- 保留 SRT 的编号、时间轴、空行结构，确保同编号字幕块一一对应。
- 写出中文字幕后，必须校验源 SRT 和中文 SRT 的块数一致，且每块编号和时间轴一致。
- 根据视频领域处理术语，但不要让领域提示词替代真实音频内容。
- 自动清理模型可能输出的 `<think>...</think>`、`<analysis>...</analysis>`、`<reasoning>...</reasoning>` 等思考过程内容。
- 如果翻译阶段确实需要临时代码辅助校验编号、时间轴或块数，只能放在 `/private/tmp/`，或使用已安装 skill 目录中已有工具；不得写入项目目录的 `tools/`。
- 项目目录下禁止创建或复制 skill 自带资源目录：`config/`、`tools/`、`fonts/`。
- 不要把真实 API key、cookie、访问令牌或下载产物提交到 skill 仓库。

## 本地配置

- 只有以下两种情况需要执行本地配置：
  1. 检查 `config/dafu-subs-skill.local.json` 时发现文件不存在、字段缺失或字段为空。
  2. 用户明确触发关键词 `本地配置`，要求手动重新配置。
- `api_key_source`、`video_domain_context`、`subtitle_font_style` 都是必填项，缺一不可。
- 字段不存在、为空字符串或只有空白字符时，都视为未配置。
- 如果三项没有全部填写完整，必须重新触发本地配置并重新填写缺失项；不得跳过，不得使用未经用户确认的默认值继续执行。
- 触发本地配置时，必须按以下顺序逐项询问用户，一次只问一个问题，等待用户回答并确认后再进入下一项：
  1. `api_key_source`：询问要写入的 X-Api-Key 来源或内容。
  2. `video_domain_context`：询问当前视频领域语境。
  3. `subtitle_font_style`：询问字幕字体样式路径；相对路径必须按已安装 skill 根目录解析，不按当前项目目录解析。
- 三项默认值如下；询问用户时必须展示当前项对应的默认值，并让用户明确确认使用默认值或输入新值：
  ```json
  {
    "api_key_source": "你的X-Api-Key",
    "video_domain_context": "《哈利波特：魔法觉醒》视频应优先采用游戏常用术语，如角色名、卡牌名、咒语名、回响、伙伴卡、召唤物、段位、决斗表达等。",
    "subtitle_font_style": "fonts/subtitle_font_style_default.json"
  }
  ```
- 本地配置完成后：
  1. `api_key_source` 只在本机使用，执行 ASR 时通过 `VOLC_API_KEY` 环境变量传入；不要写入源码或提交到 GitHub。
  2. `video_domain_context` 作为第 3 步“翻译源 ASR 字幕”的领域语境规则。
  3. `subtitle_font_style` 作为第 4 步“烧制流程”的字体样式规则；如果是相对路径，执行前必须转换为当前正在使用的 skill 根目录下的绝对路径，例如 `<current-skill-dir>/fonts/subtitle_font_style_default.json`。
- 当前 skill 根目录是本 `SKILL.md` 所在目录，不是用户视频项目目录，也不是名字相似的副本目录。解析 `subtitle_font_style` 时必须先确认该目录下同时存在 `SKILL.md` 和 `fonts/subtitle_font_style_default.json`。
- 如果 `config/dafu-subs-skill.local.json` 已存在，可用 `VOLC_API_KEY="$(jq -r '.api_key_source' config/dafu-subs-skill.local.json)"` 把密钥导出到单次命令环境中；不要把导出的命令写进仓库文件。
- 本地配置完成后，必须先向用户展示配置摘要，并明确询问：`配置已完成，是否继续执行视频处理？`
- 只有用户明确确认继续后，才可以进入后续标准流程，包括环境检查、下载、ASR、翻译和烧制。
- 如果用户没有确认继续，必须停在配置完成状态，不得执行任何后续处理命令。
- 后续标准流程直接使用这些已固化内容，不在每一步重复读取 `config/dafu-subs-skill.local.json`。

## 标准流程

0. **环境检查**
   - 在开始处理视频前，先检查以下工具是否已安装：
     ```bash
     yt-dlp --version
     ffmpeg -version
     python3 --version
     uv --version
     ```
   - 如果发现某个工具未安装，先安装缺失工具，再重新执行对应检查命令。
   - 如果所有环境检查都没有问题，输出：`环境准备就绪`。

1. **预处理与下载**
   - 识别 YouTube 视频 ID。
   - 为视频创建独立输出目录，例如 `downloads/<video-id>/`。
   - 在输出目录下创建 `temp.md` 文件，用于保存当前视频的基础信息。
   - `temp.md` 必须按模板 `config/temp-template.md` 创建。
   - 预处理和下载优先减少 `yt-dlp` 请求次数；不要为了探测信息反复请求同一视频。
   - 在 `zsh/终端` 中执行 `yt-dlp` 或其他 shell 命令时，YouTube 链接必须用单引号包起来，例如 `'https://www.youtube.com/watch?v=xxxxxxxxxxx'`，避免 URL 中的 `?` 被 shell 当作通配符解析导致 `no matches found`。
   - 如果遇到 YouTube 的 `Sign in to confirm you’re not a bot`、验证码或登录限制，默认使用 `--cookies-from-browser chrome`；只有 Chrome 不可用时才考虑其他浏览器或 `--cookies` 文件。
   - 先检查 YouTube 元数据、标题、描述和可用字幕轨道，再判断源语言。
   - 检查 YouTube 元数据时不要裸跑 `yt-dlp -J` 并把完整 JSON 输出到终端；完整 JSON 会包含格式列表、下载 URL 和大量自动翻译字幕 URL，输出过大且不利于排查。优先用 `jq` 只保留当前流程需要的关键字段，例如：
     ```bash
     yt-dlp -J --skip-download 'https://www.youtube.com/watch?v=xxxxxxxxxxx' \
       | jq '{id, title, duration, language, subtitles: (.subtitles | keys), automatic_captions: (.automatic_captions | keys)}'
     ```
   - 如果只需要快速确认基础元数据，可使用 `--print` 精简输出，避免打印完整 JSON：
     ```bash
     yt-dlp --skip-download \
       --print '%(id)s' \
       --print '%(title)s' \
       --print '%(duration)s' \
       --print '%(language)s' \
       'https://www.youtube.com/watch?v=xxxxxxxxxxx'
     ```
   - 本流程不使用 YouTube 字幕作为 ASR 或翻译输入。
   - 如需辅助判断源语言，可用 `yt-dlp --list-subs 'https://www.youtube.com/watch?v=xxxxxxxxxxx'` 或精简 JSON 查看字幕轨道；如果源语言已能从标题、元数据、描述或音频语境可靠判断，可跳过字幕轨道检查。
   - `temp.md` 记录：视频链接、视频 ID、标题、时长、源语言、源语言判断依据、可用字幕轨道和备注。
   - 标题、时长等信息优先从 YouTube 元数据读取；暂时无法确定的字段先写 `待确认`，后续步骤确认后及时回填。
   - 判断出源语言后，在 `temp.md` 中显式设置，并按火山引擎 API 语言代码写入 `downloads/<video-id>/temp.md`。
   - 语言代码统一使用以下映射：`<source>` 为以下之一：中文普通话 `zh-CN`，英语 `en-US`，日语 `ja-JP`，韩语 `ko-KR`，葡萄牙语 `pt-BR`等。
   - 如果无法可靠判断，先向用户确认。
   - 使用 `yt-dlp` 下载 1080p `.mp4` 视频，尽量保持 MP4 容器，不重新编码；名称保持下载的默认名称，不要修改。
   - 如果同一次任务既需要 `.mp4` 视频又需要 `.m4a` 音频，优先使用一次 `yt-dlp` 下载并在合并时加 `-k` 或 `--keep-video`，确保合并前的 `.m4a` 分片被保留，作为后续 ASR 或其他音频处理的输入；`-k` 额外留下的无声视频分片（如 `.f399.mp4`）属于中间文件，不算最终交付产物，不要在最终回复或摘要的主产物列表中展示，并在流程结束前按当前仓库删除规则处理。
   - 下载视频封面，例如 `.webp`、`.jpg` 或 `.png`；名称保持下载的默认名称，不要修改。
   - 如果下载到的视频封面不是 `.jpg`，必须保留原封面文件不动，并额外复制一份 `.jpg` 封面副本；不要移动、重命名或覆盖原始封面。

2. **调用火山引擎 API**
   - 执行前必须先检查 `downloads/<video-id>/temp.md`。
   - 确认 `downloads/<video-id>/` 下存在 `.m4a` 音频文件；如果不存在，先回到第 1 步补足音频。
   - 确认 `temp.md` 中已经标记源语言；如果源语言仍为 `待确认` 或为空，先按第 1 步补足后再继续。
   - 输入：从 `downloads/<video-id>/` 中确认可用的单个 `.m4a` 音频文件路径。
   - 首次使用或触发 `本地配置` 时，必须先确认 `api_key_source`，但不要把真实密钥写进 `tools/api_volcengine_asr.py`；执行命令时用 `VOLC_API_KEY="<X-Api-Key>"` 或用户已配置的等价本地环境变量传入。
   - 必须使用 `uv` 执行 Python 脚本：`uv run ./tools/api_volcengine_asr.py`，使用新版 `X-Api-Key` + `volc.seedasr.auc`。
   - 使用 `uv` 时必须把缓存目录放在当前工作区内，避免沙盒环境无权限写入默认用户缓存目录；推荐设置：`UV_CACHE_DIR="./.uv-cache"`。
   - 火山引擎 ASR 是必需联网步骤；在当前沙盒环境中，直接调用经常会因网络限制出现 DNS 错误 `nodename nor servname provided, or not known`，这不是火山脚本问题。
   - 执行火山 ASR 时优先按权限流程使用 `require_escalated` 联网运行同一条 `uv run ./tools/api_volcengine_asr.py` 命令；如果已在当前会话批准对应 `uv run` 前缀，直接复用授权，避免先在沙盒内失败一次。
   - 如果火山 ASR 联网调用失败，只重试同一条命令并保持 `HARDCODED_AUDIO_FILE`、`HARDCODED_AUDIO_LANGUAGE`、`HARDCODED_OUTPUT_JSON`、`HARDCODED_OUTPUT_SRT` 不变；不要改脚本、不要改输入文件。
   - 每次处理具体视频时，必须显式传入以下任务参数，不能在脚本里写死固定文件路径或固定语言：`HARDCODED_AUDIO_FILE`、`HARDCODED_AUDIO_LANGUAGE`、`HARDCODED_OUTPUT_JSON`、`HARDCODED_OUTPUT_SRT`。
   - 必须从 `temp.md` 读取源语言，并设置 `HARDCODED_AUDIO_LANGUAGE`；音频文件路径来自当前任务目录下确认可用的 `.m4a` 文件。
   - 推荐调用方式：`VOLC_API_KEY="<X-Api-Key>" UV_CACHE_DIR="./.uv-cache" HARDCODED_AUDIO_FILE="<音频路径>" HARDCODED_AUDIO_LANGUAGE="<source>" HARDCODED_OUTPUT_JSON="<原音频文件名>.volc-asr-<source>.json" HARDCODED_OUTPUT_SRT="<原音频文件名>.volc-asr-<source>.srt" uv run ./tools/api_volcengine_asr.py`。
   - 脚本也支持使用命令行参数传入同样的信息，例如 `--file`、`--language`、`--output-json`、`--output-srt`。
   - 请求需开启 `show_utterances=true`，火山返回 `utterances` 时间戳后，本地转换为源语言 SRT。
   - ASR 阶段只转写源语言，不翻译；同时可保存完整 JSON 方便排查。
   - 输出：`<原音频文件名>.volc-asr-<source>.json` 与 `<原音频文件名>.volc-asr-<source>.srt`。

3. **翻译源ASR 字幕**
   - 输入：`<原音频文件名>.volc-asr-<source>.srt`
   - 由 AI 直接将源语言 SRT 逐条翻译成简体中文，只使用当前字幕块文本，不参考或复用已有中文字幕。
   - 翻译阶段不考虑本地翻译包；不得查找、安装或调用本地翻译包、离线翻译模型或项目内临时翻译脚本来生成译文。
   - 翻译结果必须直接写入最终中文字幕 `.srt`；除最终 `.srt` 外，不保留一次性翻译脚本或中间生成脚本。
   - 必须保留原 SRT 的编号、时间轴、空行结构，确保中文块与源字幕同编号一一对应。
   - 翻译时优先理解视频领域语境，而不是只做字面机翻或固定术语替换。
   - 只有源字幕内容支持时才写入领域术语，不要凭主题自动补词。
   - ASR 术语明显可疑但无法确定时，保守翻译；必要时保留原词或音译。
   - 自动清理 `<think>...</think>`、`<analysis>...</analysis>`、`<reasoning>...</reasoning>` 等内容。
   - 如果确实需要临时代码辅助校验编号、时间轴或块数，只能写在 `/private/tmp/`，或使用已安装 skill 目录中已有工具；不得写入项目目录的 `tools/`。
   - 写出中文字幕后，必须校验源 SRT 和中文 SRT 的块数一致，且每块编号和时间轴一致；发现不一致时必须修正中文 SRT 后重新校验。
   - 翻译会写入新的中文字幕 `.srt`；不要批量删除文件或目录。
   - 输出：`<原音频文件名>.volc-asr-<source>.srt -> <原音频文件名>.volc-asr-<source>-zh.srt`。

4. **烧制流程**
   - 输入：原视频 `.mp4`、中文字幕 `.srt`、源语言字幕 `.srt`、字体样式 `.json`。
   - 字体样式统一放在当前正在使用的 skill 根目录的 `fonts/` 下，默认使用 `fonts/subtitle_font_style_default.json`；执行 `tools/build_bilingual_ass.py --style-json` 前必须解析为当前 skill 目录中的绝对路径，不要按当前项目目录、视频输出目录或名字相似的副本目录解析。
   - 路径解析步骤：
     1. 以本 `SKILL.md` 所在目录作为 `<current-skill-dir>`。
     2. 将 `fonts/subtitle_font_style_default.json` 解析为 `<current-skill-dir>/fonts/subtitle_font_style_default.json`。
     3. 运行前检查该绝对路径存在；如果不存在，先检查当前 skill 是否安装完整或是否使用了错误的副本目录，不要要求用户从视频项目中提供 `fonts/模板`。
     4. 如果存在多个 `dafu-subs-skill*` 目录，优先使用当前被调用 skill 的目录；不要自动切换到 `dafu-subs-skill-1`、`dafu-subs-skill-2` 等名字相似目录。
   - 默认排版：双语都在底部，中文字幕在上，源语言字幕在下，优先使用事件级 `\pos(x,y)` 控制位置；不要只依赖固定 `MarginV`，因为字幕换行后高度会变化。
   - 源语言不固定，统一使用 `source` 样式，不写死 `japanese`、`english` 等字段名。
   - 网页颜色 `#RRGGBB` 写入 ASS 前必须转为 `&HAABBGGRR`，如 `#DBDBFD -> &H00FDDBDB`。
   - 先合成双语 `.ass`：源语言对白用 `Source`，中文字幕对白用 `Chinese`。
   - `.ass` 的 `[Script Info]` 必须写入与输入视频一致的 `PlayResX` 和 `PlayResY`，例如 1080p 视频写 `PlayResX: 1920`、`PlayResY: 1080`，避免 libass 默认按 `384x288` 缩放导致字幕异常放大。
   - ASS/libass 的自动换行不可靠，不能像 SRT 一样把长句交给播放器处理；中文、日文、韩文等无空格文本可能直接横向超出画面，源语言文本也可能因空格、标点、字体或渲染器差异表现不一致。
   - 合成 `.ass` 时必须主动控制长字幕换行，使用 ASS 换行符 `\N`，避免长句横向超出画面；换行后的实际行数必须用于后续 `1中 / 1源`、`1中 / 2源+`、`2中+ / 1源`、`2中+ / 2源+` 档位判断。
   - 中文和源语言都默认使用“基于宽度预估的主动换行”，不要再按固定字符数硬切。宽度预估应结合目标画布宽度、字体字号、描边和文本字符类型，为每种字幕样式设置可用最大宽度。
   - 中文字幕按估算显示宽度寻找断点：优先在句读标点、逗号顿号、空格等自然断点后换行；如果没有合适断点，再按字符序列保守断开，避免单个标点独占行首或过短尾巴单独成行。
   - 英文等拉丁源语言按“单词边界 + 宽度”换行，尽量避免把单词从中间切开；日文、韩文等源语言按“字符序列 + 宽度”换行，优先在标点或自然停顿处断开。
   - 默认双语间距按 1920x1080 画布调校；如果输入视频不是 1080p，必须按 `PlayResY / 1080` 等比换算以下 Y 坐标偏移，或重新截图确认后微调。
   - 默认采用四档事件级位置，按换行后的实际行数选择：
     - `1中 / 1源`：中文 `y = PlayResY - 52`，源语言 `y = PlayResY - 10`。
     - `2中+ / 1源`：中文 `y = PlayResY - 66`，源语言 `y = PlayResY - 14`。
     - `1中 / 2源+`：中文 `y = PlayResY - 78`，源语言 `y = PlayResY - 18`。
     - `2中+ / 2源+`：中文 `y = PlayResY - 92`，源语言 `y = PlayResY - 12`。
   - 以上换行与间距参数可作为游戏解说、主播口播类 1080p 视频的默认模板。对常规 1080p、默认字体样式、默认字号的任务，可直接完整烧制，不需要额外生成预览截图。
   - 只有当字幕样式、字体、字号、视频分辨率、画面安全区或源语言文字宽度明显变化，或实际成片出现遮挡、越界、行距异常时，才需要做临时视觉检查。
   - 临时视觉检查优先直接查看成片中的单帧或短片段，不要求固定生成 4 类预览截图；只有在需要定位特定排版问题时才按需抽帧。
   - 预览截图只用于临时排错，不作为最终产物保留。检查完成后不要在最终交付中列出预览截图；如确实生成了预览截图，结束前必须逐个明确文件路径向用户确认是否删除，或提示用户手动删除，不允许批量删除。
   - `.ass` 命名建议：`<basename>.bilingual.ass`；多配色可用 `<basename>.<style-name>.bilingual.ass`。
   - 硬烧使用 `ffmpeg -vf "ass=filename='<bilingual.ass>'" -c:v libx264 -preset medium -crf 22 -c:a copy`。
   - 当 `.ass` 文件路径包含空格、方括号、全角标点、emoji 或其他特殊字符时，必须使用 `ass=filename='<bilingual.ass>'`，不要直接写 `ass=<bilingual.ass>`，避免 ffmpeg 把路径中的特殊字符解析为滤镜参数并报 `Trailing garbage after a filter`。
   - 如果 `ass=filename='<bilingual.ass>'` 仍因长路径、特殊字符或滤镜解析问题失败，可将 `.ass` 复制到 `/private/tmp/` 下的简短临时文件名，再用该短路径硬烧；最终 `.ass` 和 `.mp4` 产物仍应保存在原任务目录，临时副本不作为最终产物展示。
   - 硬烧命令必须直接运行 `ffmpeg`，不要用 `/usr/bin/time -l` 包裹；该统计工具在沙盒中可能因读取系统统计失败而让已经成功生成的视频表现为退出码 1。
   - 判断硬烧是否成功以成品文件和 `ffprobe` 校验为准：检查输出文件存在、视频流、音频流、分辨率和时长。这样把“编码是否成功”和“统计工具是否失败”分开。
   - 烧制耗时和平均速度优先使用 `ffmpeg` 日志中的最终 `time=`、`speed=`，或用简单开始/结束时间记录。
   - 硬烧日志中如果出现 `Neither PlayResX nor PlayResY defined. Assuming 384x288`，必须停止并重新生成 `.ass` 后再烧制。
   - 输出命名建议：`<basename>.hardsub.mp4`；完成后检查文件存在、分辨率、时长和音频流。

5. **全流程总结**
   - 从用户给出视频链接开始计时，完成 1-4 全部流程后，按 `config/summary-template.md` 生成中文摘要文件。
   - 摘要需记录视频链接、下载产物、ASR 字幕、中文字幕、ASS 字幕、硬烧成品和最终状态。
   - 摘要需记录各阶段耗时、全流程总耗时、平均烧制速度和完成时间；不需要记录最高 CPU 占用或最高内存占用。
   - 摘要命名建议：`<basename>.summary.md`，并与硬烧成品放在同一目录。
   - 最终回复必须直接输出一份摘要内容，信息量至少覆盖 `config/summary-template.md` 中的全部字段；不要只给 `.summary.md` 文件链接。
   - 最终回复建议按“主产物链接 + 全流程摘要”组织；主产物只列正式交付文件，不列 `yt-dlp` 保留的分片文件或临时预览截图。
