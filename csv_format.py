import pandas as pd
from sqlalchemy import create_engine, exc
import os
import csv # ★ csvモジュールをインポート
import re
import unicodedata # Unicodeデータを扱うためのライブラリをインポート


# --- MySQLデータベースの接続情報 ---
# ご自身の環境に合わせて変更してください
DB_USER = "root"
DB_PASSWORD = "mamhidet_mysql"  # MySQLのパスワード
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "patent_db" # データベース名

# 出力するCSVファイルのパス
OUTPUT_CSV = "patents_mysql_export.csv"

def clean_text(text):
    """
    考えられるほぼ全ての特殊文字や制御文字を網羅的に処理する、非常に強力なクリーニング関数
    """
    if not isinstance(text, str):
        return text

    # Unicode正規化（NFKD）を行い、互換文字を基本文字に分解
    # 例：「①」->「1」, 「㈱」->「(株)」
    try:
        normalized_text = unicodedata.normalize('NFKD', text)
    except TypeError:
        return text # 予期せぬデータ型の場合

    cleaned_chars = []
    for char in normalized_text:
        cat = unicodedata.category(char)
        # ================================================================
        # ★★★ ここが最も重要な修正点 ★★★
        # Unicodeカテゴリに基づいて、より網羅的に文字を処理します
        # ================================================================

        # 1. 制御文字(Cc, Cf, Cs, Co, Cn)は完全に除去
        if cat.startswith('C'):
            continue
        # 2. 区切り文字(Zs, Zl, Zp)はすべて標準的な半角スペースに置換
        elif cat.startswith('Z'):
            cleaned_chars.append(' ')
        # 3. それ以外の文字（通常の文字、数字、記号など）はそのまま保持
        else:
            cleaned_chars.append(char)
            
    text = "".join(cleaned_chars)
    
    # 複数のスペースが連続している場合、1つにまとめる
    text = re.sub(r' +', ' ', text)
    
    # 処理後に文頭や文末に不要なスペースが残る場合があるので除去
    return text.strip()

def export_mysql_to_csv():
    """
    MySQLデータベースから特許データを読み込み、クリーンなCSVファイルに出力します。
    """
    db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    print(f"{DB_HOST} 上の '{DB_NAME}' データベースに接続しています...")
    
    try:
        engine = create_engine(db_url)
        df = pd.read_sql("SELECT * FROM patents", engine)
        print(f"{len(df)} 件のデータを読み込みました。")

        # カラム名をサニタイズ
        sanitized_columns = [str(col).strip().replace('\r', '').replace('\n', '') for col in df.columns]
        df.columns = sanitized_columns

        # データ内の特殊文字を網羅的に処理
        print("データ内の特殊文字を強力な方法で処理しています...")
        string_columns = df.select_dtypes(include=['object']).columns
        
        for col in string_columns:
            df[col] = df[col].fillna('').astype(str).apply(clean_text)

        print("特殊文字の処理が完了しました。")

        # Python標準のcsvモジュールを使用して書き出し
        print("csvモジュールを使ってファイルに書き込んでいます...")
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\n')
            writer.writerow(df.columns)
            writer.writerows(df.values)

        print(f"データのエクスポートが完了しました: {OUTPUT_CSV}")

    except exc.OperationalError as e:
        print(f"エラー: データベースに接続できませんでした。接続情報が正しいか確認してください。")
        print(f"詳細: {e}")
    except Exception as e:
        print(f"データのエクスポート中にエラーが発生しました: {e}")

if __name__ == "__main__":
    export_mysql_to_csv()
