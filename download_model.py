from transformers import AutoTokenizer, AutoModelForTokenClassification
import os

# ダウンロードしたいモデルの名前
model_name = "cl-tohoku/bert-base-japanese-whole-word-masking-finetuned-ner"
# モデルを保存するフォルダ名
output_dir = "./local-bert-ner"

print(f"モデル '{model_name}' のダウンロードを開始します...")
print(f"保存先フォルダ: {output_dir}")
print("これには数分かかることがあります。しばらくお待ちください...")

try:
    # 保存先フォルダが存在しない場合は作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # トークナイザーをダウンロードして指定フォルダに保存
    print("トークナイザーをダウンロード中...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(output_dir)
    
    # モデル本体をダウンロードして指定フォルダに保存
    print("モデル本体をダウンロード中...")
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    model.save_pretrained(output_dir)
    
    print(f"\n✅ ダウンロードと保存が正常に完了しました。")
    print(f"モデルファイルが '{output_dir}' フォルダに保存されました。")
    print("これで analyze_patents_hf.py を実行できます。")

except Exception as e:
    print(f"\n❌ ダウンロード中にエラーが発生しました: {e}")
    print("ネットワーク接続を確認するか、プロキシ/ファイアウォールの設定を見直してください。")

