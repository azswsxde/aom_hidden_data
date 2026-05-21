#include "hidden_data_manager.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static uint8_t *g_payload_bits = NULL;

static size_t g_payload_bits_only = 0;
static size_t g_end_keyword_bits = 0;
static size_t g_total_bits = 0;
static size_t g_bit_index = 0;

static int g_initialized = 0;

/*
 * End keyword:
 * 你原本的：
 * 0, 1, 0, 0, 1, 1, 1, 0,
 * 0, 1, 0, 0, 0, 0, 1, 1,
 * 0, 1, 0, 1, 0, 1, 0, 1
 */
static const int kEndKeywordBits[] = {
  0, 1, 0, 0, 1, 1, 1, 0,
  0, 1, 0, 0, 0, 0, 1, 1,
  0, 1, 0, 1, 0, 1, 0, 1
};

static const size_t kEndKeywordBitCount =
    sizeof(kEndKeywordBits) / sizeof(kEndKeywordBits[0]);

int hidden_data_init(const char *path) {
  FILE *fp = NULL;
  long file_size = 0;
  uint8_t *file_buffer = NULL;

  if (path == NULL) {
    return -1;
  }

  hidden_data_free();

  fp = fopen(path, "rb");
  if (fp == NULL) {
    return -2;
  }

  if (fseek(fp, 0, SEEK_END) != 0) {
    fclose(fp);
    return -3;
  }

  file_size = ftell(fp);
  if (file_size <= 0) {
    fclose(fp);
    return -4;
  }

  if (fseek(fp, 0, SEEK_SET) != 0) {
    fclose(fp);
    return -5;
  }

  file_buffer = (uint8_t *)malloc((size_t)file_size);
  if (file_buffer == NULL) {
    fclose(fp);
    return -6;
  }

  if (fread(file_buffer, 1, (size_t)file_size, fp) != (size_t)file_size) {
    free(file_buffer);
    fclose(fp);
    return -7;
  }

  fclose(fp);

  /*
   * 原始 payload bit 數：
   * 如果 hide data 是二進位檔案，1 byte = 8 bits。
   */
  g_payload_bits_only = (size_t)file_size * 8;
  g_end_keyword_bits = kEndKeywordBitCount;
  g_total_bits = g_payload_bits_only + g_end_keyword_bits;

  /*
   * 這裡直接配置 bit array。
   * 每個元素存一個 bit，值只會是 0 或 1。
   * 好處是 hidden_data_peek_bit() 很簡單，
   * angle 和 coef 不需要知道資料來自檔案還是 end keyword。
   */
  g_payload_bits = (uint8_t *)malloc(g_total_bits);
  if (g_payload_bits == NULL) {
    free(file_buffer);
    hidden_data_free();
    return -8;
  }

  /*
   * 將檔案內容展開成 bit。
   * 這裡使用 MSB first：
   * byte 的第 7 bit 先嵌入，再來第 6 bit ...
   */
  for (size_t i = 0; i < (size_t)file_size; ++i) {
    for (int b = 0; b < 8; ++b) {
      size_t bit_index = i * 8 + b;
      int bit_offset = 7 - b;
      g_payload_bits[bit_index] = (file_buffer[i] >> bit_offset) & 1;
    }
  }

  /*
   * 把 end keyword 接在 payload 後面。
   */
  for (size_t i = 0; i < kEndKeywordBitCount; ++i) {
    g_payload_bits[g_payload_bits_only + i] = (uint8_t)kEndKeywordBits[i];
  }

  free(file_buffer);

  g_bit_index = 0;
  g_initialized = 1;

  return 0;
}

void hidden_data_free(void) {
  if (g_payload_bits != NULL) {
    free(g_payload_bits);
    g_payload_bits = NULL;
  }

  g_payload_bits_only = 0;
  g_end_keyword_bits = 0;
  g_total_bits = 0;
  g_bit_index = 0;
  g_initialized = 0;
}

int hidden_data_has_next_bit(void) {
  if (!g_initialized || g_payload_bits == NULL) {
    return 0;
  }

  return g_bit_index < g_total_bits;
}

int hidden_data_peek_bit(void) {
  if (!hidden_data_has_next_bit()) {
    return -1;
  }

  return g_payload_bits[g_bit_index];
}

int hidden_data_commit_bit(void) {
  if (!hidden_data_has_next_bit()) {
    return -1;
  }

  g_bit_index++;
  return 0;
}

size_t hidden_data_get_bit_index(void) {
  return g_bit_index;
}

size_t hidden_data_get_total_bits(void) {
  return g_total_bits;
}

size_t hidden_data_get_payload_bits(void) {
  return g_payload_bits_only;
}

size_t hidden_data_get_end_keyword_bits(void) {
  return g_end_keyword_bits;
}

int hidden_data_is_finished(void) {
  if (!g_initialized || g_payload_bits == NULL) {
    return 1;
  }

  return g_bit_index >= g_total_bits;
}

// ==============================
// Decoder-side shared end keyword detector
// ==============================

static unsigned int g_decode_keyword_buffer = 0;
static int g_decode_got_end_keyword = 0;
static size_t g_decode_total_bits = 0;
static HiddenDataCarrierType g_decode_last_carrier = HIDDEN_DATA_CARRIER_UNKNOWN;

/*
 * End keyword = "NCU"
 * Binary:
 * N = 01001110
 * C = 01000011
 * U = 01010101
 *
 * Combined 24-bit value:
 * 01001110 01000011 01010101 = 5129045
 */
#define HIDDEN_DATA_END_KEYWORD_VALUE 5129045u
#define HIDDEN_DATA_END_KEYWORD_MASK  0xFFFFFFu
#define HIDDEN_DATA_END_KEYWORD_BITS  24u

void hidden_data_decode_reset(void) {
  g_decode_keyword_buffer = 0;
  g_decode_got_end_keyword = 0;
  g_decode_total_bits = 0;
  g_decode_last_carrier = HIDDEN_DATA_CARRIER_UNKNOWN;
}

int hidden_data_decode_push_bit(int bit_value, HiddenDataCarrierType carrier) {
  if (bit_value != 0 && bit_value != 1) {
    return -1;
  }

  if (g_decode_got_end_keyword) {
    return 1;
  }

  g_decode_keyword_buffer =
      ((g_decode_keyword_buffer << 1) | (unsigned int)bit_value) &
      HIDDEN_DATA_END_KEYWORD_MASK;

  g_decode_total_bits++;
  g_decode_last_carrier = carrier;

  if (g_decode_keyword_buffer == HIDDEN_DATA_END_KEYWORD_VALUE) {
    g_decode_got_end_keyword = 1;
    return 1;
  }

  return 0;
}

int hidden_data_decode_got_end_keyword(void) {
  return g_decode_got_end_keyword;
}

size_t hidden_data_decode_get_total_bits(void) {
  return g_decode_total_bits;
}

size_t hidden_data_decode_get_payload_bits(void) {
  if (g_decode_total_bits < HIDDEN_DATA_END_KEYWORD_BITS) {
    return g_decode_total_bits;
  }

  if (g_decode_got_end_keyword) {
    return g_decode_total_bits - HIDDEN_DATA_END_KEYWORD_BITS;
  }

  return g_decode_total_bits;
}

unsigned int hidden_data_decode_get_keyword_buffer(void) {
  return g_decode_keyword_buffer;
}

HiddenDataCarrierType hidden_data_decode_get_last_carrier(void) {
  return g_decode_last_carrier;
}

unsigned int hidden_data_get_end_keyword_value(void) {
  return HIDDEN_DATA_END_KEYWORD_VALUE;
}

size_t hidden_data_get_end_keyword_bit_count(void) {
  return HIDDEN_DATA_END_KEYWORD_BITS;
}