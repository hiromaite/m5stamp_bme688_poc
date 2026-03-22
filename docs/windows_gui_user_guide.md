# Windows GUI アプリ利用ガイド

この文書は、Windows 上で `bme688_logger` を使って
`M5StampS3 + BME688` の計測を行う試験ユーザー向けの説明書です。

## 起動方法

1. 配布されたフォルダ `bme688_logger` を開きます
2. `bme688_logger.exe` をダブルクリックします
3. 起動中はスプラッシュ画面が表示されます
4. メインウィンドウが開いたら使用可能です

## 画面の見方

左側:

- `Connection`
  - 接続ポートの選択
  - `Scan`
  - `Connect` / `Disconnect`
- `Session Metadata`
  - `Operator`
  - `Segment Label`
  - `Target ppm`
- `Recording`
  - `Record` / `Stop`
  - `Start Segment` / `End Segment`
  - `Clear Plots`
- `Profile`
  - 現在のヒータープロファイル
  - `Profile Settings`
  - `Reset Profile`
  - 保存済みプリセットの選択、読込、保存
- `Stability`
  - 各ヒーターステップの安定ランプ
  - `Stability Settings`
- `Event Log`
  - 接続や記録の履歴

右側:

- `Plot Span`
- `Time Axis`
- 上側グラフ
  - 温度
  - 湿度
  - 気圧
- 下側グラフ
  - 10 本のガス抵抗値
  - ヒーター温度
  - セグメント帯表示

## 基本的な操作手順

### 1. デバイスへ接続する

1. `Scan` を押します
2. 接続先のポートを確認します
3. `Connect` を押します
4. `Status` が `Connected` になり、グラフが更新されれば接続成功です

## 2. 記録を開始する

1. 必要に応じて `Operator`、`Segment Label`、`Target ppm` を入力します
2. `Record` を押します
3. `Recording` セクションが赤く点滅し、記録中であることが表示されます

## 3. セグメントを付ける

1. セグメントを開始したいタイミングで `Start Segment` を押します
2. 必要に応じて `Segment Label` と `Target ppm` を変更します
3. セグメントを終了したいタイミングで `End Segment` を押します

下側グラフの上部には、セグメント帯が表示されます。

## 4. 記録を停止する

1. `Stop` を押します
2. 確認ダイアログで `Yes` を選びます
3. CSV が確定保存されます

## 5. アプリを終了する

1. ウィンドウを閉じます
2. 確認ダイアログで `Yes` を選びます

記録中に終了する場合は、記録停止を伴う確認になります。

## ヒータープロファイルの使い方

### 一時的に変更する

1. `Profile Settings` を押します
2. ステップごとの温度と duration multiplier を入力します
3. `OK` を押します

### デフォルトへ戻す

- `Reset Profile` を押します

### 名前を付けて保存する

1. 保存したいプロファイルを現在値として読み込んだ状態にします
2. `Save Preset` を押します
3. 名前を入力して保存します

### 保存済みプロファイルを使う

1. プルダウンから保存済みプリセットを選びます
2. `Load Preset` を押します

保存済みプリセットは、次回起動時にも読み込まれます。

## 安定判定の見方

- `Stability` セクションには、現在のヒータープロファイルに対応する安定ランプが表示されます
- 色の意味
  - 緑: stable
  - 赤: unstable
  - 灰: まだ履歴不足、または未使用ステップ
- 上部の summary には、現在の安定状況が表示されます

### 安定判定条件を変更する

1. `Stability Settings` を押します
2. 次の値を必要に応じて変更します
   - `Threshold (%)`
   - `Recent Window (s)`
   - `History Window (s)`
   - `Required Stable Channels`
3. `OK` を押します

設定は次回起動時にも保持されます。

## グラフの操作

- `Plot Span`
  - `10 min`, `30 min`, `1 hour`, `5 hours`, `All`
- `Time Axis`
  - `Relative`
  - `Clock`
- マウス操作
  - パン
  - ズーム
  - 凡例クリックによるトレース表示切替

手動で横軸をパンまたはズームすると、`Plot Span` のボタンは全て非選択状態になります。
再び span を使いたい場合は、希望するボタンを押してください。

## 保存ファイル

記録データはアプリの `data` ディレクトリに保存されます。

- 記録中: `*.partial.csv`
- 正常終了後: `*.csv`

もし前回の終了が正常でなかった場合は、起動時に未完了セッションの警告が表示されます。

## 注意事項

- 記録中は `Clear Plots` は無効になります
- 接続中または記録中は、Windows のスリープ抑止が動作する想定です
- `Reset Profile` は firmware 側のデフォルトプロファイルへ戻します

## 困ったとき

- ポートが見えない
  - `Scan` を押してください
  - デバイスの USB 接続を確認してください
- 接続できない
  - 他のシリアルモニタが開いていないか確認してください
- 記録ファイルが `.partial.csv` のまま
  - 前回が異常終了だった可能性があります
  - 内容を確認し、必要なら退避してください
- グラフが多すぎて見づらい
  - 凡例をクリックして不要なトレースを非表示にできます
