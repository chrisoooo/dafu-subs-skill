#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import error, request

# 火山引擎语音中文文档，https://www.volcengine.com/docs/6561/1354868?lang=zh

SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
SUCCESS_CODE = 20000000
RUNNING_CODES = {20000001, 20000002}
DEFAULT_RESOURCE_ID = "volc.seedasr.auc"

# Keep this empty in public repositories. Pass secrets with VOLC_API_KEY instead.
# HARDCODED_API_KEY remains as a local fallback for private, uncommitted edits only.
HARDCODED_API_KEY = ""
HARDCODED_APP_KEY = ""
HARDCODED_ACCESS_KEY = ""
HARDCODED_RESOURCE_ID = DEFAULT_RESOURCE_ID
HARDCODED_AUDIO_URL = ""
HARDCODED_AUDIO_FILE = ""
HARDCODED_AUDIO_FORMAT = "m4a"
HARDCODED_AUDIO_LANGUAGE = ""
HARDCODED_OUTPUT_JSON = ""
HARDCODED_OUTPUT_SRT = ""


def read_runtime_value(name: str, fallback: str = "") -> str:
    return (os.getenv(name) or fallback).strip()


def default_output_paths(audio_file: Path | None, language: str = "") -> tuple[str, str]:
    if audio_file is None:
        return "", ""
    base_name = audio_file.name
    source = language.strip() or "source"
    return (
        str(audio_file.with_name(f"{base_name}.volc-asr-{source}.json")),
        str(audio_file.with_name(f"{base_name}.volc-asr-{source}.srt")),
    )

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="调用火山引擎音频识别标准版 API，提交音频 URL 并轮询结果。"
    )
    parser.add_argument(
        "--url",
        default=read_runtime_value("HARDCODED_AUDIO_URL", HARDCODED_AUDIO_URL),
        help="公网可访问的音频 URL，也可通过 HARDCODED_AUDIO_URL 传入",
    )
    parser.add_argument(
        "--file",
        default=read_runtime_value("HARDCODED_AUDIO_FILE", HARDCODED_AUDIO_FILE),
        help="本地音频文件路径，设置后优先于 --url，也可通过 HARDCODED_AUDIO_FILE 传入",
    )
    parser.add_argument(
        "--format",
        default=read_runtime_value("HARDCODED_AUDIO_FORMAT", HARDCODED_AUDIO_FORMAT),
        choices=["mp3", "wav", "ogg", "raw", "m4a"],
    )
    parser.add_argument(
        "--language",
        default=read_runtime_value("HARDCODED_AUDIO_LANGUAGE", HARDCODED_AUDIO_LANGUAGE),
        help="显式指定识别语言，如 ja-JP、en-US，也可通过 HARDCODED_AUDIO_LANGUAGE 传入",
    )
    parser.add_argument("--uid", help="请求中的 user.uid，默认取 VOLC_UID 或 VOLC_APP_KEY")
    parser.add_argument("--resource-id", default=os.getenv("VOLC_RESOURCE_ID", HARDCODED_RESOURCE_ID))
    parser.add_argument("--poll-interval", type=float, default=5.0, help="轮询间隔，单位秒")
    parser.add_argument("--timeout", type=float, default=600.0, help="总超时时间，单位秒")
    parser.add_argument(
        "--output-json",
        default=read_runtime_value("HARDCODED_OUTPUT_JSON", HARDCODED_OUTPUT_JSON),
        help="可选：保存完整响应 JSON 的路径，也可通过 HARDCODED_OUTPUT_JSON 传入",
    )
    parser.add_argument(
        "--output-srt",
        default=read_runtime_value("HARDCODED_OUTPUT_SRT", HARDCODED_OUTPUT_SRT),
        help="可选：根据 utterances 保存 SRT 字幕，也可通过 HARDCODED_OUTPUT_SRT 传入",
    )
    parser.add_argument("--disable-itn", action="store_true", help="关闭数字/日期规范化")
    parser.add_argument("--disable-punc", action="store_true", help="关闭标点恢复")
    parser.add_argument("--hide-utterances", action="store_true", help="不请求 utterances 详情")
    return parser.parse_args()


def read_config(name: str, fallback: str = "") -> str:
    value = (os.getenv(name) or fallback).strip()
    if not value:
        raise SystemExit(f"Missing required config: {name}")
    if value.startswith("你的_"):
        raise SystemExit(f"Please fill {name} in the script or export it as an environment variable")
    return value


def read_optional_config(name: str, fallback: str = "") -> str:
    value = (os.getenv(name) or fallback).strip()
    if value.startswith("你的_"):
        return ""
    return value


def read_text_config(label: str, value: str) -> str:
    text = value.strip()
    if not text:
        raise SystemExit(f"Missing required config: {label}")
    if "example.com/your-audio.mp3" in text:
        raise SystemExit(f"Please fill {label} in the script or pass it on the command line")
    return text


def read_optional_file_path(value: str) -> Path | None:
    text = value.strip()
    if not text:
        return None
    if "*" in text:
        raise SystemExit("Please provide a single explicit audio file path, not a wildcard path")
    path = Path(text).expanduser()
    if not path.is_file():
        raise SystemExit(f"Local audio file not found: {path}")
    return path


def read_header(headers: Any, name: str) -> str:
    value = headers.get(name)
    return value.strip() if isinstance(value, str) else ""


def build_headers(
    resource_id: str,
    request_id: str,
    api_key: str = "",
    app_key: str = "",
    access_key: str = "",
) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }
    if api_key:
        headers["X-Api-Key"] = api_key
    else:
        headers["X-Api-App-Key"] = app_key
        headers["X-Api-Access-Key"] = access_key
    return headers


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            meta = {
                "http_status": str(resp.status),
                "logid": read_header(resp.headers, "X-Tt-Logid"),
                "status_code": read_header(resp.headers, "X-Api-Status-Code"),
                "message": read_header(resp.headers, "X-Api-Message"),
            }
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} calling {url}\n{body}") from exc
    except error.URLError as exc:
        raise SystemExit(f"Network error calling {url}: {exc}") from exc

    if not body.strip():
        return {}, meta
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from {url}: {body}") from exc
    return parsed, meta


def build_submit_payload(args: argparse.Namespace, uid: str) -> dict[str, Any]:
    audio_data: dict[str, Any] = {"format": args.format}
    if args.language:
        audio_data["language"] = args.language
    if args.file_path is not None:
        audio_data["data"] = base64.b64encode(args.file_path.read_bytes()).decode("ascii")
    else:
        audio_data["url"] = args.url

    return {
        "user": {"uid": uid},
        "audio": audio_data,
        "request": {
            "model_name": "bigmodel",
            "enable_itn": not args.disable_itn,
            "enable_punc": not args.disable_punc,
            "enable_ddc": False,
            "enable_speaker_info": False,
            "enable_channel_split": False,
            "show_utterances": not args.hide_utterances,
            "vad_segment": False,
            "sensitive_words_filter": "",
        },
    }


def build_query_payload(uid: str) -> dict[str, Any]:
    return {}


def extract_code(response: dict[str, Any]) -> int | None:
    code = response.get("code")
    return code if isinstance(code, int) else None


def parse_status_code(meta: dict[str, str]) -> int | None:
    value = meta.get("status_code", "")
    return int(value) if value.isdigit() else None


def save_json(path_text: str, payload: dict[str, Any]) -> Path:
    path = Path(path_text).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def format_srt_time(value: Any) -> str:
    ms = max(0, int(round(float(value))))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def pick_first(item: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = item.get(name)
        if value is not None:
            return value
    return None


def save_srt(path_text: str, response: dict[str, Any]) -> Path:
    result = response.get("result") or {}
    utterances = result.get("utterances") or []
    if not utterances:
        raise SystemExit("No utterances found in response; cannot write SRT")

    path = Path(path_text).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        line_no = 1
        for item in utterances:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            start = pick_first(item, ("start_time", "start", "start_ms"))
            end = pick_first(item, ("end_time", "end", "end_ms"))
            if not text or start is None or end is None:
                continue
            f.write(f"{line_no}\n")
            f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
            f.write(f"{text}\n\n")
            line_no += 1

    return path


def main() -> None:
    args = parse_args()
    api_key = read_optional_config("VOLC_API_KEY", HARDCODED_API_KEY)
    app_key = read_optional_config("VOLC_APP_KEY", HARDCODED_APP_KEY)
    access_key = read_optional_config("VOLC_ACCESS_KEY", HARDCODED_ACCESS_KEY)
    resource_id = read_config("VOLC_RESOURCE_ID", args.resource_id)
    args.file_path = read_optional_file_path(args.file)
    if args.file_path is None:
        args.url = read_text_config("HARDCODED_AUDIO_URL", args.url)
    else:
        default_json, default_srt = default_output_paths(args.file_path, args.language)
        args.output_json = (args.output_json or default_json).strip()
        args.output_srt = (args.output_srt or default_srt).strip()
    if not api_key and (not app_key or not access_key):
        raise SystemExit("Please fill VOLC_API_KEY or both VOLC_APP_KEY and VOLC_ACCESS_KEY")

    uid_seed = api_key or app_key
    uid = (args.uid or os.getenv("VOLC_UID") or uid_seed).strip()
    request_id = str(uuid.uuid4())
    headers = build_headers(
        resource_id=resource_id,
        request_id=request_id,
        api_key=api_key,
        app_key=app_key,
        access_key=access_key,
    )

    submit_payload = build_submit_payload(args, uid)
    submit_response, submit_meta = post_json(SUBMIT_URL, headers, submit_payload)
    submit_code = parse_status_code(submit_meta)

    print(f"REQUEST_ID={request_id}")
    if submit_meta.get("logid"):
        print(f"SUBMIT_LOGID={submit_meta['logid']}")
        headers["X-Tt-Logid"] = submit_meta["logid"]
    print(f"SUBMIT_CODE={submit_code}")
    print(f"SUBMIT_MESSAGE={submit_meta.get('message')}")

    if submit_code not in (SUCCESS_CODE, None):
        if args.output_json:
            output_path = save_json(args.output_json, submit_response)
            print(f"OUTPUT_JSON={output_path}")
        raise SystemExit(1)

    deadline = time.monotonic() + args.timeout
    query_payload = build_query_payload(uid)
    last_response = submit_response

    while time.monotonic() < deadline:
        time.sleep(args.poll_interval)
        query_response, query_meta = post_json(QUERY_URL, headers, query_payload)
        last_response = query_response
        query_code = parse_status_code(query_meta) or extract_code(query_response)

        if query_meta.get("logid"):
            print(f"QUERY_LOGID={query_meta['logid']}")
        print(f"QUERY_CODE={query_code}")
        print(f"QUERY_MESSAGE={query_meta.get('message') or query_response.get('message')}")

        result = query_response.get("result") or {}
        if result.get("text") and query_code in (SUCCESS_CODE, None):
            text = result.get("text") or ""
            print("RESULT_TEXT_BEGIN")
            print(text)
            print("RESULT_TEXT_END")
            if args.output_json:
                output_path = save_json(args.output_json, query_response)
                print(f"OUTPUT_JSON={output_path}")
            if args.output_srt:
                srt_path = save_srt(args.output_srt, query_response)
                print(f"OUTPUT_SRT={srt_path}")
            return

        if query_code is None and not result:
            continue

        if query_code not in RUNNING_CODES:
            if args.output_json:
                output_path = save_json(args.output_json, query_response)
                print(f"OUTPUT_JSON={output_path}")
            raise SystemExit(1)

    if args.output_json:
        output_path = save_json(args.output_json, last_response)
        print(f"OUTPUT_JSON={output_path}")
    raise SystemExit("Timed out waiting for ASR result")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Interrupted by user")
