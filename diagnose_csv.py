import pandas as pd
import unicodedata
from collections import defaultdict
import os

# --- ★★★ 入力ファイル名 ★★★ ---
# 診断したいCSVファイルの名前を指定してください
INPUT_CSV_FILE = "patents_mysql_export.csv"

# 問題が見つかった場合に表示する最大報告数
MAX_REPORTS = 50

# ★★★ 出力ファイル名 ★★★
OUTPUT_REPORT_FILE = "diagnose_report.txt"

def full_diagnose_from_csv():
    """CSVファイルを直接スキャンし、問題のある特殊文字をすべてリストアップし、ファイルに出力します。"""
    
    unique_problem_chars = set()
    report_count = 0

    if not os.path.exists(INPUT_CSV_FILE):
        print(f"エラー: 入力ファイル '{INPUT_CSV_FILE}' が見つかりません。ファイル名が正しいか確認してください。")
        return

    # 'with'ステートメントでレポートファイルを開き、処理が終わったら自動で閉じる
    with open(OUTPUT_REPORT_FILE, 'w', encoding='utf-8') as f:
        
        def log_to_file_and_console(message, is_console_only=False):
            """コンソールとファイルの両方に出力するヘルパー関数"""
            print(message)
            if not is_console_only:
                f.write(message + '\n')

        try:
            log_to_file_and_console(f"CSVファイル '{INPUT_CSV_FILE}' を読み込んでいます...", is_console_only=True)
            # CSVを読み込む際、すべての列を文字列として扱う(dtype=str)
            # これにより、pandasによる自動的なデータ型変換を防ぎ、生のデータをチェックできる
            # keep_default_na=False は、'NA'などの文字列が欠損値として扱われるのを防ぐ
            df = pd.read_csv(INPUT_CSV_FILE, dtype=str, keep_default_na=False)
            log_to_file_and_console(f"{len(df)} 件のデータをスキャンします。", is_console_only=True)

            log_to_file_and_console("\n" + "="*60)
            log_to_file_and_console("  データ全体の診断を開始します...")
            log_to_file_and_console("="*60)
            
            for index, row in df.iterrows():
                # CSVの行番号はヘッダー(1) + 0-indexedの行数 + 1
                csv_row_num = index + 2
                
                for column in df.columns:
                    value = row[column]
                    if not value: # valueが空文字列の場合はスキップ
                        continue

                    for char_index, char in enumerate(value):
                        cat = unicodedata.category(char)
                        is_problematic = (
                            cat.startswith('C') or 
                            (cat == 'Zs' and char != ' ') or 
                            cat in ['Zl', 'Zp']
                        )
                        
                        if is_problematic:
                            unique_problem_chars.add(char)
                            
                            if report_count < MAX_REPORTS:
                                report_count += 1
                                try:
                                    char_name = unicodedata.name(char)
                                except ValueError:
                                    char_name = "名前なし"
                                
                                report_message = f"[{report_count:02d}] 問題を発見: CSV行={csv_row_num}, カラム='{column}', 文字='{char}' (repr: {char!r}), カテゴリ: {cat} ({char_name})"
                                log_to_file_and_console(report_message)

            log_to_file_and_console("\n" + "="*60)
            log_to_file_and_console("  診断完了: サマリーレポート")
            log_to_file_and_console("="*60)
            
            if not unique_problem_chars:
                log_to_file_and_console("おめでとうございます！問題となる可能性のある特殊文字は見つかりませんでした。")
            else:
                log_to_file_and_console(f"データ全体から {len(unique_problem_chars)} 種類の問題となる可能性のある文字が見つかりました。")
                log_to_file_and_console("これらの文字をエクスポートスクリプトで除去する必要があります。")
                log_to_file_and_console("\n--- 発見されたユニークな問題文字リスト ---")
                for char in sorted(list(unique_problem_chars)):
                    try:
                        name = unicodedata.name(char)
                    except ValueError:
                        name = "名前なし"
                    cat = unicodedata.category(char)
                    char_info = f"  - 文字: '{char}' (repr: {char!r}), カテゴリ: {cat} ({name})"
                    log_to_file_and_console(char_info)
                log_to_file_and_console("------------------------------------------")
            
            log_to_file_and_console(f"\n診断レポートが {OUTPUT_REPORT_FILE} に保存されました。", is_console_only=True)

        except FileNotFoundError:
            error_message = f"エラー: 入力ファイル '{INPUT_CSV_FILE}' が見つかりませんでした。"
            log_to_file_and_console(error_message)
        except Exception as e:
            error_message = f"処理中にエラーが発生しました: {e}"
            log_to_file_and_console(error_message)

if __name__ == "__main__":
    full_diagnose_from_csv()

