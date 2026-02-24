import pandas as pd
from janome.tokenizer import Tokenizer
from collections import Counter
import itertools
import networkx as nx
import matplotlib.pyplot as plt
import japanize_matplotlib  # 日本語表示を有効化

# --- ストップワードの定義 ---
# 分析から除外したい、特徴を捉えない一般的な単語のリスト
stop_words = [
    # ユーザーが指摘した単語
    '請求', '範囲', '詳細', '説明', '選択', '図面', '提供', '代表', '拡大', '回転',
    # 特許文書で頻出する定型的な単語
    '構成', '課題', '解決', '手段', '発明', '考案', '従来', '技術', '効果', '実施',
    '形態', '方法', '装置', 'システム', '制御', '部分', '部材', '本体', '構造',
    '特徴', '作用', '目的', '上記', '下記', '同様', '各部', '図', '号',
    # 一般的な名詞・代名詞
    'もの', 'こと', 'ため', '場合', 'これ', 'それ', 'よう', 'みたい', 'さん', 'ところ',
    'すべて', '一つ', 'それぞれ', 'のち', 'のり', '一例'
]
print(f"除外するストップワード: {stop_words}")

# --- 1. データの読み込みと前処理 ---
print("1. CSVファイルを読み込んでいます...")
try:
    # CSVファイルを読み込みます
    df = pd.read_csv('高効率化_data.csv')
    # 分析対象のテキストを結合（NaNは空文字に変換）
    df['text'] = df['要約_課題'].fillna('') + df['要約_解決手段'].fillna('')
except FileNotFoundError:
    print("エラー: '水耕栽培_data.csv' が見つかりません。")
    print("コードと同じディレクトリにファイルを置いてください。")
    exit()

# --- 2. 日本語の形態素解析 ---
print("2. テキストを単語に分割しています（形態素解析）...")
t = Tokenizer()

# 各特許の要約から「名詞」のみを抽出し、ストップワードを除外する
words_list = []
for text in df['text']:
    tokens = t.tokenize(text)
    # 2文字以上の名詞で、かつストップワードに含まれない単語のみを抽出
    words = [
        token.surface for token in tokens 
        if token.part_of_speech.startswith('名詞') 
        and len(token.surface) > 1
        and token.surface not in stop_words  # ストップワードを除外する条件を追加
    ]
    words_list.append(words)

# --- 3. 共起関係の集計 ---
print("3. 単語の共起関係を数えています...")
co_occurrence_pairs = []
# 各特許ごとに出現した単語のペアを作成
for words in words_list:
    # 組み合わせを生成し、リストに追加
    pairs = list(itertools.combinations(set(words), 2)) # set()で重複ペアを除外
    co_occurrence_pairs.extend(pairs)

# ペアの出現回数を数える
co_occurrence_counts = Counter(co_occurrence_pairs)

# 頻度の高いペア上位50件を抽出
top_50_pairs = co_occurrence_counts.most_common(50)

# --- 3-1. 共起ペアをCSVファイルに出力 ---
print("3-1. 上位50の共起ペアを 'top_50_pairs.csv' に出力します...")
pairs_df = pd.DataFrame(top_50_pairs, columns=['Pair', 'Frequency'])
# ペアを分割して別々の列にする
if not pairs_df.empty:
    pairs_df[['Word1', 'Word2']] = pd.DataFrame(pairs_df['Pair'].tolist(), index=pairs_df.index)
    pairs_df[['Word1', 'Word2', 'Frequency']].to_csv('top_50_pairs.csv', index=False, encoding='utf-8-sig')
else:
    print("警告: 有効な共起ペアが見つかりませんでした。'top_50_pairs.csv' は空になります。")
    pd.DataFrame(columns=['Word1', 'Word2', 'Frequency']).to_csv('top_50_pairs.csv', index=False, encoding='utf-8-sig')


# --- 4. ネットワークグラフの作成 ---
print("4. ネットワークグラフを作成しています...")
G = nx.Graph()

# 頻出単語の出現回数を計算（ノードのサイズ用）
all_words = [word for words in words_list for word in words]
word_counts = Counter(all_words)

# グラフにノード（単語）とエッジ（単語間のつながり）を追加
for pair, weight in top_50_pairs:
    word1, word2 = pair
    # エッジを追加（weightは共起頻度）
    G.add_edge(word1, word2, weight=weight)
    # ノードのサイズを単語の総出現回数に設定
    if 'size' not in G.nodes[word1]:
        G.add_node(word1, size=word_counts[word1])
    if 'size' not in G.nodes[word2]:
        G.add_node(word2, size=word_counts[word2])
        
# --- 4-1. 単語の出現頻度をCSVファイルに出力 ---
print("4-1. 各単語の出現頻度を 'word_frequencies.csv' に出力します...")
# グラフに含まれる単語のみを抽出
nodes_in_graph = list(G.nodes())
word_freq_list = [{'Word': word, 'Frequency': word_counts[word]} for word in nodes_in_graph]
word_freq_df = pd.DataFrame(word_freq_list)
if not word_freq_df.empty:
    word_freq_df.sort_values(by='Frequency', ascending=False, inplace=True)
word_freq_df.to_csv('word_frequencies.csv', index=False, encoding='utf-8-sig')


# --- 5. ネットワークの可視化とファイル保存 ---
if G.nodes():
    print("5. グラフを描画し、'co_occurrence_network.png' に保存します...")
    plt.figure(figsize=(20, 20))

    # ネットワークのレイアウトを計算（バネモデル）
    pos = nx.spring_layout(G, k=0.9, seed=42)

    # ノードのサイズとエッジの太さを設定
    node_sizes = [d.get('size', 0) * 100 for n, d in G.nodes(data=True)]
    edge_widths = [d.get('weight', 0) * 0.5 for u, v, d in G.edges(data=True)]

    # 描画
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='c', alpha=0.8)
    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color='gray', alpha=0.6)
    nx.draw_networkx_labels(G, pos, font_size=12, font_family='IPAexGothic') # フォント指定

    plt.title('「水耕栽培」特許の共起ネットワーク (上位50ペア)', fontsize=22)
    plt.axis('off') # 軸を非表示

    # グラフを画像ファイルとして保存
    plt.savefig('co_occurrence_network.png', dpi=300, bbox_inches='tight')
    plt.close() # メモリ解放のためにプロットを閉じる
else:
    print("警告: グラフを描画するデータがありません。'co_occurrence_network.png' は生成されません。")


print("\n分析が完了し、すべてのファイルを出力しました。")
print("- co_occurrence_network.png (グラフ画像)")
print("- top_50_pairs.csv (共起ペアリスト)")
print("- word_frequencies.csv (単語頻度リスト)")

