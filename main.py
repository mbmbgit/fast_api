# 必要なライブラリをインポート
import pandas as pd
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import re
import json
# D:/python/.venv/Scripts/Activate.ps1
def extract_patent_info(text):
    """
    特許公報のテキストから正規表現を使って情報を抽出する関数。

    Args:
        text (str): 特許公報のテキストデータ。

    Returns:
        dict: 抽出した情報を格納した辞書。
    """
    
    # re.search() を安全に実行し、結果を返すヘルパー関数
    def safe_search(pattern, string):
        match = re.search(pattern, string)
        # マッチすればキャプチャしたグループ(1)を、しなければ '抽出不可' を返す
        return match.group(1).strip() if match else "抽出不可"

    # 抽出する情報を格納する辞書
    patent_data = {}

    # 各項目を正規表現で抽出
    # 辞書のキーも、どちらが取得されるか分かるように変更すると、より親切です
    patent_data["公開/特許番号"] = safe_search(r"(?:【公開番号】|【特許番号】|【登録日】|【公表番号】)(.*?)\(", text)
    patent_data["公開/登録日"] = safe_search(r"(?:【公開日】|【登録日】|【公表日】)(.*?)\(", text)
    # patent_data["発明の名称"] = safe_search(r"【発明の名称】|【考案の名称】(.*)", text)
    patent_data["発明/考案の名称"] = safe_search(r"(?:【発明の名称】|【考案の名称】)(.*)", text)
    patent_data["出願番号"] = safe_search(r"【出願番号】(.*?)\(", text)
    patent_data["出願日"] = safe_search(r"【出願日】(.*?)\(", text)
    
    # (71)出願人ブロックから氏名または名称を抽出
    # 変更点: テキスト全体からすべての「【氏名又は名称】」をリストとして抽出する
    # re.findallは、マッチしたすべての文字列をリストで返す
    all_names = re.findall(r"【氏名又は名称】|【氏名】(.*)", text)
    
    # 抽出した各名前の前後の空白を削除し、結果を格納する
    # 発明者と同様に、キーの名前をリストであることが分かるように変更
    # (71)【出願人】ブロックから【氏名又は名称】を抽出
    patent_data["出願人・代理人リスト"] = safe_search(r"(?:\(71\)【出願人】|\(73\)【特許権者】|\(73\)【実用新案権者】)[\s\S]*?【氏名又は名称】(.*)", text)
    # patent_data["出願人・代理人リスト"] = [name.strip() for name in all_names] if all_names else ["抽出不可"]

    # (72)発明者は複数存在する可能性があるため、findallですべて取得
    # \s* は、氏名の前にある可能性のある空白や改行にマッチさせる
    inventors = re.findall(r"【発明者】|【考案者】\s*【氏名】(.*)", text)
    patent_data["発明者"] = [name.strip() for name in inventors] if inventors else ["抽出不可"]

    # (57)要約ブロックから課題と解決手段を抽出
    abstract_pattern = r"(?:\(([^)]*)\))?【要約】([\s\S]*)"
    abstract_match = re.search(abstract_pattern, text)
    if abstract_match:
        abstract_block = abstract_match.group(2)
        patent_data["要約_課題"] = safe_search(r"【課題】(.*)", abstract_block)
        # 解決手段は複数行にわたるため、re.DOTALLフラグも考慮
        solution_match = re.search(r"【解決手段】(.*)", abstract_block, re.DOTALL)
        if solution_match:
            # 不要な空白や改行を整理
            patent_data["要約_解決手段"] = ' '.join(solution_match.group(1).strip().split())
        else:
            patent_data["要約_解決手段"] = "抽出不可"
    else:
        patent_data["要約_課題"] = "抽出不可"
        patent_data["要約_解決手段"] = "抽出不可"

    return patent_data

print("--- スクリプトを開始します ---")

# --- 1. Selenium WebDriverの設定 ---
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # ブラウザを非表示で実行したい場合はこの行を有効化
options.add_argument("--start-maximized") # ウィンドウを最大化
options.page_load_strategy = 'normal'
# User-Agentを設定してボット検出を回避
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')
options.add_experimental_option("excludeSwitches", ["enable-automation"])

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 130) # 要素が見つかるまでの最大待機時間を15秒に設定

# --- 2. J-PlatPatにアクセスして検索 ---
url = "https://www.j-platpat.inpit.go.jp/"
search_text = "機械学習"
master_list = []
# ☑釣り　☑水耕栽培　エンジン　タイヤ　☑乳酸菌　IoT 道路　物流　倉庫　NEC 富士通　さくらインターネット　エヌビディア　グーグル　マイクロソフト　アマゾン
#任天堂　ソニー　ポケモン　サンリオ　バンダイナムコ　サイバーエージェント　KADOKAWA ウォルト・ディズニー　東映　東宝　講談社　集英社　カバー　ANYCOLOR
print(f"'{url}' にアクセスしています...")
driver.get(url)

# 検索キーワードを入力
search_box_id = "s01_srchCondtn_txtSimpleSearch"
wait.until(EC.visibility_of_element_located((By.ID, search_box_id)))
text_box = driver.find_element(By.ID, search_box_id)
text_box.send_keys(search_text)
print(f"検索キーワード '{search_text}' を入力しました。")

# 検索ボタンをクリック
search_btn_id = "s01_srchBtn_btnSearch"
search_btn = driver.find_element(By.ID, search_btn_id)
search_btn.click()
print("検索ボタンをクリックしました。結果ページを待機中...")

# 検索結果が表示されるまで待機
wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='patentUtltyIntnlSimpleBibLst']")))
print("検索結果ページが表示されました。")

# --- 3. ページ最下部までスクロールして全件表示 ---
print("全件表示のため、ページをスクロールします...")
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1) # 新しいコンテンツが読み込まれるのを待つ
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        print("ページの最下部に到達しました。")
        break
    last_height = new_height

# --- 4. 各特許情報をループで取得 ---
# 検索結果の全アイテムを取得
patent_items = driver.find_elements(By.XPATH, "//*[@id='patentUtltyIntnlSimpleBibLst_tableView_docNumArea']")
print(f"合計 {len(patent_items)} 件の特許情報を取得します。")

original_window = driver.current_window_handle

for i, item in enumerate(patent_items):
    
    # 「特開」リンクを探す
    try:
      target_link = item.find_element(By.CLASS_NAME, "ng-star-inserted")
    except:
      target_link = item.find_element(By.CLASS_NAME, "linetable-format-column")
    # Ctrl+クリックで新しいタブで開く
    target_link.send_keys(Keys.CONTROL + Keys.RETURN)
    time.sleep(2) # 新しいタブが開くのを待つ
    
    # 新しいタブに切り替え
    new_tab = [window for window in driver.window_handles if window != original_window][0]
    driver.switch_to.window(new_tab)
    time.sleep(2)

    
    # --- 5. 新しいタブからデータを取得 ---
    # 全体のテキスト
    text_id = "//*[@id='result_content']"

    #特許のステータス
    try:
        pretent_status = driver.find_element(By.XPATH,'//*[@id="p0201_docuTitleArea_lblReferenceNumberTitle"]').text
        
        print(pretent_status)
    except:
        pretent_status = "抽出不可"
    #result_content > div
    #result_content
    try:
        detail = wait.until(EC.presence_of_element_located((By.XPATH, text_id))).text.strip()
    except:
        detail = ' '
    data = extract_patent_info(detail)
    

    # 取得したデータをリストに追加
    individual_data = {
          "公開/特許番号":data["公開/特許番号"],
          "公開/登録日":data["公開/登録日"],
          "発明の名称":data["発明/考案の名称"],

          "出願番号":data["出願番号"],

          "出願日":data["出願日"],

          "出願人":data["出願人・代理人リスト"],

          "発明者":data["発明者"],

          "要約_課題":data["要約_課題"],

          "要約_解決手段":data["要約_解決手段"],

          "特許ステータス":pretent_status
        
    }
    master_list.append(individual_data)
    
    print(f"[{i+1}/{len(patent_items)}] 取得完了: {data['発明/考案の名称']}...")
    
    # タブを閉じて元のタブに戻る
    driver.close()
    driver.switch_to.window(original_window)
    time.sleep(1)

    

# --- 6. データをDataFrameに変換し、CSVに出力 ---
# master_list が空でない場合のみ実行
if master_list:
    df = pd.DataFrame(master_list)

    # ★ 2. 出力先のディレクトリパスとファイル名を指定
    output_directory = r'D:\python\j-plat-pat\patent\patent_api\data'
    csv_filename = f'{search_text}_data.csv'

    # ★ 3. ディレクトリが存在しない場合に作成 (任意ですが推奨)
    os.makedirs(output_directory, exist_ok=True)

    # ★ 4. 完全なファイルパスを作成
    full_path = os.path.join(output_directory, csv_filename)

    # ★ 5. df.to_csv に完全なパスを指定
    df.to_csv(full_path, index=False, encoding='utf-8-sig')

    # ★ 6. 出力メッセージもフルパスを表示するように変更
    print(f"\nデータフレームを作成し、'{full_path}' に出力しました。")

else:
    print("\n取得できたデータがありませんでした。CSVファイルは出力されません。")



# finally:
#     # --- 7. ブラウザを閉じる ---
#     driver.quit()
#     print("--- スクリプトを終了します ---")

  ##オプションでAIでカテゴリ分け
#   Groq	LLaMA 3.1 8B/70Bなどのモデルを超高速なLPU（Learning Processing Unit）で提供。無料利用枠で1日あたりのリクエスト数や1分あたりのトークン制限が設けられていますが、非常に高速で性能も高いため、人気があります。
# OpenRouter	複数のAIモデル（Llama、Mixtral、Qwenなど）を統一されたAPIで提供しており、無料枠が日次でリセットされるモデルが多数存在します。テストや趣味のプロジェクトに便利です。
# Hugging Face Inference API	大量のオープンソースモデルがホスティングされており、公開されている多くのモデルは**無料で推論（Inference）**を利用できます。

#10/8 16:51start

#