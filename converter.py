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

        if self.predicted_sample > 2047: self.predicted_sample = 2047
        elif self.predicted_sample < -2048: self.predicted_sample = -2048

        return self.predicted_sample << 4

def convert_file(input_path, output_path, sample_rate):
    try:
        with open(input_path, 'rb') as f:
            raw_data = f.read()
    except Exception as e:
        print(f"[ERROR] 読み込み失敗: {input_path} -> {e}")
        return False

    # ヘッダー検出とスキップ処理 (Z-MUSIC "ZmAdpCm")
    start_offset = 0
    if raw_data.startswith(b'ZmAdpCm'):
        # 固定32バイトスキップ (多くのZPDで有効)
        start_offset = 32
    
    adpcm_data = raw_data[start_offset:]
    decoder = OkiAdpcmDecoder()
    pcm_samples = []

    for byte in adpcm_data:
        high = (byte >> 4) & 0x0F
        low = byte & 0x0F
        pcm_samples.append(struct.pack('<h', decoder.decode_nibble(high)))
        pcm_samples.append(struct.pack('<h', decoder.decode_nibble(low)))

    try:
        with wave.open(output_path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b''.join(pcm_samples))
        print(f"[OK] 変換完了: {output_path}")
        return True
    except Exception as e:
        print(f"[ERROR] 書き込み失敗: {output_path} -> {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="X68000 ZPD to WAV Batch Converter")
    parser.add_argument('--input_dir', default='./zpd_files', help='Input directory containing .ZPD files')
    parser.add_argument('--output_dir', default='./output_wavs', help='Output directory for .wav files')
    parser.add_argument('--rate', type=int, default=15625, help='Sampling rate (default: 15625)')
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # 大文字小文字を区別せずZPDファイルを検索
    files = glob.glob(os.path.join(args.input_dir, '*.[zZ][pP][dD]'))
    
    if not files:
        print(f"警告: '{args.input_dir}' にZPDファイルが見つかりません。")
        return

    print(f"--- 変換開始: {len(files)} ファイル ---")
    for file_path in files:
        file_name = os.path.basename(file_path)
        base_name, _ = os.path.splitext(file_name)
        output_path = os.path.join(args.output_dir, base_name + ".wav")
        convert_file(file_path, output_path, args.rate)
    print("--- 全処理終了 ---")

if __name__ == "__main__":
    main()
