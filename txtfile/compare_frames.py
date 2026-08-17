import os
import cv2
import argparse
import numpy as np
from skimage import color
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
from tqdm import tqdm


def normalize_folder_name(name, remove_prefixes=None):
    if remove_prefixes is None:
        remove_prefixes = []
    for prefix in remove_prefixes:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def get_frame_files(folder):
    return sorted([
        f for f in os.listdir(folder)
        if f.startswith("frame_") and f.endswith(".png")
    ])


def compare_two_folders(folder1, folder2, output_file):
    files1 = get_frame_files(folder1)
    files2 = get_frame_files(folder2)

    if len(files1) != len(files2):
        raise ValueError(
            f"圖片數量不同！\n"
            f"{folder1}: {len(files1)} 張\n"
            f"{folder2}: {len(files2)} 張"
        )

    total_frames = len(files1)

    psnr_values = []
    ssim_values = []
    edge_diff_values = []
    gradient_diff_values = []
    fft_diff_values = []
    color_shift_values = []

    for f1, f2 in tqdm(zip(files1, files2), total=total_frames, desc=os.path.basename(folder2)):
        path1 = os.path.join(folder1, f1)
        path2 = os.path.join(folder2, f2)

        img1 = cv2.imread(path1, cv2.IMREAD_COLOR)
        img2 = cv2.imread(path2, cv2.IMREAD_COLOR)

        if img1 is None or img2 is None:
            print(f"讀取失敗: {path1} 或 {path2}")
            continue

        if img1.shape != img2.shape:
            raise ValueError(
                f"圖片尺寸不同！\n"
                f"{path1}: {img1.shape}\n"
                f"{path2}: {img2.shape}"
            )

        # PSNR
        psnr_value = psnr(img1, img2, data_range=255)
        psnr_values.append(psnr_value)

        # SSIM
        ssim_value = ssim(img1, img2, channel_axis=-1)
        ssim_values.append(ssim_value)

        # Edge Artifact (Sobel)
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        sobel1 = cv2.Sobel(gray1, cv2.CV_64F, 1, 1, ksize=3)
        sobel2 = cv2.Sobel(gray2, cv2.CV_64F, 1, 1, ksize=3)
        edge_diff = np.mean(np.abs(sobel1 - sobel2))
        edge_diff_values.append(edge_diff)

        # Gradient Discontinuity (Laplacian)
        lap1 = cv2.Laplacian(gray1, cv2.CV_64F)
        lap2 = cv2.Laplacian(gray2, cv2.CV_64F)
        gradient_diff = np.mean(np.abs(lap1 - lap2))
        gradient_diff_values.append(gradient_diff)

        # FFT Difference
        fft1 = np.fft.fftshift(np.fft.fft2(gray1))
        fft2 = np.fft.fftshift(np.fft.fft2(gray2))
        fft_diff = np.mean(np.abs(np.abs(fft1) - np.abs(fft2)))
        fft_diff_values.append(fft_diff)

        # Color Shift (deltaE)
        lab1 = cv2.cvtColor(img1, cv2.COLOR_BGR2LAB)
        lab2 = cv2.cvtColor(img2, cv2.COLOR_BGR2LAB)
        delta_e = color.deltaE_ciede2000(lab1, lab2)
        color_shift = np.mean(delta_e)
        color_shift_values.append(color_shift)

    if not psnr_values:
        raise ValueError(f"沒有成功比對任何圖片：{folder1} vs {folder2}")

    finite_psnr = [v for v in psnr_values if np.isfinite(v)]
    if finite_psnr:
        avg_psnr = np.mean(finite_psnr)
        psnr_str = f"平均 PSNR（排除 inf）: {avg_psnr:.2f} dB"
    else:
        psnr_str = "沒有有效的 PSNR 數值可計算平均"

    inf_count = sum([not np.isfinite(v) for v in psnr_values])
    avg_ssim = np.mean(ssim_values)
    avg_edge_diff = np.mean(edge_diff_values)
    avg_gradient_diff = np.mean(gradient_diff_values)
    avg_fft_diff = np.mean(fft_diff_values)
    avg_color_shift = np.mean(color_shift_values)

    lines = [
        f"folder1: {folder1}",
        f"folder2: {folder2}",
        psnr_str,
        f"inf 數量: {inf_count}，佔比: {inf_count/len(psnr_values):.2%}",
        f"平均 SSIM: {avg_ssim:.5f}",
        f"平均 Edge Difference: {avg_edge_diff:.4f}",
        f"平均 Gradient Difference: {avg_gradient_diff:.4f}",
        f"平均 FFT Difference: {avg_fft_diff:.4f}",
        f"平均 Color Shift: {avg_color_shift:.4f}",
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    return {
        "avg_psnr": np.mean(finite_psnr) if finite_psnr else float("nan"),
        "inf_ratio": inf_count / len(psnr_values),
        "avg_ssim": avg_ssim,
        "avg_edge_diff": avg_edge_diff,
        "avg_gradient_diff": avg_gradient_diff,
        "avg_fft_diff": avg_fft_diff,
        "avg_color_shift": avg_color_shift,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare PNG frames between ori and test folders.")
    parser.add_argument("--ref-root", required=True, help="參考根目錄，例如 ori")
    parser.add_argument("--test-root", required=True, help="測試根目錄，例如 hidden_3")
    parser.add_argument("--ref-prefix", default="ori_", help="ref 子資料夾名前綴，預設 ori_")
    parser.add_argument("--test-prefix", default="hidden_", help="test 子資料夾名前綴，預設 coeff_hidden_")
    parser.add_argument("--output-dir", default="compare_results", help="輸出結果資料夾")
    args = parser.parse_args()

    ref_root = os.path.abspath(args.ref_root)
    test_root = os.path.abspath(args.test_root)
    output_dir = os.path.abspath(args.output_dir)

    os.makedirs(output_dir, exist_ok=True)

    ref_subdirs = [
        d for d in os.listdir(ref_root)
        if os.path.isdir(os.path.join(ref_root, d))
    ]
    test_subdirs = [
        d for d in os.listdir(test_root)
        if os.path.isdir(os.path.join(test_root, d))
    ]

    ref_map = {
        normalize_folder_name(d, [args.ref_prefix]): d
        for d in ref_subdirs
    }
    test_map = {
        normalize_folder_name(d, [args.test_prefix]): d
        for d in test_subdirs
    }

    common_keys = sorted(set(ref_map.keys()) & set(test_map.keys()))
    only_ref = sorted(set(ref_map.keys()) - set(test_map.keys()))
    only_test = sorted(set(test_map.keys()) - set(ref_map.keys()))

    print(f"找到可比對子資料夾數量: {len(common_keys)}")

    if only_ref:
        print("\n只在 ref-root 出現：")
        for k in only_ref:
            print("  ", ref_map[k])

    if only_test:
        print("\n只在 test-root 出現：")
        for k in only_test:
            print("  ", test_map[k])

    summary_lines = []

    for key in common_keys:
        ref_dir_name = ref_map[key]
        test_dir_name = test_map[key]

        folder1 = os.path.join(ref_root, ref_dir_name)
        folder2 = os.path.join(test_root, test_dir_name)

        result_file = os.path.join(output_dir, f"{key}.txt")

        try:
            metrics = compare_two_folders(folder1, folder2, result_file)
            summary_lines.append(
                f"{key}\tPSNR={metrics['avg_psnr']:.2f}\tSSIM={metrics['avg_ssim']:.5f}\t"
                f"Edge={metrics['avg_edge_diff']:.4f}\tGrad={metrics['avg_gradient_diff']:.4f}\t"
                f"FFT={metrics['avg_fft_diff']:.4f}\tColor={metrics['avg_color_shift']:.4f}\t"
                f"InfRatio={metrics['inf_ratio']:.2%}"
            )
            print(f"[OK] {ref_dir_name} <-> {test_dir_name}")
        except Exception as e:
            err_msg = f"[FAIL] {ref_dir_name} <-> {test_dir_name}: {e}"
            summary_lines.append(err_msg)
            print(err_msg)

    summary_path = os.path.join(output_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")

    print(f"\nDone! summary 寫到: {summary_path}")


if __name__ == "__main__":
    main()
