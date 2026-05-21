#ifndef HIDDEN_DATA_MANAGER_H_
#define HIDDEN_DATA_MANAGER_H_

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ==============================
// Encoder-side payload manager
// ==============================

int hidden_data_init(const char *path);
void hidden_data_free(void);

int hidden_data_has_next_bit(void);
int hidden_data_peek_bit(void);
int hidden_data_commit_bit(void);

size_t hidden_data_get_bit_index(void);
size_t hidden_data_get_total_bits(void);
size_t hidden_data_get_payload_bits(void);
size_t hidden_data_get_end_keyword_bits(void);

int hidden_data_is_finished(void);

// ==============================
// Decoder-side end keyword manager
// angle decode 和 coef decode 共用這一組
// ==============================

typedef enum HiddenDataCarrierType {
  HIDDEN_DATA_CARRIER_UNKNOWN = 0,
  HIDDEN_DATA_CARRIER_ANGLE = 1,
  HIDDEN_DATA_CARRIER_COEF = 2
} HiddenDataCarrierType;

// 初始化解碼端狀態
void hidden_data_decode_reset(void);

// 推入一個解出的 bit。
// bit_value 必須是 0 或 1。
// carrier 用來記錄這個 bit 來自 angle 或 coef。
// 回傳值：
//   0 = 尚未遇到 end keyword
//   1 = 已遇到 end keyword
//  -1 = bit_value 不合法
int hidden_data_decode_push_bit(int bit_value, HiddenDataCarrierType carrier);

// 是否已經偵測到 end keyword
int hidden_data_decode_got_end_keyword(void);

// 取得目前已解出的總 bit 數，包含 end keyword
size_t hidden_data_decode_get_total_bits(void);

// 取得目前已解出的有效 payload bit 數，不包含 end keyword
size_t hidden_data_decode_get_payload_bits(void);

// 取得目前 rolling keyword buffer
unsigned int hidden_data_decode_get_keyword_buffer(void);

// 取得最後一個 bit 是從哪個 carrier 解出來的
HiddenDataCarrierType hidden_data_decode_get_last_carrier(void);

// end keyword 相關資訊
unsigned int hidden_data_get_end_keyword_value(void);
size_t hidden_data_get_end_keyword_bit_count(void);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif  // HIDDEN_DATA_MANAGER_H_