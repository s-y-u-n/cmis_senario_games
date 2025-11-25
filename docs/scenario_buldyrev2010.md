# Buldyrev et al. (2010) シナリオ設計

本ドキュメントは、Buldyrev et al. (2010)  
「Catastrophic cascade of failures in interdependent networks」シナリオの

- 共通フレームワーク（プレイヤー → v → 貢献度）上での位置づけ
- 数理モデルと実装モジュールとの対応関係
- 代表的な設定（ER / Scale-free / 実ネットワーク）

を整理する。

共通部分（ドメインモデル、Shapley アルゴリズム等）は  
`docs/design_cmis_senario_games.md` を参照のこと。

---

## 1. 共通フロー上での位置づけ

### 1.1 プレイヤー

Buldyrev2010（Protection 型）では、基本的に

- プレイヤー = 各ノード（もしくは、2 層ネットワークのノードペア (A_i, B_i)）

と解釈する。

- 実装上は、`0..N-1` のノード ID をプレイヤー ID とみなし、
  `coalition: np.ndarray[bool]` のインデックスと一致させる。
- `coalition[i] = True` であれば「ノード i（またはペア i）が防護対象 S に含まれる」と解釈する。

### 1.2 特性関数 v(S)

Buldyrev2010 / Protection の特性関数 v(S) は、

- `S` を防護対象ノード集合としたとき、
- ランダムな初期故障（percolation）と連鎖故障（cascading failure）の結果として得られる
  giant mutually connected component (MCGC) の相対サイズを性能指標とし、
- その期待値を取ったもの：

\\[
v(S) = \\mathbb{E}_\\omega[ F_S(\\omega) ]
\\]

として定義する。ここで `F_S(ω)` は、1 回のシミュレーションで得られた MCGC の相対サイズ。

実装上は、`src/cmis_senario_games/scenarios/buldyrev2010/value_protection.py` で
次のような形の `ValueFunction` を用意する：

```python
@dataclass
class BuldyrevProtectionConfig:
    percolation: PercolationParams
    num_scenarios: int
    performance_metric: str = "mcgc_size"  # デフォルト MCGC 相対サイズ


class BuldyrevProtectionValue(ValueFunction):
    game_type = GameType.PROTECTION

    def __init__(self,
                 system: InterdependentSystem,
                 config: BuldyrevProtectionConfig):
        self.system = system
        self.config = config

    def evaluate(self, coalition: np.ndarray) -> float:
        """
        coalition[i] = True のノードは「常に生き残る」と解釈。
        Monte Carlo により v(S) を近似。
        """
        total = 0.0
        for _ in range(self.config.num_scenarios):
            alive0 = sample_initial_failure(self.system, self.config.percolation)
            alive0[coalition] = True  # 防護
            result = run_cascade(self.system, alive0)
            total += result.m_infty
        return total / self.config.num_scenarios
```

ここで、

- `sample_initial_failure` と `run_cascade` は、共通フレームワーク側の
  「パーコレーション + カスケードエンジン」（v(S) 内部ロジック）に属する。
- `BuldyrevProtectionValue` は、それらを組み合わせて **Protection 型の v(S) を実現するシナリオ固有の部分** である。

### 1.3 貢献度指標

プレイヤーと v(S) が決まれば、共通アルゴリズムに渡して貢献度を計算できる：

- `estimate_shapley(value_fn, num_players, config)`
  - プレイヤー = ノードまたはノードペア
  - `value_fn` = `BuldyrevProtectionValue` インスタンス
  - 戻り値: 各プレイヤーの Shapley 値（防護投資における限界レジリエンス貢献度）
- 必要なら、これに基づいて `rank_players_lexcel` などで順位付けする。

---

## 2. モデル概要

Buldyrev2010 の数理モデル（概要）は以下の通り：

- 2 層（A, B）の相互依存ネットワーク。
- 各層は N ノード、同一 ID 空間 {0, …, N-1}。
- 依存リンクは 1:1 双方向（A_i ↔ B_i）。
- ノード故障は percolation（生残確率 p）と cascading failure によって決定。
- 性能指標:
  - giant mutually connected component (MCGC) の相対サイズ `m_infty`
  - 臨界値 p_c

これらは `InterdependentSystem` と `CascadeResult` を通じて実装に反映される。

---

## 3. 実装マッピング

本シナリオは、共通フレームワークのモジュールに対して次のように対応付けられる。

### 3.1 コアモジュールとの対応

- ネットワーク構造:  
  `src/cmis_senario_games/core/network_model.py`
- 依存関係:  
  `src/cmis_senario_games/core/interdependency.py`
- 初期故障（percolation）:  
  `src/cmis_senario_games/core/percolation.py`
- カスケードダイナミクス:  
  `src/cmis_senario_games/core/cascade_engine.py`

### 3.2 シナリオ固有モジュール

`src/cmis_senario_games/scenarios/buldyrev2010/` 以下に Buldyrev2010 向けロジックを集約する。

#### 3.2.1 `network_definition.py`

- 2 層のネットワークを構築する責務を負う。
- 代表的な関数：

```python
def build_er_system(n: int, k_avg: float, seed: int) -> InterdependentSystem:
    ...


def build_sf_system(n: int, lambda_: float, k_min: int, seed: int) -> InterdependentSystem:
    ...


def build_real_italy_system(path_power: str,
                            path_comm: str,
                            path_dep: str) -> InterdependentSystem:
    ...
```

- ER / Scale-free / Random regular / 実ネットワーク（イタリア停電）など、
  論文で扱うネットワークファミリーをここに閉じ込める。

#### 3.2.2 `config_schema.py`

- `configs/buldyrev2010/*.yaml` の構造を dataclass で定義。
- 例：`er_default.yaml` のスキーマ

```yaml
scenario_name: "buldyrev2010_er_protection"
game_type: "protection"
network:
  type: "er"
  num_nodes: 50000
  avg_degree: 4.0
  seed: 42
percolation:
  survival_prob: 0.8
  random_seed: 123
value_function:
  num_scenarios: 100
  performance_metric: "mcgc_size"
shapley:
  num_samples: 500
  random_seed: 999
```

#### 3.2.3 `value_protection.py`

- 前述の `BuldyrevProtectionValue` および `BuldyrevProtectionConfig` を提供し、
  Protection 型特性関数 v(S) を実際に実装する。

#### 3.2.4 `visualization.py`

- Buldyrev 的な図を再現するための可視化ユーティリティ：
  - (p) vs MCGC サイズ
  - (p) vs 存在確率（P∞）
  - ノード別 Shapley 値ヒートマップ（地理配置図 or 度数別）

```python
def plot_pc_curve(results_df: pd.DataFrame, output_path: str):
    """
    x: p, y: MCGC size / existence probability
    """


def plot_node_importance_shapley(phi: np.ndarray,
                                 network: InterdependentSystem,
                                 output_path: str):
    """
    ノード Shapley をネットワーク上に可視化。
    """
```

#### 3.2.5 `postprocess_metrics.py`

- 実験結果から、
  - 推定された臨界値 (p_c)
  - 分布別脆弱性比較（ER vs SF vs RR）
  を集計する。

```python
def estimate_pc_from_results(results_df: pd.DataFrame) -> float:
    ...


def summarize_v_results(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    coalition / node ごとの v 値の一覧を生成。
    """
```

---

## 4. デフォルト設定と実験定義

### 4.1 デフォルト設定（configs）

代表的な設定は `configs/buldyrev2010/*.yaml` に記述する。

- `er_default.yaml`: ER ネットワーク + 防護型ゲーム
- `sf_default.yaml`: Scale-free ネットワーク + 防護型ゲーム
- `italy_case_study.yaml`: イタリア停電ネットワーク（将来実装予定）

### 4.2 実験定義（experiments）

実験定義は `experiments/buldyrev2010/*.yaml` に記述し、
共通ランナー `core/experiment_runner.py` から実行する。

- `er_pc_sweep.yaml`:
  - `percolation.survival_prob` の値を変化させ、p と MCGC サイズの関係や p_c 近傍の挙動を調べる。
- `node_importance_shapley.yaml`:
  - ノード（またはノードペア）の Shapley 値を評価し、レジリエンスへの貢献度ランキングを得る。

---

## 5. 実装順序（Buldyrev2010 パターン）

Buldyrev2010 シナリオを実装する際の推奨ステップは次の通り：

1. **core/ の基盤クラス・エンジン実装**
   - `NetworkLayer`, `InterdependentSystem`
   - `percolation.py`, `cascade_engine.py`（Buldyrev 型カスケードの実装を含む）
   - `ValueFunction` 抽象, `contribution_shapley.py`
2. **scenarios/buldyrev2010/ 実装**
   - `network_definition.py`（ER / SF / RR / 実ネットワーク）
   - `value_protection.py`（防護型ゲーム v(S)）
   - `visualization.py`, `postprocess_metrics.py`
3. **configs/buldyrev2010/*.yaml の定義と experiment_runner からの実験実行**
   - `config_schema.py` で YAML を dataclass にマッピング。
4. **Shapley 値計算 + 可視化（ノード重要度ランキング）**
   - `estimate_shapley` + `plot_node_importance_shapley` などを組み合わせる。
5. **本ドキュメントの充実**
   - 論文の数理モデル
   - 実装上の対応関係
   - パラメータのデフォルト値・推奨値
   を追記し、再利用しやすいテンプレートとする。

---

## 6. TODO

- 論文からの数式・パラメータの抜き出し（特に p_c の解析的近似等）。
- MCGC 計算・カスケードアルゴリズムの pseudo code 化と検証。
- 実データ（イタリア停電）の入手元と前処理仕様の整理。
- 「ノード vs ノードペア」をプレイヤー定義として切り替えるための設定項目・実装方針の整理。

