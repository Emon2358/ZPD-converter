import struct
import wave
import sys
import os
import argparse
import glob

class OkiAdpcmDecoder:
    """OKI MSM6258 ADPCM Decoder Class"""
    def __init__(self):
        self.step_index = 0
        self.predicted_sample = 0
        self.step_size_table = [
            16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
            73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
            279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876,
            963, 1060, 1166, 1282, 1411, 1552
        ]
        self.index_table = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]

    def decode_nibble(self, nibble):
        step_size = self.step_size_table[self.step_index]
        self.step_index += self.index_table[nibble]
        if self.step_index < 0: self.step_index = 0
        elif self.step_index > 48: self.step_index = 48

        diff = step_size >> 3
        if nibble & 4: diff += step_size
        if nibble & 2: diff += step_size >> 1
        if nibble & 1: diff += step_size >> 2

        if nibble & 8: self.predicted_sample -= diff
        else: self.predicted_sample += diff

        # Clip to 12-bit
        if self.predicted_sample > 2047: self.predicted_sample = 2047
        elif self.predicted_sample < -2048: self.predicted_sample = -2048

        return self.predicted_sample << 4

def convert_file(input_path, output_path, sample_rate):
    try:
        # ファイルサイズチェック
        if os.path.getsize(input_path) == 0:
            print(f"[SKIP] 空のファイルです: {input_path}")
            return False

        with open(input_path, 'rb') as f:
            raw_data = f.read()
            
    except Exception as e:
        print(f"[ERROR] 読み込み失敗: {input_path} -> {e}")
        return False

    # --- ヘッダー判定ロジック ---
    start_offset = 0
    header_signature = b'ZmAdpCm'
    
    # 最初の数バイトを確認
    if raw_data.startswith(header_signature):
        # 標準的なZ-MUSICヘッダーがある場合
        start_offset = 32
        print(f"[INFO] Header detected (Z-MUSIC): {os.path.basename(input_path)}")
    else:
        # ヘッダーがない場合はRawデータとみなす
        start_offset = 0
        print(f"[INFO] No Header (Assuming Raw): {os.path.basename(input_path)}")

    adpcm_data = raw_data[start_offset:]
    
    if len(adpcm_data) == 0:
        print(f"[SKIP] データ部がありません: {input_path}")
        return False

    decoder = OkiAdpcmDecoder()
    pcm_samples = []

    # デコード処理
    for byte in adpcm_data:
        high = (byte >> 4) & 0x0F
        low = byte & 0x0F
        try:
            pcm_samples.append(struct.pack('<h', decoder.decode_nibble(high)))
            pcm_samples.append(struct.pack('<h', decoder.decode_nibble(low)))
        except Exception as e:
            print(f"[WARN] デコード中にエラー発生 (一部欠損の可能性): {e}")
            break

    # WAV書き出し
    try:
        with wave.open(output_path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b''.join(pcm_samples))
        return True
    except Exception as e:
        print(f"[ERROR] 書き込み失敗: {output_path} -> {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="X68000 ZPD to WAV Batch Converter")
    parser.add_argument('--input_dir', default='./zpd_files', help='Input directory')
    parser.add_argument('--output_dir', default='./output_wavs', help='Output directory')
    parser.add_argument('--rate', type=int, default=15625, help='Sampling rate (default: 15625)')
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # globを使って安全にファイルリストを取得（特殊文字を含むファイル名もここで吸収）
    # 大文字小文字の拡張子に対応
    pattern = os.path.join(args.input_dir, '*.[zZ][pP][dD]')
    files = glob.glob(pattern)
    
    if not files:
        print(f"警告: '{args.input_dir}' にZPDファイルが見つかりません。")
        return

    print(f"--- 変換開始: 対象 {len(files)} ファイル ---")
    
    success_count = 0
    for file_path in files:
        # ファイル名取得（ディレクトリ除く）
        file_name = os.path.basename(file_path)
        # 拡張子を除去して .wav を付与
        base_name, _ = os.path.splitext(file_name)
        output_path = os.path.join(args.output_dir, base_name + ".wav")
        
        if convert_file(file_path, output_path, args.rate):
            print(f"[OK] {file_name} -> {os.path.basename(output_path)}")
            success_count += 1
        else:
            print(f"[FAIL] {file_name}")

    print(f"--- 完了: {success_count}/{len(files)} 成功 ---")

if __name__ == "__main__":
    main()
