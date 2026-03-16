# PC Logger

このディレクトリには、M5StampS3 + BME688 の `parallel mode` ワークフロー向け
PC 側ツール群が含まれています。

## 構成

- `src/serial_logger.py`: serial 受信と CSV 保存を行う CLI ロガー PoC
- `main.py`: packaging を意識した GUI エントリポイント
- `src/gui_app.py`: GUI 実装本体
- `src/app_metadata.py`: アプリ名とバージョン定数
- `src/serial_protocol.py`: 共通 serial 解析ヘルパー
- `pc_logger.pyproject`: Qt project 記述
- `pysidedeploy.spec`: Qt deployment 設定
- `requirements.txt`: Python 依存
- `data/`: 取得ログの既定出力ディレクトリ

## セットアップ

```bash
cd pc_logger
source .venv/bin/activate
pip install -r requirements.txt
```

Windows で実行ファイル化する場合も、まず同じ `requirements.txt` を使って
環境を整えます。

## CLI ロガーの起動

```bash
cd pc_logger
source .venv/bin/activate
python src/serial_logger.py --port /dev/cu.usbmodem4101
```

## GUI の起動

```bash
cd pc_logger
source .venv/bin/activate
python main.py
```

CLI ロガーで利用できるオプション:

```bash
python src/serial_logger.py --help
```

## GUI の現在機能

- ポートスキャン
- connect / disconnect
- ライブステータス表示
- `Record` / `Stop`
- `Start Segment` / `End Segment`
- 現在のヒータープロファイル表示
- 可変長ヒータープロファイル編集（`1..10` ステップ）
- profile reset
- 環境データのライブプロット
- ガス抵抗値とヒーター温度のライブプロット
- 表示スパン切り替え

## CLI ロガーの現在動作

- `115200` baud で受信
- firmware の `[csv]` 行のみを取得
- 解析済み行を `data/session_YYYYmmdd_HHMMSS.csv` に保存
- frame が 10 step に到達すると簡易進捗行を表示

## 出力スキーマ

ロガーは firmware から次の形式の行を受け取る想定です。

```text
[csv] frame_id,batch_id,frame_step,host_ms,field_index,gas_index,meas_index,temp_c,humidity_pct,pressure_hpa,gas_kohms,status_hex,gas_valid,heat_stable
```

保存される CSV は上記列に加えて、以下の列を持ちます。

- `received_at_iso`
- `source_line`

GUI が現在解釈できる行ファミリ:

- `[csv] ...`
- `[profile] key=value`
- `[status] key=value`
- `[event] key=value`

## Packaging 方針

現在の packaging 対象は Windows 11 です。

主経路:

- `PyInstaller`
- `main.spec` を使った `--onefile` パッケージング

fallback:

- `pyside6-deploy`

現在の Windows ビルドメモは [../docs/windows_build.md](../docs/windows_build.md) を参照してください。
