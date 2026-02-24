# 1. 特許出願のトレンド分析
# 目的: 「高効率化」関連技術が、いつ頃から注目され、どのように推移してきたかを把握します。

# 分析内容:

# 出願日・公開日を年ごとに集計し、出願件数の推移を折れ線グラフで可視化します。

# これにより、技術開発が活発になった時期や、市場の関心が高まったタイミングを読み取ることができます。

# 2. 主要プレイヤーの特定（出願人・発明者分析）
# 目的: どの企業や発明者が「高効率化」技術の研究開発をリードしているかを明らかにします。

# 分析内容:

# 出願人ランキング: 出願件数の多い企業や組織をランキング形式で表示し、棒グラフで可視化します。上位企業の動向を追うことで、業界の競争環境を理解できます。

# 発明者ランキング: 同様に、貢献度の高い発明者を特定します。キーパーソンを見つけることで、技術の核心に迫るヒントが得られるかもしれません。

# 3. 技術内容のテキストマイニング
# 目的: 特許の名称や要約から、具体的な技術キーワードやトレンドを抽出します。

# 分析内容:

# ワードクラウド: 「発明の名称」や「要約」に含まれる単語の出現頻度を分析し、頻出する単語を大きく表示するワードクラウドを作成します。これにより、どのような技術要素（例：「電力変換」「制御方法」「モータ」など）が注目されているか、視覚的に一目で把握できます。
# WC.pyに実装
# 共起ネットワーク: 単語と単語の結びつきを分析し、ネットワーク図として可視化します。例えば、「高効率化」というキーワードが、どのような技術（「インバータ」「半導体」など）と一緒に登場することが多いか、その関連性を探ることができます。
# pip install pandas janome networkx matplotlib japanize-matplotlib
import pandas as pd
from janome.tokenizer import Tokenizer
from collections import Counter
import itertools
import networkx as nx
import matplotlib.pyplot as plt
import japanize_matplotlib  # 日本語表示を有効化

# --- 1. データの読み込みと前処理 ---
print("1. CSVファイルを読み込んでいます...")
try:
    # CSVファイルを読み込みます
    df = pd.read_csv('水耕栽培_data.csv')
    # 分析対象のテキストを結合（NaNは空文字に変換）
    df['text'] = df['要約_課題'].fillna('') + df['要約_解決手段'].fillna('')
except FileNotFoundError:
    print("エラー: '水耕栽培_data.csv' が見つかりません。")
    print("コードと同じディレクトリにファイルを置いてください。")
    exit()

# --- 2. 日本語の形態素解析 ---
print("2. テキストを単語に分割しています（形態素解析）...")
t = Tokenizer()

# 各特許の要約から「名詞」のみを抽出する
words_list = []
for text in df['text']:
    tokens = t.tokenize(text)
    # 2文字以上の名詞のみを抽出
    words = [token.surface for token in tokens if token.part_of_speech.startswith('名詞') and len(token.surface) > 1]
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
pairs_df[['Word1', 'Word2']] = pd.DataFrame(pairs_df['Pair'].tolist(), index=pairs_df.index)
pairs_df[['Word1', 'Word2', 'Frequency']].to_csv('top_50_pairs.csv', index=False, encoding='utf-8-sig')

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
word_freq_df.sort_values(by='Frequency', ascending=False, inplace=True)
word_freq_df.to_csv('word_frequencies.csv', index=False, encoding='utf-8-sig')


# --- 5. ネットワークの可視化とファイル保存 ---
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

print("\n分析が完了し、すべてのファイルを出力しました。")
print("- co_occurrence_network.png (グラフ画像)")
print("- top_50_pairs.csv (共起ペアリスト)")
print("- word_frequencies.csv (単語頻度リスト)")

# 4. 共同研究開発の状況分析
# 目的: 企業間の連携や、産学連携の動向を把握します。

# 分析内容:

# 共同出願（共願）の分析: 複数の出願人が名を連ねる特許を抽出し、どのような企業・組織が共同で研究開発を行っているかを分析します。これにより、オープンイノベーションの動向や、技術的なパートナーシップを把握できます。

