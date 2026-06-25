 # AV1 Hidden Data Encoder / Decoder

本專案基於 AV1 編碼器進行資料隱藏實驗，主要研究在 AV1 編碼流程中，透過修改特定編碼資訊來嵌入隱藏資料，並在解碼端進行資料擷取。

This project is based on the AV1 encoder and focuses on data hiding experiments.  
The main objective is to embed hidden information by modifying selected coding syntax or coding decisions during the AV1 encoding process, and then extract the embedded information during decoding.

---

## 1. Project Overview / 專案介紹

本研究目前主要包含兩種資料隱藏方式：

1. **Angle-based data hiding**  
   透過 AV1 幀內預測角度模式進行資料嵌入。

2. **Coefficient-based data hiding**  
   透過 AV1 量化後係數或掃描位置相關資訊進行資料嵌入。

目前資料嵌入內容已支援由外部二進位檔案 `data.bin` 讀取。

During encoding, the encoder reads the hidden payload from an external binary file named `data.bin`, and embeds the payload into the AV1 bitstream according to the selected data hiding method.

---

## 2. Build Instructions / 編譯方式

### 2.1 Clone the Repository / 下載專案

```bash
git clone https://github.com/azswsxde/aom_hidden_data
```

### 2.2 Build AOM / 建立 AOM 編譯環境

```bash
make aom_build
```

### 2.3 Configure and Compile / 設定與編譯

```bash
cd aom_build
cmake path/to/aom_hidden_data
make
```

其中 `path/to/aom_hidden_data` 請替換成實際的專案路徑。

Replace `path/to/aom_hidden_data` with the actual path of this project.

---

## 3. Usage / 使用方式

### 3.1 Encoder / 編碼器

```bash
./simple_encoder_mark av1 (video height) (video width) (yuv file path with name) (output avif path with name) (fps) 0 (total_frame) (bitrate)
```

#### Parameters / 參數說明

| Parameter                    | Description     |
| ---------------------------- | --------------- |
| `av1`                        | 使用 AV1 編碼格式     |
| `video height`               | 輸入 YUV 影片高度     |
| `video width`                | 輸入 YUV 影片寬度     |
| `yuv file path with name`    | 輸入 YUV 檔案路徑與檔名  |
| `output avif path with name` | 輸出 AVIF 檔案路徑與檔名 |
| `fps`                        | 影片幀率            |
| `0`                          | 起始幀或 offset 參數  |
| `total_frame`                | 編碼總幀數           |
| `bitrate`                    | 目標位元率           |

#### Hidden Payload File / 隱藏資料檔案

Before running the encoder, prepare a binary payload file named `data.bin`.

The encoder reads the hidden payload from `data.bin` during encoding. The file content is loaded as binary data and converted into a bitstream for embedding. After the payload is loaded, the encoder automatically appends the keyword `NCU` to the end of the payload as an ending symbol. Therefore, users only need to place the original payload content in `data.bin`; the ending keyword does not need to be manually added.

編碼前請先準備一個名為 `data.bin` 的二進位檔案。

Encoder 會在 encoding 過程中讀取 `data.bin` 作為欲嵌入的隱藏資料。檔案內容會以 binary data 方式讀入，並轉換成 bitstream 後進行嵌入。讀取檔案內容後，encoder 會自動在 payload 最後加入 `NCU` 作為資料結束符號。因此，使用者只需要將原始欲嵌入資料放入 `data.bin`，不需要手動在檔案尾端加入結束符號。

`data.bin` should be placed in the working directory where `simple_encoder_mark` is executed, unless another path is configured in the source code.

`data.bin` 應放在執行 `simple_encoder_mark` 的工作目錄下，除非程式碼中有另外指定其他讀取路徑。

If `data.bin` cannot be found or cannot be loaded correctly, the encoder will not have a valid hidden payload to embed. Please check the execution directory and file permission before running the encoder.

若 `data.bin` 不存在或讀取失敗，encoder 將無法取得有效的 hidden payload 進行嵌入。執行前請確認工作目錄與檔案權限是否正確。

Example:

```bash
head -c 1024 /dev/urandom > data.bin
./simple_encoder_mark av1 1280 720 input.yuv output.avif 30 0 150 8192
```

In this example, the encoder reads the content of `data.bin`, automatically appends `NCU` after `hidden message`, and embeds the resulting payload during AV1 encoding.

在此範例中，encoder 會讀取 `data.bin` 中的 `hidden message`，接著自動在資料最後加入 `NCU`，並將完整 payload 嵌入至 AV1 編碼流程中。


---

### 3.2 Decoder / 解碼器

```bash
./simple_decoder_mark (avif path with name) (out yuv file path with name)
```

#### Parameters / 參數說明

| Parameter | Description |
|---|---|
| `avif path with name` | 輸入 AVIF 檔案路徑與檔名 |
| `out yuv file path with name` | 輸出 YUV 檔案路徑與檔名 |

---

## 4. Example / 使用範例

### Encoding / 編碼

```bash
./simple_encoder_mark av1 1280 720 /home/mark/500GB/testdata/VIRAT.yuv VIRAT_offset0_padding0_hidden_all_y_plane_only.avif 30 0 150 8192 > ~/paper/encode.txt
```

### Decoding / 解碼

```bash
./simple_decoder_mark VIRAT_offset0_padding0_hidden_all_y_plane_only.avif VIRAT_offset0_padding0_hidden_all_y_plane_only.yuv > ~/paper/decode.txt
```

在上述範例中，編碼結果會輸出為 `.avif` 檔案，並將編碼過程中的資訊記錄至 `encode.txt`。  
解碼後的 YUV 影片會輸出為指定檔案，解碼與資料擷取資訊則記錄至 `decode.txt`。

In this example, the encoded result is saved as an `.avif` file, while encoding logs are redirected to `encode.txt`.  
The decoded YUV file is generated after decoding, and decoding or extraction logs are redirected to `decode.txt`.

---

## 5. Data Hiding Methods / 資料隱藏方法

### 5.1 Angle-based Data Hiding / 幀內預測角度資料隱藏

Angle-based data hiding embeds information by modifying or selecting specific intra prediction angle-related coding decisions in AV1.

本方法利用 AV1 幀內預測中的角度模式資訊進行資料嵌入。  
由於幀內預測模式會影響像素預測方向，因此此方法需要考量下列因素：

- 嵌入資料後的影像品質變化
- 預測角度修改後造成的失真
- 不同區塊大小下的穩定性
- 不同 bitrate 下的可嵌入容量與錯誤率
- 解碼端是否能穩定還原嵌入資料

相關程式碼位置如下：

| Process | File |
|---|---|
| Encoder embedding | `encodeframe_utils.c` |
| Decoder extraction | `decodemv.c` |

---

### 5.2 Coefficient-based Data Hiding / 係數資料隱藏

Coefficient-based data hiding embeds information by modifying selected transform coefficient-related information after quantization.

本方法主要針對 AV1 量化後的轉換係數進行資料嵌入。  
由於係數會直接影響重建影像品質，因此需要特別注意嵌入位置與條件控制。

可測試的實驗條件包含：

- 量化參數條件
- 掃描位置選擇
- 區塊條件限制
- 嵌入密度控制
- non-zero AC coefficient ratio 條件
- 不同 bitrate 下的穩定性
- 不同影片內容下的影像品質與容量變化

相關程式碼位置如下：

| Process | File |
|---|---|
| Encoder embedding | `encodemb.c` |
| Decoder extraction | `decodeframe.c` |

---

## 6. Experimental Control / 實驗控制方式

目前可透過手動開啟或關閉程式碼中的條件來測試不同實驗項目。

The experimental conditions can currently be controlled by manually enabling or disabling specific parts of the source code.

建議測試項目包含：

| Item | Description |
|---|---|
| Q condition | 測試不同量化條件下的嵌入效果 |
| Scan position | 測試不同係數掃描位置的穩定性 |
| Block condition | 測試不同區塊條件限制 |
| Embedding density | 控制每個區塊或每個 frame 的嵌入量 |
| Non-zero AC ratio | 限制非零 AC 係數比例，以降低影像失真 |
| Bitrate | 比較不同 bitrate 下的影像品質與嵌入穩定性 |
| Video content | 比較不同影片內容對資料隱藏效果的影響 |

---

## 7. Current Limitations / 目前限制

目前版本仍屬於研究與實驗階段，具有以下限制：

1. Hidden payload 目前固定由工作目錄下的 `data.bin` 讀取，尚未提供 command-line argument 指定 payload path。
2. Encoder 會自動在 payload 最後加入 `NCU` 作為結束符號，目前尚未加入 payload length header 或更完整的同步機制。
3. 實驗條件主要透過手動修改程式碼控制。
4. 尚未加入完整的錯誤更正碼機制。
5. 不同影片、bitrate、block size、transform type 與係數分布條件下，嵌入穩定性仍需進一步分析。
6. Decode 端目前依賴與 Encode 端完全一致的掃描與篩選規則，若兩端條件不同，可能造成 hidden payload 擷取錯誤。

The current implementation is still in the experimental stage and has the following limitations:

1. The hidden payload is currently read from `data.bin` in the working directory, and command-line payload path selection is not yet supported.
2. The encoder automatically appends `NCU` as the ending keyword, but a payload length header or a more robust synchronization mechanism has not yet been added.
3. Experimental conditions are mainly controlled by manually modifying the source code.
4. Error correction coding has not yet been fully integrated.
5. Embedding stability under different videos, bitrates, block sizes, transform types, and coefficient distributions requires further evaluation.
6. The decoder currently relies on exactly the same scanning and filtering rules as the encoder. If the conditions differ between encoder and decoder, hidden payload extraction may fail.

---

## 8. Notes / 注意事項

- 請確認輸入 YUV 影片解析度與指令中的 height、width 一致。
- 請確認輸入影片格式為 raw YUV。
- 建議將 encoding 與 decoding log 輸出成文字檔，方便後續分析。
- 不同 bitrate 可能會影響嵌入容量、影像品質與資料擷取正確率。
- 若修改 angle mode 或 coefficient value，應同時確認解碼端是否能使用相同規則擷取資料。

Please make sure that the input YUV resolution matches the specified height and width.  
It is also recommended to save encoding and decoding logs for further analysis.

---

## 9. Research Purpose / 研究目的

本專案主要用於 AV1 編碼器中資料隱藏方法之研究，目標包含：

- 提升資料嵌入穩定性
- 降低嵌入後造成的影像品質損失
- 分析不同嵌入條件對 bitrate、PSNR、SSIM、VMAF 與 BD-rate 的影響
- 比較 angle-based 與 coefficient-based data hiding 的特性
- 建立適合 AV1 編碼架構的資料隱藏方法

The purpose of this project is to investigate data hiding methods in the AV1 encoder.  
The main research objectives include improving embedding stability, reducing visual distortion, analyzing rate-distortion performance, and comparing different embedding strategies under the AV1 coding structure.

---

## 10. Related Source Files / 相關程式碼檔案

| Method | Encoder File | Decoder File |
|---|---|---|
| Angle-based data hiding | `encodeframe_utils.c` | `decodemv.c` |
| Coefficient-based data hiding | `encodemb.c` | `decodeframe.c` |

---

## 11. Suggested Future Work / 未來改進方向

未來可進一步加入以下功能：

1. 支援透過 command-line argument 指定 hidden payload file path。
2. 加入錯誤更正碼，提高解碼端資料擷取穩定性。
3. 自動化實驗參數設定，減少手動修改程式碼。
4. 輸出嵌入容量、錯誤率與影像品質分析結果。
5. 支援不同嵌入策略之快速切換。
6. 建立完整的實驗腳本，用於多影片、多 bitrate 與多條件測試。
7. 進一步分析不同 transform type、scan position、qcoeff 範圍與 EOB 條件對影像品質和 payload recovery rate 的影響。

Possible future improvements include supporting command-line payload file selection, adding payload length or synchronization headers, integrating error correction codes, automating experimental parameters, and providing complete evaluation scripts for multiple videos, bitrates, transform types, and embedding conditions.


## 12. 相關參考
1. https://arxiv.org/pdf/2008.06091
2. https://github.com/av1stego/aom
3. https://media.xiph.org/video/derf/