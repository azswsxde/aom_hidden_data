from pathlib import Path
import subprocess
import csv
import sys


ROOT = Path(r"D:\碩士實驗\testdata")
FFMPEG = "ffmpeg"

LOG_CSV = ROOT / "ffmpeg_decode_log.csv"

SKIP_DIRS = {
    "difference_map",
    "__pycache__",
}


def find_avif_files():
    results = []

    for avif_path in ROOT.rglob("*.avif"):
        relative = avif_path.relative_to(ROOT)

        if any(part in SKIP_DIRS for part in relative.parts):
            continue

        results.append(avif_path)

    return sorted(results)


def make_output_path(avif_path):
    # xxx.avif -> xxx.yuv
    return avif_path.with_suffix(".yuv")


def decode_avif(avif_path, yuv_path):

    command = [
        FFMPEG,
        "-hide_banner",
        "-loglevel", "error",

        # 強制覆蓋
        "-y",

        "-i", str(avif_path),

        # raw 8-bit YUV420
        "-pix_fmt", "yuv420p",
        "-f", "rawvideo",

        str(yuv_path),
    ]

    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main():

    print("=" * 80)
    print("AVIF -> YUV420p FFmpeg batch decode")
    print("WARNING: existing .yuv files will be overwritten")
    print("=" * 80)
    print()

    try:
        subprocess.run(
            [FFMPEG, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[ERROR] 找不到 FFmpeg")
        print("請確認 ffmpeg 已加入 PATH")
        sys.exit(1)

    avif_files = find_avif_files()

    print(f"找到 {len(avif_files)} 個 AVIF")
    print()

    rows = []

    success = 0
    failed = 0

    for i, avif_path in enumerate(avif_files, start=1):

        yuv_path = make_output_path(avif_path)

        print("-" * 80)
        print(f"[{i}/{len(avif_files)}]")
        print(f"AVIF : {avif_path}")
        print(f"YUV  : {yuv_path}")

        result = decode_avif(
            avif_path,
            yuv_path
        )

        if result.returncode == 0 and yuv_path.exists():

            success += 1

            print(
                f"[OK] {yuv_path.stat().st_size:,} bytes"
            )

            rows.append({
                "avif_file": str(avif_path),
                "yuv_file": str(yuv_path),
                "status": "OK",
                "avif_size": avif_path.stat().st_size,
                "yuv_size": yuv_path.stat().st_size,
                "error": "",
            })

        else:

            failed += 1

            print("[FAILED]")
            print(result.stderr)

            rows.append({
                "avif_file": str(avif_path),
                "yuv_file": str(yuv_path),
                "status": "FAILED",
                "avif_size": (
                    avif_path.stat().st_size
                    if avif_path.exists()
                    else ""
                ),
                "yuv_size": (
                    yuv_path.stat().st_size
                    if yuv_path.exists()
                    else ""
                ),
                "error": result.stderr.strip(),
            })

    # --------------------------------------------------------
    # log
    # --------------------------------------------------------

    with open(
        LOG_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "avif_file",
                "yuv_file",
                "status",
                "avif_size",
                "yuv_size",
                "error",
            ]
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 80)
    print("完成")
    print("=" * 80)
    print(f"成功 : {success}")
    print(f"失敗 : {failed}")
    print(f"Log  : {LOG_CSV}")


if __name__ == "__main__":
    main()