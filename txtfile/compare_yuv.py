from pathlib import Path
import csv
import math
import re
import numpy as np


# ============================================================
# 根目錄
# ============================================================

ROOT = Path(r"D:\碩士實驗\testdata")

# Clean AV1 decode YUV
CLEAN_ROOT = ROOT / "ori_video"

# 輸出
OUTPUT_CSV = ROOT / "yuv_compare_all.csv"


# ============================================================
# 哪些資料夾不是 Steg 實驗
# ============================================================

SKIP_DIRS = {
    "ori_video",
    "original_decode",
    "ffmpeg_decode",
    "difference_map",
    "__pycache__",
}


# ============================================================
# Source YUV 與影片規格
# ============================================================

VIDEO_INFO = {

    "Fallout4": {
        "aliases": [
            "fallout4",
        ],
        "source": ROOT / "Fallout4_1080p.yuv",
        "width": 1920,
        "height": 1080,
        "fps": 60,
    },

    "FourPeople": {
        "aliases": [
            "fourpeople",
            "four_people",
        ],
        "source": ROOT / "FourPeople_720p_60.yuv",
        "width": 1280,
        "height": 720,
        "fps": 60,
    },

    "Johnny": {
        "aliases": [
            "johnny",
        ],
        "source": ROOT / "Johnny_720p_60.yuv",
        "width": 1280,
        "height": 720,
        "fps": 60,
    },

    "KristenAndSara": {
        "aliases": [
            "kristenandsara",
            "kristen_and_sara",
            "kristen",
        ],
        "source": ROOT / "KristenAndSara_720p_60.yuv",
        "width": 1280,
        "height": 720,
        "fps": 60,
    },

    "SpeedBag": {
        "aliases": [
            "speed_bag",
            "speedbag",
        ],
        "source": ROOT / "speed_bag_1080p.yuv",
        "width": 1920,
        "height": 1080,
        "fps": 30,
    },
}


# ============================================================
# High / Middle / Low 對應實際 bitrate
#
# 按照你目前的實驗規劃：
#
# 1080p:
# High   = 8000
# Middle = 5000
# Low    = 1200
#
# 720p:
# High   = 5000
# Middle = 2500
# Low    = 1200
# ============================================================

BITRATE_TABLE = {

    1080: {
        "High": 8000,
        "Middle": 5000,
        "Low": 1200,
    },

    720: {
        "High": 5000,
        "Middle": 2500,
        "Low": 1200,
    },
}


# ============================================================
# 名稱解析
# ============================================================

def normalize(text):
    return str(text).lower().replace("-", "_").replace(" ", "_")


def detect_video(path):
    """
    從完整 path 判斷是哪一部影片。
    """

    text = normalize(path)

    for video_name, info in VIDEO_INFO.items():

        for alias in info["aliases"]:

            if alias.lower() in text:
                return video_name

    return None


def detect_quality(path):
    """
    判斷 High / Middle / Low。
    """

    text = normalize(path)

    if re.search(r"(^|_)high($|_)", text):
        return "High"

    if re.search(r"(^|_)middle($|_)", text):
        return "Middle"

    if re.search(r"(^|_)low($|_)", text):
        return "Low"

    return None


def quality_to_bitrate(video_name, quality):

    if video_name is None or quality is None:
        return None

    height = VIDEO_INFO[video_name]["height"]

    table = BITRATE_TABLE.get(height)

    if table is None:
        return None

    return table.get(quality)


# ============================================================
# YUV420p 8-bit
# ============================================================

def get_yuv_info(width, height):

    y_size = width * height

    uv_width = width // 2
    uv_height = height // 2

    uv_size = uv_width * uv_height

    frame_size = y_size + uv_size * 2

    return {
        "Y_SIZE": y_size,
        "UV_SIZE": uv_size,
        "FRAME_SIZE": frame_size,
    }


def get_frame_count(path, width, height):

    info = get_yuv_info(width, height)

    file_size = path.stat().st_size
    frame_size = info["FRAME_SIZE"]

    frames = file_size // frame_size
    remainder = file_size % frame_size

    return frames, remainder


def read_frame(f, width, height):

    info = get_yuv_info(width, height)

    y_size = info["Y_SIZE"]
    uv_size = info["UV_SIZE"]

    y_raw = f.read(y_size)

    if len(y_raw) != y_size:
        return None

    u_raw = f.read(uv_size)
    v_raw = f.read(uv_size)

    if len(u_raw) != uv_size:
        return None

    if len(v_raw) != uv_size:
        return None

    y = np.frombuffer(
        y_raw,
        dtype=np.uint8
    ).reshape(height, width)

    u = np.frombuffer(
        u_raw,
        dtype=np.uint8
    ).reshape(height // 2, width // 2)

    v = np.frombuffer(
        v_raw,
        dtype=np.uint8
    ).reshape(height // 2, width // 2)

    return y, u, v


# ============================================================
# PSNR
# ============================================================

def psnr_from_mse(mse):

    if mse == 0:
        return float("inf")

    return 10.0 * math.log10(
        (255.0 ** 2) / mse
    )


# ============================================================
# 比較兩個 YUV
# ============================================================

def compare_yuv(ref_path, dist_path, width, height):

    ref_frames, ref_remain = get_frame_count(
        ref_path,
        width,
        height
    )

    dist_frames, dist_remain = get_frame_count(
        dist_path,
        width,
        height
    )

    # --------------------------------------------------------
    # Source 比 Decode 長時，自動只取共同 frame 數
    # --------------------------------------------------------

    compare_frames = min(
        ref_frames,
        dist_frames
    )

    if compare_frames == 0:
        raise RuntimeError(
            f"No comparable frames:\n"
            f"{ref_path}\n"
            f"{dist_path}"
        )

    info = get_yuv_info(width, height)

    y_pixels_per_frame = info["Y_SIZE"]
    uv_pixels_per_frame = info["UV_SIZE"]

    # --------------------------------------------------------
    # 累積
    # --------------------------------------------------------

    total_y_sse = 0
    total_u_sse = 0
    total_v_sse = 0

    total_y_diff_pixels = 0
    total_u_diff_pixels = 0
    total_v_diff_pixels = 0

    max_y_abs_diff = 0
    max_u_abs_diff = 0
    max_v_abs_diff = 0

    # --------------------------------------------------------
    # Worst Y frame
    # --------------------------------------------------------

    worst_frame = -1
    worst_frame_y_mse = -1.0
    worst_frame_y_psnr = float("inf")
    worst_frame_y_diff_pixels = 0
    worst_frame_y_max_diff = 0

    # --------------------------------------------------------
    # 開始比較
    # --------------------------------------------------------

    with open(ref_path, "rb") as f_ref, \
         open(dist_path, "rb") as f_dist:

        for frame_idx in range(compare_frames):

            ref_frame = read_frame(
                f_ref,
                width,
                height
            )

            dist_frame = read_frame(
                f_dist,
                width,
                height
            )

            if ref_frame is None or dist_frame is None:
                break

            ref_y, ref_u, ref_v = ref_frame
            dist_y, dist_u, dist_v = dist_frame

            # ------------------------------------------------
            # int16 避免 uint8 相減 overflow
            # ------------------------------------------------

            diff_y = (
                ref_y.astype(np.int16)
                - dist_y.astype(np.int16)
            )

            diff_u = (
                ref_u.astype(np.int16)
                - dist_u.astype(np.int16)
            )

            diff_v = (
                ref_v.astype(np.int16)
                - dist_v.astype(np.int16)
            )

            # ------------------------------------------------
            # SSE
            # ------------------------------------------------

            y64 = diff_y.astype(np.int64)
            u64 = diff_u.astype(np.int64)
            v64 = diff_v.astype(np.int64)

            y_sse = int(np.sum(y64 * y64))
            u_sse = int(np.sum(u64 * u64))
            v_sse = int(np.sum(v64 * v64))

            total_y_sse += y_sse
            total_u_sse += u_sse
            total_v_sse += v_sse

            # ------------------------------------------------
            # Different pixel count
            # ------------------------------------------------

            y_diff_pixels = int(
                np.count_nonzero(diff_y)
            )

            u_diff_pixels = int(
                np.count_nonzero(diff_u)
            )

            v_diff_pixels = int(
                np.count_nonzero(diff_v)
            )

            total_y_diff_pixels += y_diff_pixels
            total_u_diff_pixels += u_diff_pixels
            total_v_diff_pixels += v_diff_pixels

            # ------------------------------------------------
            # Maximum absolute difference
            # ------------------------------------------------

            y_max = int(
                np.max(np.abs(diff_y))
            )

            u_max = int(
                np.max(np.abs(diff_u))
            )

            v_max = int(
                np.max(np.abs(diff_v))
            )

            max_y_abs_diff = max(
                max_y_abs_diff,
                y_max
            )

            max_u_abs_diff = max(
                max_u_abs_diff,
                u_max
            )

            max_v_abs_diff = max(
                max_v_abs_diff,
                v_max
            )

            # ------------------------------------------------
            # Frame Y MSE / PSNR
            # ------------------------------------------------

            frame_y_mse = (
                y_sse / y_pixels_per_frame
            )

            frame_y_psnr = psnr_from_mse(
                frame_y_mse
            )

            # ------------------------------------------------
            # 找 hiding 差異最大的 frame
            # ------------------------------------------------

            if frame_y_mse > worst_frame_y_mse:

                worst_frame = frame_idx

                worst_frame_y_mse = (
                    frame_y_mse
                )

                worst_frame_y_psnr = (
                    frame_y_psnr
                )

                worst_frame_y_diff_pixels = (
                    y_diff_pixels
                )

                worst_frame_y_max_diff = (
                    y_max
                )

    # ========================================================
    # Overall result
    # ========================================================

    total_y_pixels = (
        compare_frames
        * y_pixels_per_frame
    )

    total_u_pixels = (
        compare_frames
        * uv_pixels_per_frame
    )

    total_v_pixels = (
        compare_frames
        * uv_pixels_per_frame
    )

    y_mse = (
        total_y_sse
        / total_y_pixels
    )

    u_mse = (
        total_u_sse
        / total_u_pixels
    )

    v_mse = (
        total_v_sse
        / total_v_pixels
    )

    y_psnr = psnr_from_mse(y_mse)
    u_psnr = psnr_from_mse(u_mse)
    v_psnr = psnr_from_mse(v_mse)

    # --------------------------------------------------------
    # Overall YUV
    #
    # YUV420:
    # Y : U : V pixel 數 = 4 : 1 : 1
    # 所以直接以所有 sample 加權
    # --------------------------------------------------------

    total_sse = (
        total_y_sse
        + total_u_sse
        + total_v_sse
    )

    total_pixels = (
        total_y_pixels
        + total_u_pixels
        + total_v_pixels
    )

    yuv_mse = (
        total_sse / total_pixels
    )

    yuv_psnr = psnr_from_mse(
        yuv_mse
    )

    return {

        "ref_frames": ref_frames,
        "dist_frames": dist_frames,
        "compare_frames": compare_frames,

        "ref_remainder": ref_remain,
        "dist_remainder": dist_remain,

        "Y_MSE": y_mse,
        "Y_PSNR": y_psnr,

        "U_MSE": u_mse,
        "U_PSNR": u_psnr,

        "V_MSE": v_mse,
        "V_PSNR": v_psnr,

        "YUV_MSE": yuv_mse,
        "YUV_PSNR": yuv_psnr,

        "Y_Different_Pixels":
            total_y_diff_pixels,

        "U_Different_Pixels":
            total_u_diff_pixels,

        "V_Different_Pixels":
            total_v_diff_pixels,

        "Y_Max_Abs_Diff":
            max_y_abs_diff,

        "U_Max_Abs_Diff":
            max_u_abs_diff,

        "V_Max_Abs_Diff":
            max_v_abs_diff,

        "Worst_Frame":
            worst_frame,

        "Worst_Frame_Y_MSE":
            worst_frame_y_mse,

        "Worst_Frame_Y_PSNR":
            worst_frame_y_psnr,

        "Worst_Frame_Y_Different_Pixels":
            worst_frame_y_diff_pixels,

        "Worst_Frame_Y_Max_Diff":
            worst_frame_y_max_diff,
    }


# ============================================================
# 找 Clean Decode YUV
# ============================================================

def find_clean_yuv(video_name, quality):

    candidates = list(
        CLEAN_ROOT.rglob("*.yuv")
    )

    matches = []

    for path in candidates:

        v = detect_video(path)
        q = detect_quality(path)

        if v != video_name:
            continue

        if q != quality:
            continue

        matches.append(path)

    if len(matches) == 0:
        return None

    if len(matches) == 1:
        return matches[0]

    # --------------------------------------------------------
    # 如果找到多個，優先選 filename 本身含 hidden_test.yuv
    # --------------------------------------------------------

    hidden_test_matches = [
        x for x in matches
        if "hidden_test" in x.name.lower()
    ]

    if len(hidden_test_matches) == 1:
        return hidden_test_matches[0]

    print()
    print("[WARNING] Clean YUV 找到多個候選：")

    for x in matches:
        print("   ", x)

    print("使用第一個：")
    print(matches[0])

    return matches[0]


# ============================================================
# 掃描所有 Steg YUV
# ============================================================

def find_steg_yuvs():

    results = []

    for directory in ROOT.iterdir():

        if not directory.is_dir():
            continue

        if directory.name in SKIP_DIRS:
            continue

        for yuv in directory.rglob("*.yuv"):

            # 必須能辨識影片
            if detect_video(yuv) is None:
                continue

            # 必須有 High / Middle / Low
            if detect_quality(yuv) is None:
                continue

            results.append(yuv)

    return sorted(results)


# ============================================================
# CSV 欄位
# ============================================================

CSV_FIELDS = [

    "experiment",

    "video",
    "quality",
    "bitrate",
    "fps",
    "width",
    "height",

    "source_file",
    "clean_file",
    "steg_file",

    "source_frames",
    "clean_frames",
    "steg_frames",

    # ========================================================
    # Source vs Clean
    # ========================================================

    "SC_Frames",

    "SC_Y_PSNR",
    "SC_U_PSNR",
    "SC_V_PSNR",
    "SC_YUV_PSNR",

    # ========================================================
    # Source vs Steg
    # ========================================================

    "SS_Frames",

    "SS_Y_PSNR",
    "SS_U_PSNR",
    "SS_V_PSNR",
    "SS_YUV_PSNR",

    # ========================================================
    # Clean vs Steg
    # ========================================================

    "CS_Frames",

    "CS_Y_MSE",
    "CS_Y_PSNR",

    "CS_U_MSE",
    "CS_U_PSNR",

    "CS_V_MSE",
    "CS_V_PSNR",

    "CS_YUV_MSE",
    "CS_YUV_PSNR",

    "CS_Y_Different_Pixels",
    "CS_U_Different_Pixels",
    "CS_V_Different_Pixels",

    "CS_Y_Max_Abs_Diff",
    "CS_U_Max_Abs_Diff",
    "CS_V_Max_Abs_Diff",

    "CS_Worst_Frame",
    "CS_Worst_Frame_Y_MSE",
    "CS_Worst_Frame_Y_PSNR",

    "CS_Worst_Frame_Y_Different_Pixels",
    "CS_Worst_Frame_Y_Max_Diff",

    "status",
]


# ============================================================
# Source vs Clean cache
#
# 同一部影片 + quality 的 Clean 是相同的，
# 不需要對每個 Steg 實驗重算一次。
# ============================================================

SOURCE_CLEAN_CACHE = {}


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("AV1 Steganography YUV Batch Comparison")
    print("=" * 80)

    print()
    print(f"ROOT       : {ROOT}")
    print(f"CLEAN ROOT : {CLEAN_ROOT}")

    steg_files = find_steg_yuvs()

    print()
    print(
        f"找到 {len(steg_files)} 個 Steg YUV"
    )

    rows = []

    for i, steg_path in enumerate(
        steg_files,
        start=1
    ):

        print()
        print("=" * 80)

        print(
            f"[{i}/{len(steg_files)}]"
        )

        print(steg_path)

        # ----------------------------------------------------
        # 所屬 experiment
        # ----------------------------------------------------

        relative = steg_path.relative_to(ROOT)

        experiment = relative.parts[0]

        # ----------------------------------------------------
        # Detect
        # ----------------------------------------------------

        video_name = detect_video(
            steg_path
        )

        quality = detect_quality(
            steg_path
        )

        if video_name is None:
            print("[SKIP] 無法辨識影片")
            continue

        if quality is None:
            print("[SKIP] 無法辨識 High/Middle/Low")
            continue

        video_info = VIDEO_INFO[
            video_name
        ]

        width = video_info["width"]
        height = video_info["height"]
        fps = video_info["fps"]

        source_path = video_info[
            "source"
        ]

        bitrate = quality_to_bitrate(
            video_name,
            quality
        )

        # ----------------------------------------------------
        # 找 clean
        # ----------------------------------------------------

        clean_path = find_clean_yuv(
            video_name,
            quality
        )

        if clean_path is None:

            print(
                "[ERROR] 找不到對應 Clean YUV"
            )

            print(
                f"Video   = {video_name}"
            )

            print(
                f"Quality = {quality}"
            )

            rows.append({
                "experiment": experiment,
                "video": video_name,
                "quality": quality,
                "bitrate": bitrate,
                "steg_file": str(steg_path),
                "status": "CLEAN_NOT_FOUND",
            })

            continue

        if not source_path.exists():

            print(
                f"[ERROR] Source 不存在："
                f"{source_path}"
            )

            continue

        # ----------------------------------------------------
        # Frames
        # ----------------------------------------------------

        source_frames, source_rem = (
            get_frame_count(
                source_path,
                width,
                height
            )
        )

        clean_frames, clean_rem = (
            get_frame_count(
                clean_path,
                width,
                height
            )
        )

        steg_frames, steg_rem = (
            get_frame_count(
                steg_path,
                width,
                height
            )
        )

        print(
            f"Video    : {video_name}"
        )

        print(
            f"Quality  : {quality}"
        )

        print(
            f"Bitrate  : {bitrate} kbps"
        )

        print(
            f"Source   : {source_path.name}"
        )

        print(
            f"Clean    : {clean_path.name}"
        )

        print(
            f"Frames   : "
            f"Source={source_frames}, "
            f"Clean={clean_frames}, "
            f"Steg={steg_frames}"
        )

        # ----------------------------------------------------
        # 檔案大小不是完整 frame
        # ----------------------------------------------------

        if source_rem != 0:
            print(
                "[WARNING] Source YUV "
                "size 不是完整 frame 倍數"
            )

        if clean_rem != 0:
            print(
                "[WARNING] Clean YUV "
                "size 不是完整 frame 倍數"
            )

        if steg_rem != 0:
            print(
                "[WARNING] Steg YUV "
                "size 不是完整 frame 倍數"
            )

        # ====================================================
        # 1. Source vs Clean
        # ====================================================

        cache_key = (
            video_name,
            quality
        )

        if cache_key in SOURCE_CLEAN_CACHE:

            sc = SOURCE_CLEAN_CACHE[
                cache_key
            ]

            print(
                "Source vs Clean : "
                "use cache"
            )

        else:

            print(
                "Source vs Clean : comparing..."
            )

            sc = compare_yuv(
                source_path,
                clean_path,
                width,
                height
            )

            SOURCE_CLEAN_CACHE[
                cache_key
            ] = sc

        # ====================================================
        # 2. Source vs Steg
        # ====================================================

        print(
            "Source vs Steg  : comparing..."
        )

        ss = compare_yuv(
            source_path,
            steg_path,
            width,
            height
        )

        # ====================================================
        # 3. Clean vs Steg
        # ====================================================

        print(
            "Clean vs Steg   : comparing..."
        )

        cs = compare_yuv(
            clean_path,
            steg_path,
            width,
            height
        )

        # ----------------------------------------------------
        # Console
        # ----------------------------------------------------

        print()

        print(
            f"Source-Clean "
            f"Y PSNR = "
            f"{sc['Y_PSNR']:.4f} dB"
        )

        print(
            f"Source-Steg  "
            f"Y PSNR = "
            f"{ss['Y_PSNR']:.4f} dB"
        )

        print(
            f"Clean-Steg   "
            f"Y PSNR = "
            f"{cs['Y_PSNR']:.4f} dB"
        )

        print(
            f"Clean-Steg worst frame = "
            f"{cs['Worst_Frame']}"
        )

        # ====================================================
        # CSV
        # ====================================================

        row = {

            "experiment":
                experiment,

            "video":
                video_name,

            "quality":
                quality,

            "bitrate":
                bitrate,

            "fps":
                fps,

            "width":
                width,

            "height":
                height,

            "source_file":
                str(source_path),

            "clean_file":
                str(clean_path),

            "steg_file":
                str(steg_path),

            "source_frames":
                source_frames,

            "clean_frames":
                clean_frames,

            "steg_frames":
                steg_frames,

            # =================================================
            # Source Clean
            # =================================================

            "SC_Frames":
                sc["compare_frames"],

            "SC_Y_PSNR":
                sc["Y_PSNR"],

            "SC_U_PSNR":
                sc["U_PSNR"],

            "SC_V_PSNR":
                sc["V_PSNR"],

            "SC_YUV_PSNR":
                sc["YUV_PSNR"],

            # =================================================
            # Source Steg
            # =================================================

            "SS_Frames":
                ss["compare_frames"],

            "SS_Y_PSNR":
                ss["Y_PSNR"],

            "SS_U_PSNR":
                ss["U_PSNR"],

            "SS_V_PSNR":
                ss["V_PSNR"],

            "SS_YUV_PSNR":
                ss["YUV_PSNR"],

            # =================================================
            # Clean Steg
            # =================================================

            "CS_Frames":
                cs["compare_frames"],

            "CS_Y_MSE":
                cs["Y_MSE"],

            "CS_Y_PSNR":
                cs["Y_PSNR"],

            "CS_U_MSE":
                cs["U_MSE"],

            "CS_U_PSNR":
                cs["U_PSNR"],

            "CS_V_MSE":
                cs["V_MSE"],

            "CS_V_PSNR":
                cs["V_PSNR"],

            "CS_YUV_MSE":
                cs["YUV_MSE"],

            "CS_YUV_PSNR":
                cs["YUV_PSNR"],

            "CS_Y_Different_Pixels":
                cs[
                    "Y_Different_Pixels"
                ],

            "CS_U_Different_Pixels":
                cs[
                    "U_Different_Pixels"
                ],

            "CS_V_Different_Pixels":
                cs[
                    "V_Different_Pixels"
                ],

            "CS_Y_Max_Abs_Diff":
                cs[
                    "Y_Max_Abs_Diff"
                ],

            "CS_U_Max_Abs_Diff":
                cs[
                    "U_Max_Abs_Diff"
                ],

            "CS_V_Max_Abs_Diff":
                cs[
                    "V_Max_Abs_Diff"
                ],

            "CS_Worst_Frame":
                cs[
                    "Worst_Frame"
                ],

            "CS_Worst_Frame_Y_MSE":
                cs[
                    "Worst_Frame_Y_MSE"
                ],

            "CS_Worst_Frame_Y_PSNR":
                cs[
                    "Worst_Frame_Y_PSNR"
                ],

            "CS_Worst_Frame_Y_Different_Pixels":
                cs[
                    "Worst_Frame_Y_Different_Pixels"
                ],

            "CS_Worst_Frame_Y_Max_Diff":
                cs[
                    "Worst_Frame_Y_Max_Diff"
                ],

            "status":
                "OK",
        }

        rows.append(row)

    # ========================================================
    # Write CSV
    # ========================================================

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=CSV_FIELDS
        )

        writer.writeheader()

        for row in rows:

            complete = {
                field: row.get(field, "")
                for field in CSV_FIELDS
            }

            writer.writerow(complete)

    print()
    print("=" * 80)
    print("全部完成")
    print("=" * 80)

    print()
    print(
        f"結果：{OUTPUT_CSV}"
    )


if __name__ == "__main__":
    main()