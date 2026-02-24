# -*- coding: utf-8 -*-

#  python .\data_analyzed.py .\乳酸菌_data.csv test.csv

import pandas as pd
import re
from datetime import date
import ast
from transformers import pipeline
from janome.tokenizer import Tokenizer
import os
import argparse # コマンドライン引数を扱うためのライブラリをインポート

# --- Hugging FaceのNERモデルとJanomeを読み込み ---
print("Hugging FaceのNERモデルをローカルから読み込んでいます...")
try:
    model_path = "./local-bert-ner"
    if not os.path.isdir(model_path):
        print(f"エラー: モデルフォルダ '{model_path}' が見つかりません。")
        print("手動でダウンロードしたモデルファイルがこのフォルダに正しく配置されているか確認してください。")
        exit()
    ner_pipeline = pipeline("ner", model=model_path, tokenizer=model_path)
    print("モデルの読み込みに成功しました。")
except Exception as e:
    print(f"モデルの読み込み中にエラーが発生しました: {e}")
    print(f"'{model_path}' フォルダに必要なファイル（config.json, pytorch_model.binなど）が揃っているか確認してください。")
    exit()

print("Janome（形態素解析器）を読み込んでいます...")
t = Tokenizer()


def group_entities(entities):
    """
    Hugging FaceのNER結果をグループ化する関数
    """
    if not entities:
        return []
    grouped = []
    current_entity = {"text": "", "label": ""}
    for ent in entities:
        entity_label = ent['entity']
        word = ent['word'].replace("##", "")
        simple_label = entity_label.split('-')[-1]
        if entity_label.startswith('B-') or current_entity["label"] != simple_label:
            if current_entity["text"]:
                grouped.append(current_entity)
            current_entity = {"text": word, "label": simple_label}
        else:
            current_entity["text"] += word
    if current_entity["text"]:
        grouped.append(current_entity)
    return grouped


def convert_wareki_to_date(wareki_str):
    """
    和暦文字列をdatetime.dateオブジェクトに変換する関数
    """
    if not isinstance(wareki_str, str) or not any(era in wareki_str for era in ["令和", "平成", "昭和", "大正", "明治"]):
        return None
    era_starts = {"令和": 2018, "平成": 1988, "昭和": 1925, "大正": 1911, "明治": 1867}
    try:
        for era, start_year_minus_one in era_starts.items():
            if wareki_str.startswith(era):
                parts = wareki_str[len(era):].replace('元年', '1年')
                numbers = re.findall(r'\d+', parts)
                if len(numbers) == 3:
                    wareki_year, month, day = map(int, numbers)
                    western_year = start_year_minus_one + wareki_year
                    return date(western_year, month, day)
        return None
    except (ValueError, IndexError):
        return None

def analyze_patent_data(input_csv_path, output_csv_path):
    """
    特許データCSVを読み込み、NERと特徴量エンジニアリングを行う関数
    """
    print(f"'{input_csv_path}' を読み込んでいます...")
    try:
        # 文字コードのエラーを防ぐために encoding を指定
        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"エラー: ファイル '{input_csv_path}' が見つかりません。パスが正しいか確認してください。")
        return
    except Exception as e:
        print(f"ファイルの読み込み中に予期せぬエラーが発生しました: {e}")
        return

    # --- 1. データの前処理 ---
    print("データの前処理を開始します...")
    # ★ 修正点: カラム名を '発明者/考案者' から '発明者' に変更
    if '発明者' not in df.columns:
        print("エラー: '発明者' 列がCSVファイルに存在しません。")
        return
        
    df['公開/登録日_西暦'] = df['公開/登録日'].apply(convert_wareki_to_date)
    df['出願日_西暦'] = df['出願日'].apply(convert_wareki_to_date)
    # ★ 修正点: カラム名を '発明者/考案者' から '発明者' に変更
    df['発明者_リスト'] = df['発明者'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else [])

    # --- 2. Hugging Faceのモデルで固有名詞抽出 (NER) ---
    print("固有名詞抽出（NER）のサンプルを実行します...")
    sample_text = df['要約_解決手段'].iloc[0] if pd.notna(df['要約_解決手段'].iloc[0]) else ""
    
    raw_entities = ner_pipeline(sample_text)
    grouped_entities = group_entities(raw_entities)
    
    print("\n--- NER抽出結果 (最初の行の要約_解決手段) ---")
    if grouped_entities:
        for ent in grouped_entities:
            print(f"  - {ent['text']} ({ent['label']})")
    else:
        print("  - 固有名詞は見つかりませんでした。")
    print("----------------------------------------\n")

    # --- 3. 特徴量エンジニアリング ---
    print("特徴量エンジニアリングを開始します...")

    df['公開/登録日_西暦'] = pd.to_datetime(df['公開/登録日_西暦'], errors='coerce')
    df['出願日_西暦'] = pd.to_datetime(df['出願日_西暦'], errors='coerce')
    df['出願から公開までの日数'] = (df['公開/登録日_西暦'] - df['出願日_西暦']).dt.days
    df['出願年'] = df['出願日_西暦'].dt.year
    df['出願月'] = df['出願日_西暦'].dt.month

    df['要約_課題_文字数'] = df['要約_課題'].str.len()
    df['要約_解決手段_文字数'] = df['要約_解決手段'].str.len()

    def count_nouns(text):
        if not isinstance(text, str):
            return 0
        return len([token for token in t.tokenize(text) if token.part_of_speech.startswith('名詞')])

    print("要約から名詞の数をカウントしています...")
    # ★ 修正点: '発明の名称' も分析対象に含める
    df['要約_名詞数'] = (df['発明の名称'].fillna('') + " " + df['要約_課題'].fillna('') + " " + df['要約_解決手段'].fillna('')).apply(count_nouns)

    df['発明者数'] = df['発明者_リスト'].apply(len)
    # ★ 修正点: カラム名を '出願人/特許権者' から '出願人' に変更
    df['出願人_法人フラグ'] = df['出願人'].str.contains(
        '株式会社|有限会社|合同会社|学校法人|財団法人|社団法人|[ァ-ン]', na=False
    ).astype(int)

    print(f"特徴量エンジニアリングが完了しました。'{output_csv_path}' に結果を保存します。")
    
    df_to_save = df.drop(columns=['発明者_リスト'])
    df_to_save.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print("完了しました。")
    print("\n生成された特徴量の最初の5行:")
    print(df_to_save.head())

# コマンドラインからファイルパスを受け取るように変更
if __name__ == '__main__':
    # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(description='特許データCSVを分析し、特徴量を追加して新しいCSVファイルとして出力します。')
    
    # 入力ファイルの引数を定義
    parser.add_argument('input_file', type=str, help='入力するCSVファイルのパス (例: 水耕栽培_data.csv)')
    
    # 出力ファイルの引数を定義
    parser.add_argument('output_file', type=str, help='出力するCSVファイルのパス (例: analyzed_data.csv)')
    
    # 引数をパース
    args = parser.parse_args()
    
    # 関数を実行
    analyze_patent_data(args.input_file, args.output_file)

