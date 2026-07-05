#!/usr/bin/env python3
"""Play a video as a terminal ASCII animation.

Only Python's standard library is used. FFmpeg is used for video decoding.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


LIGHT_TO_DARK = (
    " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a video as high-detail ASCII animation in the terminal."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input video path, e.g. ./video.mp4.",
    )
    parser.add_argument(
        "--cols",
        "--width",
        dest="cols",
        type=int,
        default=0,
        help="ASCII width in characters. Defaults to current terminal width.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=24,
        help="Playback FPS. Lower this if the terminal lags.",
    )
    parser.add_argument(
        "--aspect",
        type=float,
        default=None,
        help="Terminal character aspect correction. Defaults to 0.42.",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=1.25,
        help="Center zoom before rendering. Increase if the cat looks too small.",
    )
    parser.add_argument(
        "--y-shift",
        type=float,
        default=-0.16,
        help="Vertical crop shift. Negative values keep more top/ear space.",
    )
    parser.add_argument(
        "--contrast",
        type=float,
        default=2.65,
        help="ASCII density boost for non-white pixels.",
    )
    parser.add_argument(
        "--brightness",
        type=int,
        default=0,
        help="Brightness offset from -255 to 255 before character mapping.",
    )
    parser.add_argument(
        "--palette",
        default=LIGHT_TO_DARK,
        help="Characters ordered from lightest to darkest.",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=0.62,
        help="Lower values make faint fur details use stronger characters.",
    )
    parser.add_argument(
        "--edge-weight",
        type=float,
        default=1.25,
        help="How strongly local edges are preserved in the ASCII output.",
    )
    parser.add_argument(
        "--white-cutoff",
        type=int,
        default=245,
        help="Pixels brighter than this are treated as background unless they form an edge.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop the animation until Ctrl+C.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Debug option: stop after this many frames.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(message)


def winget_tool_candidates(name: str) -> list[Path]:
    if os.name != "nt":
        return []

    exe = f"{name}.exe"
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        local_app_data / "Microsoft" / "WinGet" / "Links" / exe,
        Path(r"C:\ffmpeg\bin") / exe,
        Path(r"C:\Program Files\ffmpeg\bin") / exe,
        Path(r"C:\Program Files\Gyan\FFmpeg\bin") / exe,
    ]

    packages = local_app_data / "Microsoft" / "WinGet" / "Packages"
    if packages.exists():
        for package_dir in packages.glob("Gyan.FFmpeg*"):
            candidates.extend(
                path for path in package_dir.rglob(exe) if path.parent.name.lower() == "bin"
            )

    return candidates


def resolve_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found

    for candidate in winget_tool_candidates(name):
        if candidate.exists():
            return str(candidate)

    fail(
        f"Missing required command: {name}\n"
        "Install FFmpeg in Windows PowerShell:\n"
        "  winget install --id Gyan.FFmpeg -e --source winget\n"
        "Then close and reopen VSCode, or open a new PowerShell terminal.\n"
        "Verify with:\n"
        "  ffmpeg -version\n"
        "Run again with:\n"
        "  python .\\ascii_cat.py"
    )


def ffprobe_size(path: Path, ffprobe: str) -> tuple[int, int]:
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def auto_columns(requested: int, src_w: int, src_h: int, aspect: float) -> int:
    terminal = shutil.get_terminal_size(fallback=(120, 40))
    if requested > 0:
        return max(20, requested)

    max_cols_by_width = max(20, terminal.columns - 1)
    usable_lines = max(10, terminal.lines - 4)
    max_cols_by_height = max(20, round(usable_lines / ((src_h / src_w) * aspect)))
    return min(max_cols_by_width, max_cols_by_height)


def corrected_rows(cols: int, src_w: int, src_h: int, aspect: float) -> int:
    return max(1, round(cols * (src_h / src_w) * aspect))


def crop_filter(src_w: int, src_h: int, zoom: float, y_shift: float) -> str | None:
    if zoom <= 1.0:
        return None
    crop_w = max(2, round(src_w / zoom))
    crop_h = max(2, round(src_h / zoom))
    crop_x = max(0, (src_w - crop_w) // 2)
    spare_y = src_h - crop_h
    crop_y = round((spare_y / 2) + (spare_y * y_shift))
    crop_y = max(0, min(spare_y, crop_y))
    return f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"


def stream_frames(
    input_path: Path,
    cols: int,
    rows: int,
    fps: float,
    ffmpeg: str,
    crop: str | None,
) -> subprocess.Popen[bytes]:
    filters = [f"fps={fps}"]
    if crop:
        filters.append(crop)
    filters.append(f"scale={cols}:{rows}:flags=lanczos")
    filters.append("format=gray")
    command = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(input_path),
        "-vf",
        ",".join(filters),
        "-an",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def enable_windows_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        console_mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(console_mode)):
            kernel32.SetConsoleMode(handle, console_mode.value | 0x0004)
    except Exception:
        pass


def render_frame(
    raw: bytes,
    cols: int,
    rows: int,
    palette: str,
    *,
    contrast: float,
    brightness: int,
    gamma: float,
    edge_weight: float,
    white_cutoff: int,
) -> str:
    palette_max = len(palette) - 1
    lines = []
    for y in range(rows):
        chars = []
        row_offset = y * cols
        for x in range(cols):
            index = row_offset + x
            value = max(0, min(255, raw[index] + brightness))

            # Most of the source video is white background. Treat it as empty
            # space, but preserve real contour changes near the cat.
            darkness = 0.0 if value >= white_cutoff else (255 - value) / 255
            density = min(1.0, darkness * contrast)
            density = density**gamma if density > 0 else 0.0

            right = raw[index + 1] if x + 1 < cols else raw[index]
            down = raw[index + cols] if y + 1 < rows else raw[index]
            edge = (abs(raw[index] - right) + abs(raw[index] - down)) / 255
            edge = min(1.0, edge * edge_weight)
            if value >= white_cutoff and edge < 0.18:
                edge = 0.0

            score = max(density, edge)
            chars.append(" " if score < 0.035 else palette[round(score * palette_max)])
        lines.append("".join(chars))
    return "\n".join(lines)


def play_once(
    args: argparse.Namespace,
    cols: int,
    rows: int,
    palette: str,
    ffmpeg: str,
    crop: str | None,
) -> int:
    frame_size = cols * rows
    proc = stream_frames(args.input, cols, rows, args.fps, ffmpeg, crop)
    assert proc.stdout is not None

    frame_count = 0
    next_frame_at = time.perf_counter()
    frame_delay = 1 / args.fps

    while True:
        raw = proc.stdout.read(frame_size)
        if not raw:
            break
        if len(raw) != frame_size:
            stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
            fail(f"FFmpeg returned a partial frame.\n{stderr}")

        sys.stdout.write("\x1b[H")
        sys.stdout.write(
            render_frame(
                raw,
                cols,
                rows,
                palette,
                contrast=args.contrast,
                brightness=args.brightness,
                gamma=args.gamma,
                edge_weight=args.edge_weight,
                white_cutoff=args.white_cutoff,
            )
        )
        sys.stdout.write("\n")
        sys.stdout.flush()

        frame_count += 1
        if args.max_frames and frame_count >= args.max_frames:
            proc.kill()
            break

        next_frame_at += frame_delay
        sleep_for = next_frame_at - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)

    _, stderr_bytes = proc.communicate()
    if proc.returncode not in (0, None) and not args.max_frames:
        fail(stderr_bytes.decode("utf-8", errors="replace"))
    return frame_count


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        fail(f"Input video does not exist: {args.input}")
    if args.fps <= 0:
        fail("--fps must be greater than 0")
    aspect = args.aspect
    if aspect is None:
        aspect = 0.42
    if aspect <= 0:
        fail("--aspect must be greater than 0")
    if args.zoom <= 0:
        fail("--zoom must be greater than 0")
    if args.gamma <= 0:
        fail("--gamma must be greater than 0")
    if args.edge_weight < 0:
        fail("--edge-weight must be zero or greater")
    if not 0 <= args.white_cutoff <= 255:
        fail("--white-cutoff must be between 0 and 255")
    if len(args.palette) < 2:
        fail("--palette must contain at least 2 characters")

    ffmpeg = resolve_tool("ffmpeg")
    ffprobe = resolve_tool("ffprobe")
    enable_windows_ansi()

    src_w, src_h = ffprobe_size(args.input, ffprobe)
    cols = auto_columns(args.cols, src_w, src_h, aspect)
    rows = corrected_rows(cols, src_w, src_h, aspect)
    crop = crop_filter(src_w, src_h, args.zoom, args.y_shift)

    print(
        f"Playing {args.input} as pure ASCII: source={src_w}x{src_h}, "
        f"render={cols}x{rows}, fps={args.fps}, zoom={args.zoom}. Ctrl+C to stop."
    )
    time.sleep(0.8)

    sys.stdout.write("\x1b[2J\x1b[?25l")
    sys.stdout.flush()
    total_frames = 0
    try:
        while True:
            total_frames += play_once(args, cols, rows, args.palette, ffmpeg, crop)
            if not args.loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[?25h\x1b[0m\n")
        sys.stdout.flush()

    print(f"Done. Rendered {total_frames} frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
