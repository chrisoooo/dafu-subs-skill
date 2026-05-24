#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    index: str
    start: str
    end: str
    text: str


def parse_srt(path: Path) -> list[Cue]:
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    cues: list[Cue] = []
    for block in blocks:
        lines = [line.rstrip("\n") for line in block.splitlines()]
        if len(lines) < 3:
            continue
        index = lines[0].strip()
        timing = lines[1].strip()
        if " --> " not in timing:
            continue
        start, end = timing.split(" --> ", 1)
        text = " ".join(line.strip() for line in lines[2:])
        cues.append(Cue(index=index, start=srt_to_ass_time(start), end=srt_to_ass_time(end), text=text))
    return cues


def srt_to_ass_time(value: str) -> str:
    hours, minutes, rest = value.split(":", 2)
    seconds, millis = rest.split(",", 1)
    centis = int(round(int(millis) / 10))
    if centis == 100:
        centis = 99
    return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}.{centis:02d}"


def escape_ass(text: str) -> str:
    return text.replace("{", r"\{").replace("}", r"\}")


BREAK_AFTER_CHARS = set(
    " ,.;:!?)]}、。，．！？：；）】》〉」』〕］｝・/ー-"
)
TRIM_TRAILING_CHARS = set(" \t")


def contains_cjk(text: str) -> bool:
    return any(is_cjk_char(ch) for ch in text)


def is_cjk_char(ch: str) -> bool:
    codepoint = ord(ch)
    return (
        0x4E00 <= codepoint <= 0x9FFF
        or 0x3400 <= codepoint <= 0x4DBF
        or 0x3040 <= codepoint <= 0x309F
        or 0x30A0 <= codepoint <= 0x30FF
        or 0x31F0 <= codepoint <= 0x31FF
        or 0xAC00 <= codepoint <= 0xD7AF
    )


def estimate_char_width_em(ch: str) -> float:
    if ch.isspace():
        return 0.35
    if is_cjk_char(ch):
        return 1.0
    if ch.isdigit():
        return 0.62
    if "A" <= ch <= "Z":
        if ch in "MW":
            return 0.9
        if ch in "IJ":
            return 0.45
        return 0.72
    if "a" <= ch <= "z":
        if ch in "mw":
            return 0.82
        if ch in "il":
            return 0.32
        return 0.58
    if ch in ".,'`":
        return 0.28
    if ch in ":;|!":
        return 0.32
    if ch in "()[]{}<>":
        return 0.42
    if ch in "，。、！？：；（）【】《》「」『』":
        return 0.62
    if unicodedata.east_asian_width(ch) in {"F", "W"}:
        return 1.0
    return 0.65


def estimate_line_width(text: str, font_size: float, outline: float) -> float:
    text_width = sum(estimate_char_width_em(ch) for ch in text) * font_size
    # Outline grows on both sides of the rendered glyph run.
    return text_width + outline * 4


def detect_text_mode(text: str, prefer_cjk: bool) -> str:
    if prefer_cjk:
        return "cjk"
    if contains_cjk(text):
        return "cjk"
    if re.search(r"[A-Za-z]", text):
        return "latin"
    return "generic"


def trim_line_end(text: str) -> str:
    return text.rstrip("".join(TRIM_TRAILING_CHARS))


def split_cjk_units(text: str) -> list[str]:
    return list(text)


def wrap_cjk_text_lines(text: str, max_width: float, font_size: float, outline: float, max_lines: int = 2) -> list[str]:
    lines: list[str] = []
    current_units: list[str] = []
    last_break_index = -1
    units = split_cjk_units(text)
    while units:
        unit = units.pop(0)
        current_units.append(unit)
        if unit.isspace() or unit in BREAK_AFTER_CHARS:
            last_break_index = len(current_units)
        current_text = "".join(current_units)
        if estimate_line_width(current_text, font_size, outline) <= max_width:
            continue
        if len(lines) + 1 >= max_lines:
            current_units.extend(units)
            units = []
            break
        if 0 < last_break_index <= len(current_units):
            line = trim_line_end("".join(current_units[:last_break_index]))
            remainder = "".join(current_units[last_break_index:]).lstrip()
            lines.append(line)
            current_units = split_cjk_units(remainder)
        else:
            line = trim_line_end("".join(current_units[:-1]))
            if not line:
                line = current_text
                current_units = []
            else:
                current_units = [current_units[-1]]
            lines.append(line)
        last_break_index = -1
        for idx, current_unit in enumerate(current_units, start=1):
            if current_unit.isspace() or current_unit in BREAK_AFTER_CHARS:
                last_break_index = idx
    if current_units:
        lines.append(trim_line_end("".join(current_units)))
    return lines


def event_text(lines: list[str], x: int, y: int) -> str:
    prefix = rf"{{\pos({x},{y})}}"
    return prefix + r"\N".join(escape_ass(line) for line in lines)


def wrap_latin_text_lines(text: str, max_width: float, font_size: float, outline: float, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for index, word in enumerate(words[1:], start=1):
        candidate = f"{current} {word}"
        if estimate_line_width(candidate, font_size, outline) <= max_width:
            current = candidate
            continue
        lines.append(current)
        if len(lines) + 1 >= max_lines:
            current = " ".join(words[index:])
            break
        current = word
    lines.append(current)
    return lines


def wrap_generic_text_lines(text: str, max_width: float, font_size: float, outline: float, max_lines: int = 2) -> list[str]:
    if estimate_line_width(text, font_size, outline) <= max_width:
        return [text]
    return wrap_cjk_text_lines(text, max_width, font_size, outline, max_lines=max_lines)


def compute_max_width(play_res_x: int, style_name: str) -> float:
    scale = play_res_x / 1920
    if style_name.lower() == "chinese":
        return 1520 * scale
    return 1560 * scale


def wrap_text_lines(text: str, style_spec: dict, play_res_x: int, prefer_cjk: bool, max_lines: int = 2) -> list[str]:
    style = style_spec["style"]
    font_size = float(style["FontSize"])
    outline = float(style.get("Outline", 0))
    max_width = compute_max_width(play_res_x, style_spec.get("name", ""))
    mode = detect_text_mode(text, prefer_cjk)
    if mode == "latin":
        return wrap_latin_text_lines(text, max_width, font_size, outline, max_lines=max_lines)
    if mode == "cjk":
        return wrap_cjk_text_lines(text, max_width, font_size, outline, max_lines=max_lines)
    return wrap_generic_text_lines(text, max_width, font_size, outline, max_lines=max_lines)


def style_line(name: str, spec: dict) -> str:
    style = spec["style"]
    pos = spec["position"]
    return (
        f"Style: {name},{style['Fontname']},{style['FontSize']},"
        f"{style['PrimaryColour']},{style['PrimaryColour']},{style['OutlineColour']},{style['OutlineColour']},"
        f"{int(bool(style.get('Bold', 0)))*-1},0,0,0,100,100,0,0,"
        f"{style['BorderStyle']},{style['Outline']},{style['Shadow']},{pos['Alignment']},"
        f"{pos['MarginL']},{pos['MarginR']},{pos['MarginV']},1"
    )


def build_ass(
    chinese: list[Cue],
    source: list[Cue],
    styles: dict,
    play_res_x: int,
    play_res_y: int,
) -> str:
    if len(chinese) != len(source):
        raise SystemExit(f"SRT block count mismatch: chinese={len(chinese)} source={len(source)}")
    for zh, src in zip(chinese, source):
        if zh.index != src.index or zh.start != src.start or zh.end != src.end:
            raise SystemExit(f"SRT alignment mismatch at block {zh.index}")

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {play_res_x}",
        f"PlayResY: {play_res_y}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.601",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding",
        style_line("Chinese", styles["chinese"]),
        style_line("Source", styles["source"]),
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]

    chinese_style = dict(styles["chinese"])
    chinese_style["name"] = "Chinese"
    source_style = dict(styles["source"])
    source_style["name"] = "Source"

    events: list[str] = []
    center_x = play_res_x // 2
    # Tightest spacing when both subtitle tracks stay on one line.
    single_chinese_y = play_res_y - 52
    single_source_y = play_res_y - 10
    # Separate tuning for mixed-height pairs.
    zh_double_src_single_chinese_y = play_res_y - 66
    zh_double_src_single_source_y = play_res_y - 14
    zh_single_src_double_chinese_y = play_res_y - 78
    zh_single_src_double_source_y = play_res_y - 18
    # Slightly tighter spacing when both subtitle tracks occupy multiple lines.
    double_chinese_y = play_res_y - 92
    double_source_y = play_res_y - 12

    for zh, src in zip(chinese, source):
        zh_lines = wrap_text_lines(zh.text, chinese_style, play_res_x, prefer_cjk=True)
        src_lines = wrap_text_lines(src.text, source_style, play_res_x, prefer_cjk=False)
        zh_multiline = len(zh_lines) >= 2
        src_multiline = len(src_lines) >= 2
        if zh_multiline and src_multiline:
            chinese_y = double_chinese_y
            source_y = double_source_y
        elif zh_multiline:
            chinese_y = zh_double_src_single_chinese_y
            source_y = zh_double_src_single_source_y
        elif src_multiline:
            chinese_y = zh_single_src_double_chinese_y
            source_y = zh_single_src_double_source_y
        else:
            chinese_y = single_chinese_y
            source_y = single_source_y
        events.append(f"Dialogue: 0,{zh.start},{zh.end},Chinese,,0,0,0,,{event_text(zh_lines, center_x, chinese_y)}")
        events.append(f"Dialogue: 0,{src.start},{src.end},Source,,0,0,0,,{event_text(src_lines, center_x, source_y)}")
    return "\n".join(header + events) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bilingual ASS from aligned source/chinese SRT files.")
    parser.add_argument("--source-srt", required=True)
    parser.add_argument("--chinese-srt", required=True)
    parser.add_argument("--style-json", required=True)
    parser.add_argument("--output-ass", required=True)
    parser.add_argument("--play-res-x", type=int, default=1920)
    parser.add_argument("--play-res-y", type=int, default=1080)
    # Legacy compatibility flags. Width-based wrapping now drives the layout.
    parser.add_argument("--chinese-wrap", type=int, default=36)
    parser.add_argument("--source-wrap", type=int, default=130)
    args = parser.parse_args()

    source_path = Path(args.source_srt).expanduser()
    chinese_path = Path(args.chinese_srt).expanduser()
    style_path = Path(args.style_json).expanduser()
    output_path = Path(args.output_ass).expanduser()

    source = parse_srt(source_path)
    chinese = parse_srt(chinese_path)
    styles = json.loads(style_path.read_text(encoding="utf-8"))
    ass_text = build_ass(
        chinese,
        source,
        styles,
        args.play_res_x,
        args.play_res_y,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ass_text, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
