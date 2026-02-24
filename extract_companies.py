# -*- coding: utf-8 -*-
import pandas as pd
import re
import os
from typing import Optional
import shutil
def extract_company_patents(csv_path: str) -> Optional[pd.DataFrame]:
    """
    特許データのCSVファイルから、出願人が企業である特許の情報を抽出します。
    具体的には、「出願人」「発明の名称」「特許ステータス」「公開/登録日」「出願日」を抽出します。

    Args:
        csv_path (str): 読み込むCSVファイルのパス。

    Returns:
        Optional[pd.DataFrame]: 抽出された特許情報を含むDataFrame。
                                カラムは '出願人', '発明の名称', '特許ステータス', '公開/登録日', '出願日'。
                                エラーの場合はNone。
    """
    print(f"'{csv_path}' を読み込んでいます...")
    try:
        # CSVファイルを読み込む
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"エラー: ファイル '{csv_path}' が見つかりません。")
        return None
    except Exception as e:
        print(f"ファイルの読み込み中にエラーが発生しました: {e}")
        return None

    # 必要なカラムが存在するか確認
    required_columns = ['出願人', '発明の名称', '特許ステータス', '公開/登録日', '出願日']
    if not all(col in df.columns for col in required_columns):
        print(f"エラー: CSVファイルに必要なカラム {required_columns} のいずれかが見つかりません。")
        return None

    # 法人を示すキーワードの正規表現パターン
    # 株式会社, 有限会社, 合同会社, 学校法人, 財団法人, 社団法人, またはカタカナが含まれるものを法人と見なす
    company_pattern = re.compile(r'株式会社|有限会社|合同会社|学校法人|財団法人|社団法人|[ァ-ン]')

    # 1. '出願人' が法人パターンにマッチする行をフィルタリング
    filtered_df = df[df['出願人'].astype(str).str.contains(company_pattern, na=False)].copy()

    # 2. 特許ステータスが「登録」または「公開」のもののみを抽出
    status_keywords = ['登録', '公開']
    filtered_df = filtered_df[filtered_df['特許ステータス'].str.contains('|'.join(status_keywords), na=False)]

    # 必要なカラムのみを選択
    return filtered_df[required_columns]

def process_csv_file(input_csv_path: str):
    """指定されたCSVファイルを処理し、有効特許と申請中特許のDataFrameを返す"""
    print(f"\n{'='*20}\n処理開始: {input_csv_path}\n{'='*20}")
    # 入力ファイル名からベース名を取得 (例: 水耕栽培2_data)
    input_basename = os.path.splitext(os.path.basename(input_csv_path))[0]
    patents_df = extract_company_patents(input_csv_path)

    if patents_df is not None and not patents_df.empty:
        print(f"\n抽出された特許の総数: {len(patents_df)}件")

        # 「有効な特許」（ステータスに「登録」を含む）
        active_df = patents_df[patents_df['特許ステータス'].str.contains('登録', na=False)].copy()
        # 「申請中の特許」（ステータスに「公開」を含む）
        pending_df = patents_df[patents_df['特許ステータス'].str.contains('公開', na=False)].copy()

        # どのファイル由来かを示す列を追加
        if not active_df.empty:
            active_df['source_file'] = input_basename
        if not pending_df.empty:
            pending_df['source_file'] = input_basename

        return active_df, pending_df

    else:
        print(f"{input_basename}: 対象となる企業の特許は見つかりませんでした。")
        return pd.DataFrame(), pd.DataFrame()

def save_combined_results(df: pd.DataFrame, status_name: str, base_dir: str):
    """結合された結果をCSVとTXTに保存する関数"""
    if df.empty:
        print(f"\n--- {status_name}の特許は見つかりませんでした ---")
        return

    print(f"\n--- 全ての{status_name}の特許 ({len(df)}件) をファイルに保存します ---")
    # ファイル名を 'all_patents_有効.csv' のように変更
    output_csv = os.path.join(base_dir, f'all_patents_{status_name.lower()}.csv')
    output_txt = os.path.join(base_dir, f'all_patents_{status_name.lower()}.txt')

    try:
        # 1. CSVファイルに出力
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"  - 結合結果をCSVファイルに出力しました: {output_csv}")

        # 2. TXTファイルに出力
        with open(output_txt, 'w', encoding='utf-8') as f:
            f.write(f"--- {status_name}の特許一覧 (合計: {len(df)}件) ---\n\n")
            # ソースファイルごとにグループ化して出力
            for source_file, group in df.groupby('source_file'):
                f.write(f"▼▼▼ ソース: {source_file} ({len(group)}件) ▼▼▼\n")
                # インデックスをリセットして連番を振る
                group = group.reset_index(drop=True)
                for idx, row in group.iterrows():
                    f.write(f"[{idx + 1}]\n")
                    f.write(f"  企業名       : {row['出願人']}\n")
                    f.write(f"  発明の名称   : {row['発明の名称']}\n")
                    f.write(f"  公開/登録日  : {row['公開/登録日']}\n")
                    f.write(f"  出願日       : {row['出願日']}\n")
                    f.write(f"  特許ステータス: {row['特許ステータス']}\n")
                    f.write("-" * 20 + "\n")
                f.write("\n")
        print(f"  - 結合結果をTXTファイルに出力しました: {output_txt}")

    except Exception as e:
        print(f"{status_name}の特許のファイル書き込み中にエラーが発生しました: {e}")

if __name__ == '__main__':
    INPUT_DIR = r'D:\python\j-plat-pat\patent\patent_api\data'
    OUTPUT_DIR = r'D:\python\j-plat-pat\patent\patent_api\output'

    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 全てのファイルの結果を保存するリスト
    all_active_patents = []
    all_pending_patents = []

    # 入力ディレクトリ内のすべてのCSVファイルに対して処理を実行
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith('.csv'):
            input_csv_path = os.path.join(INPUT_DIR, filename)
            active_df, pending_df = process_csv_file(input_csv_path)
            if not active_df.empty:
                all_active_patents.append(active_df)
            if not pending_df.empty:
                all_pending_patents.append(pending_df)

    # リストに格納されたDataFrameを結合
    if all_active_patents:
        combined_active_df = pd.concat(all_active_patents, ignore_index=True)
        save_combined_results(combined_active_df, "有効", OUTPUT_DIR)

    if all_pending_patents:
        combined_pending_df = pd.concat(all_pending_patents, ignore_index=True)
        save_combined_results(combined_pending_df, "申請中", OUTPUT_DIR)

    print(f"\n{'='*20}\nすべての処理が完了しました。\n{'='*20}")
