import os
import cv2
import numpy as np
from skimage import color
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
from tqdm import tqdm

# 設定你的資料夾路徑
folder1 = "psnr_ori"
folder2 = "psnr_hidden"

# 抓 frame 名稱（假設檔名格式為 frame_xxxx.png）
files1 = sorted([f for f in os.listdir(folder1) if f.startswith("frame_") and f.endswith(".png")])
files2 = sorted([f for f in os.listdir(folder2) if f.startswith("frame_") and f.endswith(".png")])

if len(files1) != len(files2):
    raise ValueError("兩個資料夾的圖片數量不同！")

total_frames = len(files1)

# Store results
psnr_values = []
ssim_values = []
edge_diff_values = []
gradient_diff_values = []
fft_diff_values = []
color_shift_values = []

for f1, f2 in tqdm(zip(files1, files2), total=total_frames):
    img1 = cv2.imread(os.path.join(folder1, f1), cv2.IMREAD_COLOR)
    img2 = cv2.imread(os.path.join(folder2, f2), cv2.IMREAD_COLOR)

    if img1 is None or img2 is None:
        print(f"讀取失敗: {f1} 或 {f2}")
        continue

    # =======================
    # 🔹 PSNR
    # =======================
    psnr_value = psnr(img1, img2, data_range=255)
    psnr_values.append(psnr_value)

    # =======================
    # 🔹 SSIM
    # =======================
    ssim_value = ssim(img1, img2, channel_axis=-1)
    ssim_values.append(ssim_value)

    # =======================
    # 🔹 Edge Artifact (Sobel)
    # =======================
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    sobel1 = cv2.Sobel(gray1, cv2.CV_64F, 1, 1, ksize=3)
    sobel2 = cv2.Sobel(gray2, cv2.CV_64F, 1, 1, ksize=3)
    edge_diff = np.mean(np.abs(sobel1 - sobel2))
    edge_diff_values.append(edge_diff)

    # =======================
    # 🔹 Gradient Discontinuity (Laplacian)
    # =======================
    lap1 = cv2.Laplacian(gray1, cv2.CV_64F)
    lap2 = cv2.Laplacian(gray2, cv2.CV_64F)
    gradient_diff = np.mean(np.abs(lap1 - lap2))
    gradient_diff_values.append(gradient_diff)

    # =======================
    # 🔹 FFT (Ringing Artifact)
    # =======================
    fft1 = np.fft.fftshift(np.fft.fft2(gray1))
    fft2 = np.fft.fftshift(np.fft.fft2(gray2))
    fft_diff = np.mean(np.abs(np.abs(fft1) - np.abs(fft2)))
    fft_diff_values.append(fft_diff)

    # =======================
    # 🔹 Color Shift (deltaE)
    # =======================
    lab1 = cv2.cvtColor(img1, cv2.COLOR_BGR2LAB)
    lab2 = cv2.cvtColor(img2, cv2.COLOR_BGR2LAB)
    delta_e = color.deltaE_ciede2000(lab1, lab2)
    color_shift = np.mean(delta_e)
    color_shift_values.append(color_shift)

# 處理 PSNR
finite_psnr = [v for v in psnr_values if np.isfinite(v)]
if finite_psnr:
    avg_psnr = np.mean(finite_psnr)
    psnr_str = f"平均 PSNR（排除 inf）: {avg_psnr:.2f} dB"
else:
    psnr_str = "沒有有效的 PSNR 數值可計算平均"

inf_count = sum([not np.isfinite(v) for v in psnr_values])

# 平均 SSIM
avg_ssim = np.mean(ssim_values)

avg_edge_diff = np.mean(edge_diff_values)
avg_gradient_diff = np.mean(gradient_diff_values)
avg_fft_diff = np.mean(fft_diff_values)
avg_color_shift = np.mean(color_shift_values)

lines = [
    psnr_str,
    f"inf 數量: {inf_count}，佔比: {inf_count/len(psnr_values):.2%}",
    f"平均 SSIM: {avg_ssim:.5f}",
    f"平均 Edge Difference: {avg_edge_diff:.4f}",
    f"平均 Gradient Difference: {avg_gradient_diff:.4f}",
    f"平均 FFT Difference: {avg_fft_diff:.4f}",
    f"平均 Color Shift: {avg_color_shift:.4f}",
]

# 寫入檔案
with open("result.txt", "w", encoding="utf-8") as f:
    for line in lines:
        f.write(line + "\n")

print("Done! 結果已輸出到 result.txt")


# ==============================
# 🔹 Visualization of Results
# ==============================

#plt.figure(figsize=(12, 6))

#plt.subplot(2, 3, 1)
#plt.plot(psnr_values, label='PSNR (dB)')
#plt.axhline(y=30, color='r', linestyle='--', label='30 dB (Good Quality Threshold)')
#plt.xlabel('Frame')
#plt.ylabel('PSNR (dB)')
#plt.legend()
#plt.grid(True)

#plt.subplot(2, 3, 2)
#plt.plot(edge_diff_values, label='Edge Artifacts')
#plt.xlabel('Frame')
#plt.ylabel('Edge Difference')
#plt.legend()
#plt.grid(True)

#plt.subplot(2, 3, 3)
#plt.plot(gradient_diff_values, label='Gradient Discontinuity')
#plt.xlabel('Frame')
#plt.ylabel('Gradient Difference')
#plt.legend()
#plt.grid(True)

#plt.subplot(2, 3, 4)
#plt.plot(fft_diff_values, label='Ringing Artifacts')
#plt.xlabel('Frame')
#plt.ylabel('FFT Difference')
#plt.legend()
#plt.grid(True)

#plt.subplot(2, 3, 5)
#plt.plot(color_shift_values, label='Color Shift')
#plt.xlabel('Frame')
#plt.ylabel('Color Shift')
#plt.legend()
#plt.grid(True)

#plt.tight_layout()
#plt.show()
