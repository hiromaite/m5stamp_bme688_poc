# H2S ベンチマークシステム要件 v1

## 1. 目的

本プロジェクトは、`M5StampS3` に接続した `BME688` が `H2S` センサとして
どの程度機能するかを評価することを目的とする。

本システムは、以下を支援するものとする。

- デバイス側でのヒータープロファイル制御に基づく計測
- PC 側での堅牢なデータロギング
- 分類および回帰実験のためのデータセット作成
- 管理された条件下での再現可能なモデル性能評価

本仕様は以下の両方を対象とする。

- `M5StampS3` 上で動作するファームウェア
- PC 側のロガーおよび将来の GUI ツール群

## 2. 現在のベースライン

以下のマイルストーンはすでに存在しており、ベースライン参照点として扱う。

- `f5a6e7a`: 初期の `parallel-mode` firmware PoC
- `d7959e3`: Python serial logger PoC

現在の firmware の特性:

- ボード: `M5StampS3`
- センサ: I2C 接続の `BME688`
- ファームウェアライブラリ: Bosch `BME68x SensorAPI`
- 動作モード: `parallel mode`
- 現在のプロファイル: Bosch 標準の 10-step VSC 指向プロファイル
- 出力形式: 1 step ごとの有効データを含む serial CSV 行

現在の Python PoC の特性:

- `pyserial` によるシリアル受信
- 必要に応じた raw line 保存
- 解析済み CSV の永続化
- `frame_id` に基づく簡易フレーム要約

## 3. システム目標

最終システムは、以下を可能にするものとする。

1. BME688 から再現性のある multi-step ヒーター応答データを取得すること
2. 特に H2S を対象としたガス暴露条件でデータセットにラベル付けすること
3. メタデータ付きで実験セッションを保存し、確認できること
4. デバイス外で回帰および分類モデルの学習・評価を行えること
5. ヒータープロファイル、暴露条件、モデル構成を比較できること

## 4. スコープ

### スコープ内

- BME688 のプロファイル制御とデータストリーミングを行う firmware
- データ取得、保存、オペレーター監視を行う PC ロガー
- 教師あり学習に必要なメタデータの取得
- 実験セッションのトレーサビリティ
- ベンチマークワークフローの支援

### 初期プロダクトでのスコープ外

- デバイス上での機械学習推論
- クラウド同期
- 将来要求されない限り、1 個の BME688 を超えるマルチセンサ融合
- ガス暴露装置の完全なラボ自動化

## 5. 想定ワークフロー

1. M5StampS3 を USB で PC に接続する
2. BME688 を I2C で M5StampS3 に接続する
3. GUI をデバイスへ接続する
4. firmware が連続ストリームするデータをライブプロットで観察する
5. オペレーターが保存したいときだけ記録を開始する
6. 記録中にラベル付き暴露セグメントを開始・終了する
7. 記録区間について 1 つの CSV を出力する
8. 出力した CSV をオフラインのベンチマークやモデル開発に使う

## 6. Firmware 要件

### 6.1 必須要件

- firmware は `M5StampS3` 上で動作すること
- firmware は BME688 と I2C で通信すること
- firmware は Bosch `BME68x SensorAPI` を使用すること
- firmware は `parallel mode` をサポートすること
- firmware は 10-step ヒータープロファイルをサポートすること
- firmware は起動後に機械可読な serial データを連続出力すること
- firmware は有効な計測行のみを識別できること
- firmware は少なくとも以下の step / 順序情報を出力すること
  - `frame_id`
  - `frame_step`
  - `gas_index`
  - `meas_index`
- firmware は少なくとも以下を出力すること
  - 温度
  - 湿度
  - 気圧
  - ガス抵抗
  - 妥当性フラグ
- firmware は PC 側が 1 つの 10-step サイクルを再構成できるだけの情報を提供すること
- firmware は起動時にデフォルトのヒータープロファイルを読み込むこと
- firmware はランタイム中にアクティブなヒータープロファイルを更新できること
- firmware はプロファイル更新を揮発性として扱うこと
- firmware は再起動または電源再投入後にデフォルトプロファイルへ戻ること

### 6.2 強く望ましい要件

- firmware は大きな書き換えなしでヒータープロファイルを切り替えられること
- firmware は起動時またはセッション開始時にプロファイルメタデータを出力できること
- firmware は長時間運転でも安定して動作すること
- firmware は将来の PC からのコマンドインターフェースを支援できること
- firmware は明示的なセッション開始マーカーを支援できること

### 6.3 将来要件

- プリセットプロファイル選択
- オペレーター定義のカスタムヒータープロファイル
- より豊富な serial コマンド / 応答制御
- センサ故障や通信故障のステータス出力
- PC とのタイムスタンプ同期方針

## 7. PC Logger / GUI 要件

### 7.1 必須要件

- PC アプリケーションは M5StampS3 から serial データを受信できること
- PC アプリケーションは解析済みデータをディスクへ保存できること
- PC アプリケーションは必要に応じて raw line を保存できること
- PC アプリケーションは行をプロファイルサイクル単位または同等の単位で束ねられること
- PC アプリケーションは不完全なフレームを検出できること
- PC アプリケーションは PC 側の受信タイムスタンプを保持できること
- PC アプリケーションは取得行にセッションメタデータを関連付けられること
- GUI は接続中かつ動作中に受信したデータをログデータとして扱うこと
- GUI は `Record` と `Stop` の操作を持つこと
- GUI は記録区間中に受信したデータのみを CSV データセットとして出力すること
- GUI はスキャンしたポート一覧からシリアルポートを選択できること
- GUI は選択したポートへの接続を開始できること
- GUI は通信確立後に firmware から現在のヒータープロファイルを受信できること
- GUI は firmware から受信したヒータープロファイルを現在のプロファイル状態として保持し利用できること
- GUI はヒータープロファイル編集のための設定モーダルを持つこと
- GUI はヒータープロファイル更新を firmware に送信できること
- GUI は記録中にプロファイル編集操作を無効化すること
- GUI は暴露セグメントのキューイングとラベリングを支援すること
- GUI は出力時に暴露セグメント単位でラベルを適用すること
- GUI は受信データをリアルタイムに可視化すること
- GUI は 2 つのグラフを提供すること
  - 温度・気圧・湿度
  - 10 本のセンサ抵抗トレースとヒーター制御温度
- GUI は以下の表示スパン切り替えを簡単に行えること
  - 10 分
  - 30 分
  - 1 時間
  - 5 時間
  - 全区間
- GUI は実用的なグラフ操作を支援すること
  - パン
  - ズーム
  - 必要に応じた対数表示を含む軸スケール変更
- GUI は軸ごとに対数表示を設定できること
- GUI は将来の Windows 11 実行ファイル化を考慮した構成であること

### 7.2 強く望ましい要件

- アプリケーションはセッション制御用 GUI を提供すること
- アプリケーションは現在の serial 接続状態を表示すること
- アプリケーションは入力データの健全性を表示すること
  - frame completeness
  - valid / invalid 件数
  - 落ちた行や malformed line
- アプリケーションは取得中に step ごとのガス応答を可視化すること
- アプリケーションはオペレーターのメモを支援すること
- GUI は、OS が許す限り、記録中に Windows のアイドルスリープを抑止すること
- GUI は長時間プロット向けに decimation または thinning を支援すること

### 7.3 将来要件

- GUI からのプロファイル選択
- ライブプロットの強化
- 実験テンプレート
- データセットブラウザ
- 学習実行との紐付けおよびベンチマーク結果確認

## 8. データ要件

### 8.1 行単位センサデータ

現在想定しているセンサレコードは以下を含む。

- `frame_id`
- `batch_id`
- `frame_step`
- `host_ms`
- `field_index`
- `gas_index`
- `meas_index`
- `temp_c`
- `humidity_pct`
- `pressure_hpa`
- `gas_kohms`
- `status_hex`
- `gas_valid`
- `heat_stable`
- PC 側受信タイムスタンプ

### 8.2 セッションメタデータ

システムは以下を保存できること。

- セッション識別子
- オペレーター名または ID
- 開始 / 終了日時
- firmware のコミットまたはバージョン
- ヒータープロファイル ID とその完全内容
- センサ ID またはハードウェア識別子
- ボード ID またはシリアルポート
- 暴露ラベル
- 対象ガス種
- 目標濃度
- 濃度単位
- 暴露開始 / 終了タイミング
- 取得できる場合の周囲環境条件
- メモ

セッションメタデータは CSV ヘッダーに格納するものとする。

### 8.3 データセットレベルメタデータ

- train / validation / test 分割方針
- ラベルソースと信頼度
- キャリブレーション文脈
- 実験プロトコルバージョン

## 9. ベンチマーク要件

システムは少なくとも以下の 2 種類の解析モードを支援すること。

- 分類
  - 例: H2S の有無判定、ガスクラス識別
- 回帰
  - 例: H2S 濃度推定

記録データは、少なくとも以下の特徴量を導けるだけの情報を含むこと。

- 各 step のガス抵抗値
- 時系列プロファイル形状
- step 間の比や差分などの派生量
- 温度 / 湿度 / 気圧の文脈情報

初期ベンチマーク方針は以下とする。

- 分類先行のワークフロー
- 実務上の目的として LoD 指向の評価を置く
- ただし初期段階から濃度回帰もスコープ内に含める

LoD の定義基準は以下とする。

- air 測定時の出力をベースラインとする
- air 出力分布の `3 sigma` を閾値基準とする
- 暴露セグメント単位で評価する

推奨する初期濃度ラダーは以下とする。

- `0 ppm`
- `0.25 ppm`
- `0.5 ppm`
- `1 ppm`
- `2 ppm`
- `5 ppm`
- `10 ppm`

推奨する初期成功指標は以下とする。

- 分類の主要指標
  - balanced accuracy
  - Matthews correlation coefficient (MCC)
- 分類の副次指標
  - F1 score
  - AUROC
- 回帰
  - MAE
  - RMSE
  - R²

初期の実務的 LoD 判定ルールは以下とする。

- `mean_air + 3 sigma_air` により air 由来の閾値を決定する
- 暴露セグメント単位で評価する
- 以下を満たす最も低い濃度ラダーを初期実務 LoD と定義する
  - ラベル付き暴露セグメントのうち少なくとも `95%` が air 由来閾値を超える
  - かつ air-vs-H2S のセグメント分類が以下を満たす
    - balanced accuracy `>= 0.80`
    - MCC `>= 0.60`

## 10. 推奨アーキテクチャ方針

### Firmware

- Bosch `BME68x SensorAPI` を継続利用する
- デフォルトのストリーミング転送は serial CSV とする
- プロファイル制御のために単純なテキストコマンド処理を拡張する

### PC アプリケーション

推奨する段階的アプローチ:

1. logger CLI PoC
2. logger core library
3. simple GUI shell
4. richer experiment-management GUI

推奨する初期技術スタック:

- Python `3.9+`
- `venv`
- `pyserial`
- `PySide6`
- `pyqtgraph`

デプロイ方針:

- GUI は Windows 11 向けにパッケージ化できる構成で設計する
- 初期段階から `pyside6-deploy` と相性の良い project structure を優先する
- ツール都合がある場合に限り `PyInstaller` を fallback として保持する

Windows 電源管理方針:

- 記録中の best-effort なスリープ抑止として Win32 `SetThreadExecutionState`
  API を使用する

## 11. 承認済み設計判断

- ヒーター制御の主経路: `parallel mode`
- センサ API の主経路: Bosch `BME68x SensorAPI`
- 初期プロファイル: Bosch 標準 10-step プロファイル
- PC 側開発をこのリポジトリ内で行う: yes
- Python 環境をローカル `venv` で分離する: yes
- 初期ベンチマーク方針: classification-first with LoD-oriented evaluation
- ラベル粒度: exposure-segment based labeling
- 初期 GUI スコープ: minimal GUI with staged expansion
- 初期出力形式: CSV only
- メタデータ格納位置: CSV header
- firmware 動作: continuous streaming after boot
- プロファイル動作:
  - 起動時に 1 つのデフォルトプロファイルを読み込む
  - GUI 駆動のプロファイル更新を支援する
  - 更新済みプロファイルは一時的であり、電源再投入では保持されない
- プロット動作:
  - 10 本の抵抗トレースを常時重ねる
  - ヒーター温度は第 2 軸を用いる
  - 温度と湿度は同一軸
  - 気圧は別軸
  - 軸ごとに対数表示を設定できる
  - 長時間セッション向けのプロット decimation は望ましい

## 12. 承認済み GUI 操作フロー

推奨かつ承認済みの操作フローは以下とする。

1. serial ポートを `Scan`
2. 選択したポートに `Connect`
3. firmware からアクティブなプロファイルを受信
4. ライブプロットを継続更新
5. 次の暴露セグメント用ラベルを準備またはキューイング
6. `Record` を押してデータ保存開始
7. `Start Segment` を押してラベル付き暴露セグメント開始
8. `End Segment` を押してラベル付き暴露セグメント終了
9. `Stop` を押して記録終了および CSV 出力確定

これにより以下を分離する。

- 常時観察
- 明示的な記録
- 明示的な暴露ラベリング

## 13. 承認済み Serial Protocol 方針

### 13.1 Device to PC

firmware はテキスト行を連続出力するものとする。

行ファミリ:

- `[csv] ...`
- `[profile] key=value`
- `[status] key=value`
- `[event] key=value`

### 13.2 PC to Device

GUI は 1 行につき 1 コマンドを送信するものとする。

初期コマンドセット:

- `GET_PROFILE`
- `SET_PROFILE temp=... dur=... base_ms=...`
- `RESET_PROFILE`
- `PING`

### 13.3 プロトコル規則

- CSV ストリーミングはデフォルトで継続する
- 記録中はプロファイル更新コマンドを送信しない
- firmware は制御コマンドに対して短い `[event]`, `[status]`, `[profile]` 行で応答する

## 14. 承認済み CSV メタデータヘッダー形式

CSV ファイルは以下の形式を用いるものとする。

- `# ` で始まるコメント付きメタデータ行
- メタデータは `key=value` 構文
- 最初の非コメント行に通常の CSV ヘッダーを置く

推奨ファイル構造:

```text
# file_format=h2s_benchmark_csv_v1
# exported_at_iso=2026-03-14T13:30:00+09:00
# operator_id=hiromasa
# session_id=20260314_133000_run01
# recording_id=rec_001
# firmware_git_commit=f5a6e7a
# gui_git_commit=<commit-or-dirty>
# board_type=M5StampS3
# sensor_type=BME688
# sensor_id=
# serial_port=/dev/cu.usbmodem4101
# baudrate=115200
# heater_profile_id=default_vsc_10step
# heater_profile_temp_c=320,100,100,100,200,200,200,320,320,320
# heater_profile_duration_mult=5,2,10,30,5,5,5,5,5,5
# heater_profile_time_base_ms=140
# label_target_gas=H2S
# label_unit=ppm
# label_scope=exposure_segment
# concentration_ladder_ppm=0,0.25,0.5,1,2,5,10
# lod_rule=air_mean_plus_3sigma
# notes=
frame_id,batch_id,frame_step,host_ms,field_index,gas_index,meas_index,temp_c,humidity_pct,pressure_hpa,gas_kohms,status_hex,gas_valid,heat_stable,received_at_iso,segment_id,segment_label,segment_target_ppm,segment_start_iso,segment_end_iso
...
```

必須 CSV メタデータキー:

- `file_format`
- `exported_at_iso`
- `operator_id`
- `session_id`
- `firmware_git_commit`
- `gui_git_commit`
- `board_type`
- `sensor_type`
- `serial_port`
- `heater_profile_id`
- `heater_profile_temp_c`
- `heater_profile_duration_mult`
- `heater_profile_time_base_ms`
- `label_target_gas`
- `label_unit`
- `label_scope`

強く望ましいメタデータキー:

- `recording_id`
- `sensor_id`
- `concentration_ladder_ppm`
- `lod_rule`
- `notes`

## 15. 残っている実装詳細

以下の項目は実装詳細レベルでは未確定だが、この v1 仕様を妨げるものではない。

- 濃度ラダーの詳細値は初期暴露実験後に調整される可能性がある
- 最終受け入れ閾値は pilot data analysis 後に調整される可能性がある
- GUI ウィジェット配置の最終詳細
- 個別抵抗トレースを ON / OFF 切り替え可能にするかどうか
- プロット decimation を自動のみとするか、ユーザー設定可能にするか
- serial parsing と error recovery の厳密な挙動
