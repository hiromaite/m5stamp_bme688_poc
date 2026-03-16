# Ver.01.00 リリース前チェックリスト

## 目的

`M5StampS3 + BME688` のファームウェアと、Windows 11 上で動作する
PC ロガー GUI を `Ver.01.00` として固定するための確認項目です。

## スコープ

- ファームウェア
  - BME688 `parallel mode`
  - 可変長 `1..10` ステップのヒータープロファイル
  - シリアル制御 (`PING`, `GET_PROFILE`, `SET_PROFILE`, `RESET_PROFILE`)
- PC ロガー GUI
  - ポートスキャン
  - Connect / Disconnect
  - Record / Stop
  - Start Segment / End Segment
  - プロファイル取得 / 更新 / リセット
  - リアルタイムグラフ
  - CSV 保存
- Windows 11 向け実行ファイル
  - `PyInstaller` による `.exe` 生成

## チェック項目

### 1. ファームウェアのビルドと書き込み

- [ ] `pio run -e m5stack-stamps3` が成功する
- [ ] `pio run -e m5stack-stamps3 -t upload` が成功する
- [ ] シリアルモニタで起動後のログを確認できる

### 2. ファームウェアの基本動作

- [ ] `GET_PROFILE` で現在のプロファイルが返る
- [ ] `PING` で `[status] pong=true` が返る
- [ ] `SET_PROFILE` で `1..10` ステップの任意長プロファイルを設定できる
- [ ] `RESET_PROFILE` でデフォルトプロファイルに戻る
- [ ] `[csv]` 行が継続出力される
- [ ] `frame complete` が設定したステップ数と一致する

### 3. GUI の基本動作

- [ ] GUI が起動する
- [ ] ポートスキャンで対象ポートが見える
- [ ] Connect / Disconnect が動作する
- [ ] ライブプロットが更新される
- [ ] `10 min / 30 min / 1 hour / 5 hours / All` の表示スパン切替が動作する
- [ ] ガス抵抗 10 系列が描画される
- [ ] ヒーター温度が第 2 軸で描画される

### 4. GUI の記録機能

- [ ] `Record` 中のみ CSV が保存される
- [ ] `Start Segment / End Segment` が動作する
- [ ] セグメント情報が CSV に反映される
- [ ] CSV ヘッダーにメタデータが出力される

### 5. GUI のプロファイル編集

- [ ] 設定モーダルで最大 10 ステップを個別入力できる
- [ ] 温度と duration の片側のみ入力時にエラーになる
- [ ] 温度も duration も空欄の行は未使用ステップとして除外される
- [ ] 3-step などの短いプロファイルを反映できる
- [ ] `Reset Profile` でデフォルトへ戻せる

### 6. Windows 実行ファイル

- [ ] Windows 11 上で `pip install -r requirements.txt` が成功する
- [ ] `pyinstaller --clean main.spec` が成功する
- [ ] `dist/bme688_logger.exe` が起動する
- [ ] `.exe` で Connect / Record / Segment / Profile Update / CSV 保存のスモークテストに成功する

## 既知の保留事項

- 長時間表示時の decimation は未実装
- Windows コード署名は未実施
- アプリアイコンは未設定

## Ver.01.00 判定

以下を満たした時点で `Ver.01.00` として固定する。

- 上記チェック項目がすべて完了している
- ドキュメントが現行実装と一致している
- リリースノートを作成済みである
- Git タグ `v01.00` を作成済みである
