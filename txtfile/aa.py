import os
import argparse
import cv2
import numpy as np
from skimage import color
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser(
        description="比較兩個資料夾中的 frame 圖片，計算 PSNR、SSIM 等指標"
    )

    parser.add_argument(
        "--folder1",
        "-f1",
        required=True,
        help="原始圖片資料夾，例如 psnr_ori",
    )

    parser.add_argument(
        "--folder2",
        "-f2",
        required=True,
        help="比較圖片資料夾，例如 psnr_hidden",
    )

    parser.add_argument(
        "--output",
        "-o",
        default="result.txt",
        help="結果輸出檔案，預設為 result.txt",
    )

    parser.add_argument(
        "--prefix",
        default="frame_",
        help="圖片檔名前綴，預設為 frame_",
    )

    parser.add_argument(
        "--extension",
        default=".png",
        help="圖片副檔名，預設為 .png",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    folder1 = args.folder1
    folder2 = args.folder2
    output_file = args.output
    prefix = args.prefix
    extension = args.extension

    if not os.path.isdir(folder1):
        raise FileNotFoundError(f"找不到資料夾: {folder1}")

    if not os.path.isdir(folder2):
        raise FileNotFoundError(f"找不到資料夾: {folder2}")

    files1 = sorted(
        [
            f
            for f in os.listdir(folder1)
            if f.startswith(prefix) and f.endswith(extension)
        ]
    )

    files2 = sorted(
        [
            f
            for f in os.listdir(folder2)
            if f.startswith(prefix) and f.endswith(extension)
        ]
    )

    if not files1:
        raise ValueError(f"{folder1} 中找不到符合條件的圖片")

    if not files2:
        raise ValueError(f"{folder2} 中找不到符合條件的圖片")

    if len(files1) != len(files2):
        raise ValueError(
            f"兩個資料夾的圖片數量不同："
            f"{folder1} 有 {len(files1)} 張，"
            f"{folder2} 有 {len(files2)} 張"
        )

    # 確認排序後的檔名完全相同
    if files1 != files2:
        only_in_folder1 = sorted(set(files1) - set(files2))
        only_in_folder2 = sorted(set(files2) - set(files1))

        raise ValueError(
            "兩個資料夾的檔名不一致。\n"
            f"只存在 {folder1} 的檔案: {only_in_folder1[:10]}\n"
            f"只存在 {folder2} 的檔案: {only_in_folder2[:10]}"
        )

    total_frames = len(files1)

    psnr_values = []
    ssim_values = []
    edge_diff_values = []
    gradient_diff_values = []
    fft_diff_values = []
    color_shift_values = []

    valid_frame_count = 0

    for filename in tqdm(files1, total=total_frames):
        path1 = os.path.join(folder1, filename)
        path2 = os.path.join(folder2, filename)

        img1 = cv2.imread(path1, cv2.IMREAD_COLOR)
        img2 = cv2.imread(path2, cv2.IMREAD_COLOR)

        if img1 is None or img2 is None:
            print(f"讀取失敗: {path1} 或 {path2}")
            continue

        if img1.shape != img2.shape:
            print(
                f"圖片尺寸不同，跳過 {filename}: "
                f"{img1.shape} vs {img2.shape}"
            )
            continue

        valid_frame_count += 1

        # PSNR
        psnr_value = psnr(img1, img2, data_range=255)
        psnr_values.append(psnr_value)

        # SSIM
        ssim_value = ssim(
            img1,
            img2,
            channel_axis=-1,
            data_range=255,
        )
        ssim_values.append(ssim_value)

        # 灰階圖片
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Edge Artifact：Sobel
        sobel1 = cv2.Sobel(gray1, cv2.CV_64F, 1, 1, ksize=3)
        sobel2 = cv2.Sobel(gray2, cv2.CV_64F, 1, 1, ksize=3)

        edge_diff = np.mean(np.abs(sobel1 - sobel2))
        edge_diff_values.append(edge_diff)

        # Gradient Discontinuity：Laplacian
        lap1 = cv2.Laplacian(gray1, cv2.CV_64F)
        lap2 = cv2.Laplacian(gray2, cv2.CV_64F)

        gradient_diff = np.mean(np.abs(lap1 - lap2))
        gradient_diff_values.append(gradient_diff)

        # FFT：Ringing Artifact
        fft1 = np.fft.fftshift(np.fft.fft2(gray1))
        fft2 = np.fft.fftshift(np.fft.fft2(gray2))

        fft_diff = np.mean(
            np.abs(np.abs(fft1) - np.abs(fft2))
        )
        fft_diff_values.append(fft_diff)

        # Color Shift：CIEDE2000
        # OpenCV 的 LAB 數值範圍不是 skimage 預期的格式，
        # 因此先轉成 RGB，再使用 skimage 轉 LAB。
        rgb1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB) / 255.0
        rgb2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB) / 255.0

        lab1 = color.rgb2lab(rgb1)
        lab2 = color.rgb2lab(rgb2)

        delta_e = color.deltaE_ciede2000(lab1, lab2)
        color_shift = np.mean(delta_e)
        color_shift_values.append(color_shift)

    if valid_frame_count == 0:
        raise ValueError("沒有成功比較任何圖片")

    finite_psnr = [
        value
        for value in psnr_values
        if np.isfinite(value)
    ]

    if finite_psnr:
        avg_psnr = np.mean(finite_psnr)
        psnr_str = f"平均 PSNR（排除 inf）: {avg_psnr:.2f} dB"
    else:
        psnr_str = "沒有有限的 PSNR 數值可計算平均"

    inf_count = sum(
        not np.isfinite(value)
        for value in psnr_values
    )

    avg_ssim = np.mean(ssim_values)
    avg_edge_diff = np.mean(edge_diff_values)
    avg_gradient_diff = np.mean(gradient_diff_values)
    avg_fft_diff = np.mean(fft_diff_values)
    avg_color_shift = np.mean(color_shift_values)

    lines = [
        f"Folder 1: {folder1}",
        f"Folder 2: {folder2}",
        f"圖片總數: {total_frames}",
        f"有效比較數量: {valid_frame_count}",
        psnr_str,
        (
            f"inf 數量: {inf_count}，"
            f"佔比: {inf_count / len(psnr_values):.2%}"
        ),
        f"平均 SSIM: {avg_ssim:.5f}",
        f"平均 Edge Difference: {avg_edge_diff:.4f}",
        f"平均 Gradient Difference: {avg_gradient_diff:.4f}",
        f"平均 FFT Difference: {avg_fft_diff:.4f}",
        f"平均 Color Shift: {avg_color_shift:.4f}",
    ]

    with open(output_file, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\nDone! 結果已輸出到 {output_file}")


if __name__ == "__main__":
    main()


