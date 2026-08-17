from pathlib import Path
import csv
import math
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 使用者設定
# ============================================================

WIDTH = 1280
HEIGHT = 720

# ------------------------------------------------------------
# Clean YUV
# 必須是用 FFmpeg 從 clean AVIF decode 出來的 YUV
# ------------------------------------------------------------

CLEAN_YUV = Path(
    r"D:\碩士實驗\testdata\ori_video"
    r"\Johnny_720p_60_High"
    r"\Johnny_720p_60_High_hidden_test.yuv"
)


# ------------------------------------------------------------
# 要一起比較的 Steg YUV
#
# 名稱可以自己設定。
# 所有檔案都必須：
#   1. 同一部影片
#   2. 同一 bitrate
#   3. 同一 frame range
# ------------------------------------------------------------
'''
STEG_YUVS = {
    "Basic": Path(
        r"D:\碩士實驗\testdata\angle_test"
        r"\catania\Johnny_720p_60_High"
        r"\Johnny_720p_60_High_hidden_test.yuv"
    ),

    "Center": Path(
        r"D:\碩士實驗\testdata\angle_test"
        r"\center\Johnny_720p_60_High"
        r"\Johnny_720p_60_High_hidden_test.yuv"
    ),

    "Adaptive_RDO": Path(
        r"D:\碩士實驗\testdata\angle_test"
        r"\rdo_cho\Johnny_720p_60_High"
        r"\Johnny_720p_60_High_hidden_test.yuv"
    ),
}
'''
'''STEG_YUVS = {
    "Angle_Only": Path(
        r"D:\碩士實驗\testdata\angle_test"
        r"\rdo_cho\Johnny_720p_60_High"
        r"\Johnny_720p_60_High_hidden_test.yuv"
    ),

    "Joint_All": Path(
        r"D:\碩士實驗\testdata\angle_coeff_test\angle_all\Johnny_720p_60_High\Johnny_720p_60_High_hidden_test.yuv"
    ),

    "Joint_DCT": Path(
        r"D:\碩士實驗\testdata\angle_coeff_test\angle_dct\Johnny_720p_60_High\Johnny_720p_60_High_hidden_test.yuv"
    ),

    "Joint_TX_Aware": Path(
        r"D:\碩士實驗\testdata\angle_coeff_test\angle_aware\Johnny_720p_60_High\Johnny_720p_60_High_hidden_test.yuv"
    ),
}'''


STEG_YUVS = {
    "AV1Stego": Path(
        r"D:\碩士實驗\testdata\AV1Stego\1024\Johnny_720p_60_High\Johnny_720p_60_High_hidden_test.yuv"
    ),

    "StegAV1": Path(
        r"D:\碩士實驗\testdata\StegAV1\1024\Johnny_720p_60_High\Johnny_720p_60_High_hidden_test.yuv"
    ),
}

# ------------------------------------------------------------
# 輸出位置
# ------------------------------------------------------------

OUTPUT_DIR = Path(
    #r"D:\碩士實驗\testdata\difference_map\angle_johnny_high"
    #r"D:\碩士實驗\testdata\difference_map\joint_johnny_high"
    r"D:\碩士實驗\testdata\difference_map\AV1StegovsStegAV1_johnny_high"
)


# ============================================================
# Frame 選擇方式
#
# "auto_sum"
#   → 找所有方法相對 Clean 的 Y-plane MSE 總和最大 frame
#      最適合公平比較多種方法
#
# "specific"
#   → 使用你自己指定的 frame
# ============================================================

FRAME_MODE = "auto_sum"

SPECIFIC_FRAME = 100


# ============================================================
# Difference Map 放大倍率
#
# 所有方法一定使用相同倍率
# ============================================================

DIFF_SCALE =2


# ============================================================
# 是否輸出 Steg 原始 frame
# ============================================================

SAVE_STEG_FRAME = True


# ============================================================
# YUV420p 8-bit
# ============================================================

Y_SIZE = WIDTH * HEIGHT
UV_SIZE = (WIDTH // 2) * (HEIGHT // 2)

FRAME_SIZE = (
    Y_SIZE
    + UV_SIZE
    + UV_SIZE
)


# ============================================================
# 工具
# ============================================================

def get_frame_count(path):
    size = path.stat().st_size

    frames = size // FRAME_SIZE
    remain = size % FRAME_SIZE

    return frames, remain


def read_y_plane(file_obj, frame_index):
    """
    直接跳到指定 frame，只讀 Y plane。
    """

    offset = frame_index * FRAME_SIZE

    file_obj.seek(offset)

    data = file_obj.read(Y_SIZE)

    if len(data) != Y_SIZE:
        return None

    return np.frombuffer(
        data,
        dtype=np.uint8
    ).reshape(
        HEIGHT,
        WIDTH
    )


def calculate_mse(a, b):
    diff = (
        a.astype(np.float64)
        - b.astype(np.float64)
    )

    return np.mean(
        diff ** 2
    )


def psnr_from_mse(mse):
    if mse == 0:
        return float("inf")

    return 10.0 * math.log10(
        (255.0 ** 2) / mse
    )


# ============================================================
# 儲存 grayscale PNG
# ============================================================

def save_gray_image(array, output_path):
    """
    直接以 0~255 grayscale 儲存。
    不使用 colormap，
    Difference Map 比較比較直觀。
    """

    plt.imsave(
        output_path,
        array,
        cmap="gray",
        vmin=0,
        vmax=255
    )


# ============================================================
# 找共同 frame
# ============================================================

def find_best_common_frame(clean_path, steg_paths):
    """
    對每一個 frame 計算：

        sum MSE =
        MSE(Clean, Basic)
        + MSE(Clean, Center)
        + MSE(Clean, RDO)
        + ...

    最後挑 sum MSE 最大的 frame。

    這樣所有方法使用同一張 frame，
    不會有每個方法各挑自己 worst frame 的公平性問題。
    """

    clean_frames, _ = get_frame_count(
        clean_path
    )

    steg_frame_counts = []

    for path in steg_paths.values():
        frames, _ = get_frame_count(path)
        steg_frame_counts.append(frames)

    compare_frames = min(
        [clean_frames]
        + steg_frame_counts
    )

    print()
    print(
        f"Searching {compare_frames} common frames..."
    )

    best_frame = -1
    best_sum_mse = -1

    # 同時保存每個方法自己的 MSE
    best_detail = None

    with open(clean_path, "rb") as clean_file:

        steg_files = {
            name: open(path, "rb")
            for name, path in steg_paths.items()
        }

        try:

            for frame_idx in range(compare_frames):

                clean_y = read_y_plane(
                    clean_file,
                    frame_idx
                )

                total_mse = 0
                detail = {}

                for name, file_obj in steg_files.items():

                    steg_y = read_y_plane(
                        file_obj,
                        frame_idx
                    )

                    mse = calculate_mse(
                        clean_y,
                        steg_y
                    )

                    detail[name] = mse
                    total_mse += mse

                if total_mse > best_sum_mse:

                    best_sum_mse = total_mse
                    best_frame = frame_idx
                    best_detail = detail.copy()

        finally:

            for file_obj in steg_files.values():
                file_obj.close()

    return (
        best_frame,
        best_sum_mse,
        best_detail
    )


# ============================================================
# 產生 Difference Map
# ============================================================

def generate_maps(frame_index):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("=" * 80)
    print(f"Generating frame {frame_index}")
    print("=" * 80)

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    with open(CLEAN_YUV, "rb") as f:

        clean_y = read_y_plane(
            f,
            frame_index
        )

    if clean_y is None:
        raise RuntimeError(
            "Clean frame read failed."
        )

    clean_png = (
        OUTPUT_DIR
        / f"frame_{frame_index:04d}_Clean.png"
    )

    save_gray_image(
        clean_y,
        clean_png
    )

    rows = []

    # --------------------------------------------------------
    # 每種方法
    # --------------------------------------------------------

    for method, steg_path in STEG_YUVS.items():

        with open(steg_path, "rb") as f:

            steg_y = read_y_plane(
                f,
                frame_index
            )

        if steg_y is None:
            raise RuntimeError(
                f"{method}: frame read failed."
            )

        # ----------------------------------------------------
        # 原始 Difference
        # ----------------------------------------------------

        diff = np.abs(
            clean_y.astype(np.int16)
            - steg_y.astype(np.int16)
        )

        mse = np.mean(
            diff.astype(np.float64) ** 2
        )

        psnr = psnr_from_mse(
            mse
        )

        different_pixels = int(
            np.count_nonzero(diff)
        )

        max_diff = int(
            np.max(diff)
        )

        mean_abs_diff = float(
            np.mean(diff)
        )

        # ----------------------------------------------------
        # Difference Map 放大
        # ----------------------------------------------------

        scaled_diff = np.clip(
            diff.astype(np.int32)
            * DIFF_SCALE,
            0,
            255
        ).astype(np.uint8)

        # ----------------------------------------------------
        # Steg frame
        # ----------------------------------------------------

        if SAVE_STEG_FRAME:

            steg_png = (
                OUTPUT_DIR
                / (
                    f"frame_{frame_index:04d}"
                    f"_{method}.png"
                )
            )

            save_gray_image(
                steg_y,
                steg_png
            )

        # ----------------------------------------------------
        # Difference map
        # ----------------------------------------------------

        diff_png = (
            OUTPUT_DIR
            / (
                f"frame_{frame_index:04d}"
                f"_{method}"
                f"_diff_x{DIFF_SCALE}.png"
            )
        )

        save_gray_image(
            scaled_diff,
            diff_png
        )

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        rows.append({
            "frame":
                frame_index,

            "method":
                method,

            "MSE":
                mse,

            "PSNR":
                psnr,

            "Different_Pixels":
                different_pixels,

            "Different_Pixel_Ratio":
                different_pixels / Y_SIZE,

            "Mean_Abs_Diff":
                mean_abs_diff,

            "Max_Abs_Diff":
                max_diff,

            "Diff_Scale":
                DIFF_SCALE,

            "Clean_YUV":
                str(CLEAN_YUV),

            "Steg_YUV":
                str(steg_path),
        })

        print()
        print(method)

        print(
            f"  MSE              = "
            f"{mse:.6f}"
        )

        print(
            f"  PSNR             = "
            f"{psnr:.4f} dB"
        )

        print(
            f"  Different pixels = "
            f"{different_pixels:,}"
        )

        print(
            f"  Difference ratio = "
            f"{different_pixels / Y_SIZE:.6%}"
        )

        print(
            f"  Mean abs diff    = "
            f"{mean_abs_diff:.6f}"
        )

        print(
            f"  Max abs diff     = "
            f"{max_diff}"
        )

    # ========================================================
    # CSV
    # ========================================================

    csv_path = (
        OUTPUT_DIR
        / f"frame_{frame_index:04d}_result.csv"
    )

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        fieldnames = [
            "frame",
            "method",
            "MSE",
            "PSNR",
            "Different_Pixels",
            "Different_Pixel_Ratio",
            "Mean_Abs_Diff",
            "Max_Abs_Diff",
            "Diff_Scale",
            "Clean_YUV",
            "Steg_YUV",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 80)
    print("Output")
    print("=" * 80)

    print(OUTPUT_DIR)


# ============================================================
# 檢查輸入
# ============================================================

def check_files():

    if not CLEAN_YUV.exists():
        raise FileNotFoundError(
            f"Clean YUV 不存在：\n{CLEAN_YUV}"
        )

    for name, path in STEG_YUVS.items():

        if not path.exists():
            raise FileNotFoundError(
                f"{name} YUV 不存在：\n{path}"
            )

    print("=" * 80)
    print("Input")
    print("=" * 80)

    clean_frames, clean_remain = (
        get_frame_count(CLEAN_YUV)
    )

    print()
    print("Clean")
    print(CLEAN_YUV)

    print(
        f"Frames = {clean_frames}"
    )

    if clean_remain != 0:
        print(
            f"[WARNING] remainder = "
            f"{clean_remain}"
        )

    for name, path in STEG_YUVS.items():

        frames, remain = (
            get_frame_count(path)
        )

        print()
        print(name)
        print(path)

        print(
            f"Frames = {frames}"
        )

        if remain != 0:
            print(
                f"[WARNING] remainder = "
                f"{remain}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    check_files()

    if FRAME_MODE == "auto_sum":

        (
            frame_index,
            sum_mse,
            detail
        ) = find_best_common_frame(
            CLEAN_YUV,
            STEG_YUVS
        )

        print()
        print("=" * 80)
        print("Selected common frame")
        print("=" * 80)

        print(
            f"Frame = {frame_index}"
        )

        print(
            f"Sum MSE = {sum_mse:.6f}"
        )

        print()

        for method, mse in detail.items():

            print(
                f"{method:20s}: "
                f"MSE = {mse:.6f}"
            )

    elif FRAME_MODE == "specific":

        frame_index = (
            SPECIFIC_FRAME
        )

        print(
            f"Using specific frame: "
            f"{frame_index}"
        )

    else:

        raise ValueError(
            "FRAME_MODE 必須是 "
            "'auto_sum' 或 'specific'"
        )

    generate_maps(
        frame_index
    )


if __name__ == "__main__":
    main()