# Ver.02.00 リリース前チェックリスト

## 目的

`Ver.01.00` 以降に追加した運用性・性能改善を含めて、
`M5StampS3 + BME688` のファームウェアと PC ロガー GUI を
`Ver.02.00` として固定するための確認項目です。

## スコープ

- ファームウェア
  - BME688 `parallel mode`
  - 可変長 `1..10` ステップのヒータープロファイル
  - シリアル制御 (`PING`, `GET_PROFILE`, `SET_PROFILE`, `RESET_PROFILE`)
  - プロファイル入力パースの厳格化
  - 通常運転時の冗長ログ削減
- PC ロガー GUI
  - ポートスキャンと有力ポートの自動選択
  - Connect / Disconnect
  - Record / Stop
  - Start Segment / End Segment
  - プロファイル取得 / 更新 / リセット
  - リアルタイムグラフ
  - 表示スパン切替
  - Relative / Clock 時間軸
  - `Clear Plots`
  - CSV 保存
  - 長時間運用向け描画性能改善
- Windows 11 向け実行ファイル
  - `PyInstaller` による `bme688_logger.exe` 生成

## チェック項目

### 1. ファームウェアのビルドと書き込み

- [x] `pio run -e m5stack-stamps3` が成功する
- [x] `pio run -e m5stack-stamps3 -t upload` が成功する
- [x] シリアルモニタで起動後のログを確認できる

### 2. ファームウェアの基本動作

- [x] `GET_PROFILE` で現在のプロファイルが返る
- [x] `PING` で `[status] pong=true` が返る
- [x] `SET_PROFILE` で `1..10` ステップの任意長プロファイルを設定できる
- [x] `RESET_PROFILE` でデフォルトプロファイルに戻る
- [x] 不正なプロファイル文字列を reject できる
- [x] `[csv]` 行が継続出力される
- [x] `frame complete` が設定したステップ数と一致する

### 3. GUI の基本動作

- [x] GUI が起動する
- [x] ポートスキャンで対象ポートが見える
- [x] 有力なポートが自動選択される
- [x] Connect / Disconnect が動作する
- [x] ライブプロットが更新される
- [x] `10 min / 30 min / 1 hour / 5 hours / All` の表示スパン切替が動作する
- [x] `Relative / Clock` の時間軸切替が動作する
- [x] ガス抵抗 10 系列が描画される
- [x] ヒーター温度が第 2 軸で描画される
- [x] `Clear Plots` が期待どおり動作する

### 4. GUI の記録機能

- [x] `Record` 中のみ CSV が保存される
- [x] `Start Segment / End Segment` が動作する
- [x] セグメント情報が CSV に反映される
- [x] CSV ヘッダーにメタデータが出力される
- [x] ログ表示が無制限に増え続けない

### 5. GUI の性能と保持

- [x] 長時間運用で描画性能が実用的である
- [x] 7 時間保持ウィンドウが入っている
- [x] 手動パンやオートスケール後もトレースが復帰する
- [x] Relative 時間軸ラベルがレンジ変更に追従する

### 6. GUI のプロファイル編集

- [x] 設定モーダルで最大 10 ステップを個別入力できる
- [x] 温度と duration の片側のみ入力時にエラーになる
- [x] 温度も duration も空欄の行は未使用ステップとして除外される
- [x] 3-step などの短いプロファイルを反映できる
- [x] `Reset Profile` でデフォルトへ戻せる

### 7. Windows 実行ファイル

- [x] Windows 11 上で `pip install -r requirements.txt` が成功する
- [x] `pyinstaller --clean main.spec` が成功する
- [x] `dist/bme688_logger.exe` が起動する
- [x] `.exe` で Connect / Record / Segment / Profile Update / CSV 保存のスモークテストに成功する

## 既知の保留事項

- Windows コード署名は未実施
- アプリアイコンは未設定
- 7 時間を超える長時間保持では、古い領域の粗視化は未実装

## Ver.02.00 判定

以下を満たした時点で `Ver.02.00` として固定する。

- 上記チェック項目がすべて完了している
- ドキュメントが現行実装と一致している
- リリースノートを作成済みである
- Git タグ `v02.00` を作成済みである
