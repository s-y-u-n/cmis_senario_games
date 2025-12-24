# sim_contribution 設計書（v1.0）

この文書は、`sim_contribution/` に含まれるシミュレーション実装の設計（責務分離・データフロー・入出力）をまとめたものです。

## 目的（プロトコル）

本シミュレーションの目的は、以下を**差し替え可能なモジュール構成**で再現することです。

- Phase A（探索10試合）で観測テーブル（ログ）を作る
- 観測テーブル上で経験的指標を算出する（未観測提携の補完はしない）
- 戦略が最終1回の組分けを提案する（戦略入力は観測ログのみ）
- Phase B（最終評価1回）を実行し、合計観測スコア `Σy` で比較する（参考でランク分布も出す）

## 重要な設計上の制約

- 戦略への入力は `SeasonLog`（Phase A 観測ログ）**のみ**。真値パラメータは禁止。
- `indices/` の経験的スコアは、後続研究の「貢献度指標」そのものではなく、**観測ログから計算可能な意思決定用スコア**。
- 乱数は `numpy.random.Generator` を用い、`seed` により再現可能。

## ディレクトリ構成（主要ファイル）

- `sim_contribution/src/sim_contribution/config.py`
  - `Config`: 人数・分布・生成モデル係数・ランク閾値・スケジュール探索パラメータなどの集中管理
- `sim_contribution/src/sim_contribution/players/`
  - `param_generator.py`: 真値パラメータ生成（ability/cooper/skill/affinity）
  - `types.py`: `PlayerParams`, `TrueParams`
- `sim_contribution/src/sim_contribution/production/`
  - `team_value.py`: 生成モデル `v(T)` と内訳（breakdown）計算
  - `diversity.py`: 多様性 `D(T)=1-mean_cosine_similarity`
  - `comm_cost.py`: `kappa * comb(|T|,2)` のコスト計算
- `sim_contribution/src/sim_contribution/observation/`
  - `noise.py`: 観測ノイズ `ε`
  - `ranking.py`: Phase A の mean/std + 閾値で A〜E ランク付与（Phase Bも同基準）
- `sim_contribution/src/sim_contribution/schedule/`
  - `generator.py`: Phase A の固定探索スケジュール生成（10試合）
  - `constraints.py`: スケジュールのペナルティ（ソフト制約）
- `sim_contribution/src/sim_contribution/log/schema.py`
  - `TeamLog`, `MatchLog`, `SeasonLog`: Phase A の観測テーブル（JSON/CSV出力の基礎）
- `sim_contribution/src/sim_contribution/indices/`
  - `empirical_interaction.py`: 観測済みチームの経験的相互作用スコア（shrinkage付き）
  - `pair_profile.py`: ペアのランク分布ベクトル（A,B,C,D,E）
- `sim_contribution/src/sim_contribution/strategies/`
  - `random_partition.py`: ベースライン（サイズ1..3）
  - `greedy_interaction.py`: 経験的相互作用スコアに基づく貪欲組分け
  - `lexcel_weber_pairing.py`: Lexcel比較 + Weber式のペアリング（2人×5固定）
- `sim_contribution/src/sim_contribution/evaluation/`
  - `runner.py`: Phase A 実行 / Phase B 評価 / 戦略比較
  - `reporting.py`: ログ・指標一覧（Phase A indices）・真値の保存
- `sim_contribution/src/sim_contribution/viz/`
  - `plots.py`: 出力図（PNG）
- `sim_contribution/scripts/run_one_season.py`
  - エントリポイント（1シーズンを実行して outputs を生成）

## データモデル（ログ）

`SeasonLog` は Phase A の観測テーブルで、戦略入力の唯一のデータです。

- `TeamLog`
  - `members`: チーム構成（player_idのタプル）
  - `v_true`: 真の `v(T)`（可視化・保存用）
  - `y_obs`: 観測 `y=v+ε`
  - `z`, `rank`: Phase A 統計での標準化・ランク
  - `breakdown`: `v(T)` の内訳（base/diversity/affinity/cooperation/comm_cost）
- `SeasonLog.phase_a_stats`
  - `mean_y`, `std_y`, `thresholds`: Phase A で確定した標準化・閾値（Phase Bにも再利用）

## 計算内容（モデル）

### 生成モデル v(T)

`production/team_value.py` が `v(T)` と内訳を返す。

- base: `sum(a_i)`
- diversity: `lambda_div * D(T)`
- affinity: `sum_{i<j} h_ij`
- cooperation: `lambda_coop * sum(c_i) * g(|T|)`
- comm_cost: `-kappa*comb(|T|,2)`

### 観測モデル y とランク

- `y = v(T) + Normal(0, sigma_noise)`
- ランク: Phase A の mean/std で z-score → 閾値で A〜E
- Phase B のランクも Phase A の mean/std/閾値を使う（比較一貫性）

## 指標（観測ログベース）

### 経験的相互作用（チーム）

`indices/empirical_interaction.py`:

- 観測された同一チーム `T` の `y_obs` 平均を `mean_y(T)`
- 同サイズチームの `y_obs` 平均を `base(|T|)`
- `raw = mean_y(T) - base(|T|)`
- shrinkage: `w=n/(n+alpha)`, `score=w*raw`

注意: 理論的 Shapley Interaction Index の定義そのものではない（観測可能な代替）。

### ペアプロフィール（ペア）

`indices/pair_profile.py`:

- ペア `(i,j)` が同一チームで観測されたときの `rank` をカウントし `(A,B,C,D,E)` を返す

## 戦略

- `random_partition`: サイズ制約 1..3 を満たすランダム
- `greedy_interaction`: 経験的相互作用スコア降順で、重複しないチームを貪欲採用し、残りを埋める
- `lexcel_weber_pairing`: ペアの `(A,B,C,D,E)` を辞書式に比較し上位から重複なしで採用（2人×5固定）

## 出力（成果物）

`run_one_season.py` は `--outdir` に以下を出力する。

- Phase A: `phase_a_log.json`, `phase_a_teams.csv`
- Phase A 指標一覧: `phase_a_indices.json`, `phase_a_indices.csv`
  - 提携 |T|=1..3 の全組合せを対象
  - 計算できない項目は `null`（個人にはペア指標などが定義できないため）
- Phase B: `phase_b_results.json`, `phase_b_*.csv`
- 真値（分析用）: `true_params.json`
- 図: `players.png`, `phase_a_teams.png`, `phase_a_breakdown.png`, `phase_b_partitions.png`, `phase_b_summary.png`

## 交換可能性（差し替えポイント）

- 生成モデル: `production/team_value.py`
- 探索スケジュール: `schedule/generator.py`（制約・目的関数を差し替え）
- 観測・ランク: `observation/`
- 指標: `indices/`
- 戦略: `strategies/`
- 評価・レポート: `evaluation/`

