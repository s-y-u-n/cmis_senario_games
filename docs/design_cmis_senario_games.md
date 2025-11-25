# cmis_senario_games 基本設計書（共通フレームワーク）

本ドキュメントは、GitHub リポジトリ `cmis_senario_games` の「共通フレームワーク」と
その設計方針を示す。  
個々の論文パターン（Buldyrev2010 など）の詳細は、別途シナリオごとの設計書で扱う。

本フレームワークで一番大きい要件・流れは、どの論文パターンでも共通して次の 3 段階で構成される：

1. **プレイヤーを設定する**  
   - 例: 各ノード、ノードペア、リンク集合、施設グループなど。
2. **特性関数 v(S) を計算する**  
   - 任意の「プレイヤー集合 S」に対して、レジリエンス指標などの値 v(S) を返す。
   - ここで各論文固有の物理・確率モデル（パーコレーション、カスケード等）が登場する。
3. **貢献度指標を計算する**  
   - 例: Shapley 値、lex-cel ランク付けなど。
   - v(S) を「ブラックボックス」として扱い、その上で協力ゲーム理論の指標を計算する。

以下では、この 3 段階フローを軸に、共通部分と拡張ポイントを整理する。

---

## 1. リポジトリ全体構成

標準的なシミュレーションシステムの構成ルールに従い、  
「コアエンジン」「シナリオ（論文）依存コード」「実験定義」「出力」「ドキュメント」を分離する。

```text
cmis_senario_games/
  README.md
  pyproject.toml / setup.cfg          # Python パッケージ定義
  .gitignore
  docs/
    design_cmis_senario_games.md      # 本ドキュメント（共通フレームワーク）
    scenario_buldyrev2010.md          # Buldyrev2010 特化の理論・仕様
    scenarios_overview.md             # 全シナリオ一覧と対応表
  src/
    cmis_senario_games/
      __init__.py
      core/                           # 共通エンジン層
        __init__.py
        network_model.py
        interdependency.py
        percolation.py
        cascade_engine.py
        value_functions.py
        contribution_shapley.py
        contribution_lexcel.py
        experiment_runner.py
        io_config.py
        io_results.py
      scenarios/                      # 論文・フレームワーク別シナリオ
        __init__.py
        buldyrev2010/
          __init__.py
          config_schema.py
          network_definition.py
          value_protection.py
          visualization.py
          postprocess_metrics.py
        # future:
        #  xxx20yy_damage_reduction/
        #  zzz20ww_credit_allocation/
  configs/
    buldyrev2010/
      er_default.yaml                 # ER ネットワークの防護型ゲーム設定
      sf_default.yaml                 # Scale-free ネットワーク設定
      italy_case_study.yaml           # イタリア停電ケース模倣
  experiments/
    buldyrev2010/
      er_pc_sweep.yaml                # p と pc 周辺の sweep 定義
      node_importance_shapley.yaml    # Shapley によるノード重要度評価
  data/
    raw/
      # 実データ（例：イタリア停電ネットワーク）を置く場所
    processed/
      # 前処理済ネットワーク・依存リンク
  outputs/
    logs/
    results/
      buldyrev2010/
        er_pc_sweep/
        node_importance_shapley/
    figures/
      buldyrev2010/
        pc_curves.png
        node_importance_heatmap.png
  notebooks/
    buldyrev2010_exploration.ipynb    # 試行・可視化用
  tests/
    test_core_*.py
    test_scenario_buldyrev2010_*.py
```

---

## 2. ゲーム実行の基本フロー（プレイヤー → v → 貢献度）

### 2.1 プレイヤーを設定する

- プレイヤー集合は、各シナリオごとに「誰の貢献度を知りたいか」を定義する。
- 典型的には:
  - ノード（インフラ施設、需要点）
  - ノードペア（2層ネットワークの (A_i, B_i) ペア）
  - サブネットワーク（地理ブロック、事業者など）
- 実装上は、多くのケースで
  - プレイヤー = `0..N-1` のインデックス
  - `coalition: np.ndarray[bool]` で「プレイヤーが集合 S に含まれるか」を表現
  - この `N` が `ValueFunction.evaluate()` の入力次元、および Shapley などの `num_players` となる。

プレイヤーの意味付け（ノードなのか、ノードペアなのか）はシナリオ側（`src/cmis_senario_games/scenarios/...`）で決める。

### 2.2 特性関数 v(S) を計算する

- 特性関数 v(S) は「プレイヤー集合 S が与えられたときのシステム性能」を返す。
- 抽象的には `ValueFunction` プロトコルで定義される（後述）。
- 具体的な v(S) の定義はフレームワークごとに異なる:
  - Protection: 「S を防護したときのレジリエンス指標（例: MCGC サイズの期待値）」など。
  - Damage Reduction: 「被害総量の減少」など。
  - Credit Allocation: 「ある指標の寄与度にもとづくクレジット配分」など。

**重要:**  
v(S) を計算する内部ロジックとして、シナリオ固有の

- パーコレーション
- カスケード（連鎖故障）

といったダイナミクスが登場する。  
本設計書の **3. ドメインモデル設計** および **4. パーコレーション + カスケードエンジン** は、
この「v(S) を評価するためのサブロジック」を定義しているだけであり、

- 「プレイヤーをどう定義するか」
- 「Shapley などの貢献度指標をどう計算するか」

には直接関与しない。

### 2.3 貢献度指標を計算する

- 一度 v(S) を評価できれば、協力ゲーム理論の標準手続きを適用できる:
  - Shapley 値: プレイヤーごとの限界貢献度の期待値。
  - Banzhaf 値: 連立におけるスイングの期待値（必要なら追加）。
  - lex-cel ランク: 複数指標をまとめたランキングルール。
- フレームワークに依存しない **共通アルゴリズム** として、
  - `src/cmis_senario_games/core/contribution_shapley.py`
  - `src/cmis_senario_games/core/contribution_lexcel.py`
  を実装し、`ValueFunction` をブラックボックスとして扱う。

---

## 3. ドメインモデル設計

### 3.1 コアの抽象モデル（ネットワーク）

`src/cmis_senario_games/core/network_model.py`

```python
@dataclass
class NetworkLayer:
    name: str                     # "A" (power), "B" (communication) 等
    num_nodes: int
    edges: np.ndarray             # shape: (m, 2) の隣接リスト
    degree_distribution: Optional[np.ndarray] = None


@dataclass
class MultiLayerNetwork:
    layers: Dict[str, NetworkLayer]       # {"A": NetworkLayer, "B": NetworkLayer}
    # ノード ID は 0..N-1 を共有し、依存関係で層を跨いで紐づく
```

Multi-layer の構造は、いずれの論文パターンでも共通の表現を使い、

- 単層グラフ（1 layer）
- 2 層相互依存ネットワーク（Buldyrev2010 など）
- 3 層以上の多層ネットワーク

を `layers` の中身だけ差し替えて表現する。

### 3.2 依存関係（Interdependency）

`src/cmis_senario_games/core/interdependency.py`

```python
@dataclass
class DependencyMapping:
    # dep_A_to_B[i] = j  (A 層の i が B 層の j に依存)
    dep_A_to_B: np.ndarray
    dep_B_to_A: np.ndarray        # 通常は dep_A_to_B の逆写像


@dataclass
class InterdependentSystem:
    network: MultiLayerNetwork
    dependency: DependencyMapping
```

- `InterdependentSystem` は、「ネットワーク構造」と「層間依存関係」をまとめたコア構造。
- Buldyrev2010 シナリオは、その特殊ケースとして
  - 層数 = 2
  - 依存リンク = 1:1 双方向
  を仮定する。詳細は `docs/scenario_buldyrev2010.md` を参照。

---

## 4. v(S) 内部ロジック：パーコレーション + カスケードエンジン

このセクションで定義するモジュールは、**2.2「v(S) を計算する」の内部ロジック** であり、

- プレイヤーの定義や Shapley 計算とは独立した「システムダイナミクス」のみを扱う。
- どの論文パターンでも、必要に応じてこれらの組み合わせ・変種を用いる。

### 4.1 パーコレーション（初期故障のサンプリング）

`src/cmis_senario_games/core/percolation.py`

- ノード単位での生残確率 (p) に基づき、初期故障状態を生成。
- ゲームごとに「防護集合 (S)」などを考慮した修正状態を生成（これは各 `ValueFunction` 側で行う）。

```python
@dataclass
class PercolationParams:
    survival_prob: float           # p
    random_seed: Optional[int] = None


def sample_initial_failure(system: InterdependentSystem,
                           params: PercolationParams) -> np.ndarray:
    """
    戻り値: alive_mask (shape: (N,), bool)
    """
```

### 4.2 カスケードエンジン（連鎖故障）

`src/cmis_senario_games/core/cascade_engine.py`

- 相互依存ネットワーク上での cascading failure を実装する窓口。
- 入力:
  - `InterdependentSystem`
  - 初期 `alive_mask`（ゲームごとの防護集合適用後）
- 出力:
  - 最終 `alive_mask`
  - 各ステージの giant mutually connected component (MCGC) サイズなど

```python
@dataclass
class CascadeResult:
    final_alive_mask: np.ndarray     # shape: (N,)
    m_infty: float                   # MCGC 相対サイズ
    history: Dict[str, Any]          # ステップごとのメトリクス


def run_cascade(system: InterdependentSystem,
                initial_alive_mask: np.ndarray) -> CascadeResult:
    ...
```

- Buldyrev2010 の 2 層 1:1 依存カスケードは、この `run_cascade` の具体実装パターンの 1 つであり、
  詳細はシナリオ設計書 `docs/scenario_buldyrev2010.md` で扱う。
- 他の論文パターン（例: 多層依存、時間遅れ等）があれば、
  仕様に応じたカスケードロジックをこのレイヤ、もしくは scenario 側で差し替える。

---

## 5. 特性関数 (v(S)) の共通定義

`src/cmis_senario_games/core/value_functions.py`

### 5.1 ゲームタイプ

「3 フレームワーク」を共通インターフェースで扱うため、`GameType` を定義する。

```python
from enum import Enum


class GameType(Enum):
    PROTECTION = "protection"          # 防護型
    DAMAGE_REDUCTION = "damage_reduction"
    CREDIT_ALLOCATION = "credit_allocation"
```

### 5.2 抽象インターフェース `ValueFunction`

```python
class ValueFunction(Protocol):
    game_type: GameType

    def evaluate(self, coalition: np.ndarray) -> float:
        """
        coalition: shape (N,), bool マスク
        返り値: v(S) の値
        """
        ...
```

- `coalition` は「プレイヤー集合 S」を表現するブール配列。
- `evaluate()` は、内部で
  - パーコレーション (`sample_initial_failure`)
  - カスケード (`run_cascade`)
  - その他、シナリオ固有のロジック
  を呼び出して v(S) を計算する。
- 具体的な Protection / Damage Reduction / Credit Allocation 各パターンの `ValueFunction` 実装は、
  `src/cmis_senario_games/scenarios/<paper_short_name>/` 側に置く。

Buldyrev2010 における Protection 型特性関数の詳細は、
`docs/scenario_buldyrev2010.md` を参照。

---

## 6. 貢献度評価（Shapley / lex-cel）

### 6.1 Shapley 値

`src/cmis_senario_games/core/contribution_shapley.py`

- フレームワーク・シナリオに依存しない汎用実装として、
  「任意の `ValueFunction` に対して Shapley を近似」する。

```python
@dataclass
class ShapleyConfig:
    num_samples: int
    random_seed: Optional[int] = None


def estimate_shapley(value_fn: ValueFunction,
                     num_players: int,
                     config: ShapleyConfig) -> np.ndarray:
    """
    Monte Carlo permutation sampling による Shapley 近似。
    戻り値: shape (num_players,)
    """
```

- `value_fn.evaluate()` をブラックボックスとして扱い、
  ランダム順序のマージナル貢献度を平均する。
- Buldyrev2010 の場合：
  - プレイヤー = 各ノードまたはノードペア
  - `value_fn` = Protection 型特性関数
  - Shapley 値 = 「防護投資における限界レジリエンス貢献度」
  として解釈できる（詳細はシナリオ設計書で扱う）。

### 6.2 lex-cel 型ランク付け

`src/cmis_senario_games/core/contribution_lexcel.py`

- 事前に計算された貢献度ベクトル（Shapley, Banzhaf など）から、
  特定の lexicographic + cell-based ルールで順位付けを行う。

```python
@dataclass
class LexCelConfig:
    # 例：一次指標 Shapley、二次指標 何らかの距離中心性など
    primary_weight: float = 1.0


def rank_players_lexcel(contributions: np.ndarray,
                        tie_break_metric: Optional[np.ndarray],
                        config: LexCelConfig) -> np.ndarray:
    """
    戻り値: 順位（0=最上位）
    """
```

- 入力は単に「プレイヤーごとのスカラー指標」であり、
  ここでも v(S) の中身やシナリオには依存しない。

---

## 7. 実験ランナーと結果管理

`src/cmis_senario_games/core/experiment_runner.py`

- YAML の experiment 定義を読み込み、
  3 段階フローを自動的につなぐ役割を持つ:
  1. **プレイヤーを設定する**
     - シナリオモジュール（例: `scenarios/buldyrev2010/network_definition.py`）から
       ネットワーク・依存関係を構築し、プレイヤー集合を暗黙的に決める。
  2. **v(S) を計算する**
     - シナリオモジュールの `ValueFunction` 実装を構築。
     - 必要に応じてパーコレーション + カスケードエンジンを内部で利用。
  3. **貢献度指標を計算する**
     - `estimate_shapley` や `rank_players_lexcel` を呼び出し、
       `outputs/results/` 以下に保存。
- 併せて、図を `outputs/figures/` に保存する責務も持つ。

```python
def run_experiment(experiment_config_path: str):
    """
    1. config ロード
    2. Scenario module 呼び出し
    3. v(S) 評価・Shapley 計算
    4. 結果を保存
    """
```

CLI 用のエントリポイント例：

```bash
python -m cmis_senario_games.run_experiment \
  --config experiments/buldyrev2010/node_importance_shapley.yaml
```

---

## 8. 共通出力フォーマット

### 8.1 v の結果一覧

`src/cmis_senario_games/core/io_results.py` で統一フォーマットを定義：

```python
@dataclass
class ValueResult:
    game_type: GameType
    scenario_name: str
    coalition_id: str           # e.g. "node_42", "set_A", ...
    coalition_mask: np.ndarray
    v_value: float
```

CSV / Parquet 形式で保存：

```text
outputs/results/<scenario_name>/<experiment_name>/v_values.parquet
```

Buldyrev2010 の例：

- `outputs/results/buldyrev2010/node_importance_shapley/v_values.parquet`

列例：

- `scenario_name`
- `game_type`
- `coalition_id`
- `v_value`

### 8.2 貢献度（Shapley / lex-cel）出力

同様に、貢献度の結果を保存する：

```text
outputs/results/<scenario_name>/<experiment_name>/contribution.parquet
```

想定される列：

- `player_id`
- `phi_shapley`
- `rank_lexcel`
- オプションで degree, layer, centrality など説明変数も付与

---

## 9. 拡張：他フレームワーク・他論文パターンの組込み方針

- フレームワークは `GameType` と `ValueFunction` 実装で切り替え可能にする。
  - Protection: `ProtectionValue` 系
  - Damage Reduction: `DamageReductionValue` 系
  - Credit Allocation: `CreditAllocationValue` 系
- 論文パターンは `scenarios/<paper_short_name>/` として追加する。
- ネットワーク構造・パラメータの違いは
  - `network_definition.py`
  - `config_schema.py`
  に閉じ込める。
- 可能な限り `core/` の再利用を徹底し、
  「論文ごとの固有ロジック」だけを scenario 側に寄せる。

Buldyrev2010 はその第1例として、

- 2層相互依存ネットワーク
- 防護型ゲーム（`GameType.PROTECTION`）
- 特性関数 = MCGC サイズの期待値

を採用している。詳細は `docs/scenario_buldyrev2010.md` を参照。

---

## 10. 実装順序（全体ガイド）

本リポジトリに新しい論文パターンを追加するときは、次の順序を基本とする。

1. **core/ の基盤クラス・エンジンを確認／拡張**
   - `NetworkLayer`, `MultiLayerNetwork`, `InterdependentSystem`
   - 必要であれば `percolation.py`, `cascade_engine.py` にロジックを追加
   - `ValueFunction` 抽象, `contribution_shapley.py`, `contribution_lexcel.py` を再利用
2. **scenarios/<paper_short_name>/ を実装**
   - `network_definition.py`（ネットワーク生成／読み込み）
   - 各フレームワーク向けの `ValueFunction` 実装（Protection / Damage Reduction / Credit Allocation）
   - 必要な可視化・後処理モジュール（`visualization.py`, `postprocess_metrics.py` 等）
3. **configs/<paper_short_name>/*.yaml を定義し、experiment_runner から実験実行**
   - シナリオ固有の config schema（`config_schema.py`）で読み込む。
4. **Shapley 値計算 + 可視化（貢献度分析）**
   - core の `estimate_shapley` / `rank_players_lexcel` を利用。
5. **docs/scenario_<paper_short_name>.md で**
   - 論文の数理モデル
   - 実装上の対応関係
   - パラメータのデフォルト値
   を整理し、共通フレームワーク（本ドキュメント）との対応を明示する。

以上を基本骨格とし、他の論文パターン（防護型・被害削減量・クレジット配分）も
同一の「プレイヤー → v → 貢献度」フロー上で拡張していく。

