import re
import sys
import csv
from pathlib import Path


def extract_bits(filename, keyword):
    bits = []

    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.search(rf"\b{keyword}\s+([01])\b", line)
            if match:
                bits.append(int(match.group(1)))

    return bits


def compare_files(encode_file, decode_file):
    embedded_bits = extract_bits(encode_file, "embedded")
    extracted_bits = extract_bits(decode_file, "injected")

    embedded_count = len(embedded_bits)
    extracted_count = len(extracted_bits)

    compare_count = min(embedded_count, extracted_count)

    different_bits = 0
    first_mismatch = ""

    for i in range(compare_count):
        if embedded_bits[i] != extracted_bits[i]:
            different_bits += 1

            if first_mismatch == "":
                first_mismatch = i

    # 如果兩邊長度不同，多出/缺少的 bit 也算錯誤
    different_bits += abs(embedded_count - extracted_count)

    ber = (
        different_bits / embedded_count
        if embedded_count > 0
        else 0
    )

    exact_match = (
        embedded_count == extracted_count
        and different_bits == 0
    )

    return {
        "embedded_bits": embedded_count,
        "extracted_bits": extracted_count,
        "different_bits": different_bits,
        "ber": ber,
        "exact_match": "YES" if exact_match else "NO",
        "first_mismatch": first_mismatch,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python compare_all.py <root_folder>")
        print()
        print("Example:")
        print(
            r'  python compare_all.py '
            r'"D:\碩士實驗\testdata\angle_coeff_test\angle_all"'
        )
        sys.exit(1)

    root = Path(sys.argv[1])

    if not root.exists():
        print(f"Folder not found: {root}")
        sys.exit(1)

    # CSV 直接輸出在 root 底下
    output_csv = root / "compare_result.csv"

    results = []

    # 找出所有 encode_*.txt
    for encode_file in sorted(root.rglob("encode_*.txt")):

        folder = encode_file.parent

        # 只找同一 folder 裡面的 decode_*.txt
        decode_files = list(folder.glob("decode_*.txt"))

        # 沒有 decode
        if len(decode_files) == 0:
            results.append({
                "path": str(folder.relative_to(root)),
                "embedded_bits": "",
                "extracted_bits": "",
                "different_bits": "",
                "ber": "",
                "exact_match": "PAIR ERROR",
                "first_mismatch": "",
            })

            print(f"[NO DECODE] {folder}")
            continue

        # 同一 folder 有多個 decode
        if len(decode_files) > 1:
            results.append({
                "path": str(folder.relative_to(root)),
                "embedded_bits": "",
                "extracted_bits": "",
                "different_bits": "",
                "ber": "",
                "exact_match": "PAIR ERROR",
                "first_mismatch": "",
            })

            print(f"[MULTIPLE DECODE] {folder}")
            continue

        decode_file = decode_files[0]

        result = compare_files(
            encode_file,
            decode_file
        )

        results.append({
            "path": str(folder.relative_to(root)),
            "embedded_bits": result["embedded_bits"],
            "extracted_bits": result["extracted_bits"],
            "different_bits": result["different_bits"],
            "ber": f'{result["ber"]:.8f}',
            "exact_match": result["exact_match"],
            "first_mismatch": result["first_mismatch"],
        })

        print(
            f'{result["exact_match"]:3} | '
            f'BER={result["ber"]:.8f} | '
            f'{folder.relative_to(root)}'
        )

    # 輸出 CSV
    with open(
        output_csv,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "embedded_bits",
                "extracted_bits",
                "different_bits",
                "ber",
                "exact_match",
                "first_mismatch",
            ]
        )

        writer.writeheader()
        writer.writerows(results)

    print()
    print("=" * 70)
    print(f"Total folders : {len(results)}")
    print(f"CSV output    : {output_csv}")
    print("=" * 70)


if __name__ == "__main__":
    main()