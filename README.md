# 教學
## 編譯
git clone https://github.com/azswsxde/aom_hidden_data
make aom_build
cd aom_build
cmake path/to/aom_hidden_data
make
## 使用
./simple_encoder_mark av1 (video height) (video width) (yuv file path with name) (output avif path with name) (fps) 0 (total_frame) (bitrate)

./simple_decoder_mark (avif path with name) (out yuv file path with name)

example
```
./simple_encoder_mark av1 1280 720 /home/mark/500GB/testdata/VIRAT.yuv VIRAT_offset0_padding0_hidden_all_y_plane_only.avif  30 0 150 8192 > ~/paper/encode.txt
./simple_decoder_mark VIRAT_offset0_padding0_hidden_all_y_plane_only.avif VIRAT_offset0_padding0_hidden_all_y_plane_only.yuv > ~/paper/decode.txt
```

# 介紹
可以自行打開或關閉程式碼來測試不同的項目
目前資料還沒從外部資料讀取，先固定4bit不停repeat


angle hide
encode embed file - encodeframe_utils.c
decode embed file - decodemv.c

coeff hide
encode embed file - encodemb.c
decode embed file - decodeframe.c
