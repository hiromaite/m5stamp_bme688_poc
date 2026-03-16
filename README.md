# M5StampS3 BME688 H2S ベンチマーク

このリポジトリには、`M5StampS3` 向けのファームウェアと、
`BME688` のヒータープロファイル応答を収集するための PC 側 Python
アプリケーションが含まれています。目的は、`H2S` センサとしての
`BME688` を評価することです。

## 構成

- `src/main.cpp`
  - `M5StampS3` 向けファームウェア
  - Bosch `BME68x SensorAPI`
  - `parallel mode`
  - シリアル経由でのランタイムヒータープロファイル制御
- `pc_logger/`
  - Python GUI / CLI ロガー
  - ライブプロット
  - 記録と暴露セグメントのラベリング
  - GUI からのヒータープロファイル編集
- `docs/requirements_v1.md`
  - 承認済みのシステム要件ベースライン

## 現在のベースライン

現在の `main` ブランチには次の内容が含まれています。

- 可変長ヒータープロファイル（`1..10` ステップ）
- ライブプロットと表示スパン切り替えを備えた GUI
- プロファイル編集およびリセット操作
- メタデータヘッダー付き CSV 記録

## Firmware

ビルド:

```bash
~/.platformio/penv/bin/pio run -e m5stack-stamps3
```

アップロード:

```bash
~/.platformio/penv/bin/pio run -e m5stack-stamps3 -t upload --upload-port /dev/cu.usbmodem4101
```

## PC Logger

詳細は [pc_logger/README.md](pc_logger/README.md) を参照してください。

### ビルド (PyInstaller)

Windows でスタンドアロン実行可能ファイルをビルドするには:

```bash
cd pc_logger
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller pyinstaller-hooks-contrib
pyi-makespec --onefile --windowed main.py
# main.spec を編集: pathex=['src'], hiddenimports, datas, hookspath を設定
pyinstaller --clean main.spec
```

ビルドされた実行可能ファイルは `dist/main.exe` に生成されます。

### 実行

Python 環境を構築できる場合は、以下の手順で GUI を起動できます。

```bash
cd pc_logger
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

または、ビルドされた実行可能ファイルを使用:

```bash
dist/main.exe
```

```bash
cd pc_logger
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Windows パッケージング

Windows 配布に向けた準備はこのリポジトリ内で進めています。現在の
Windows ビルドメモは [docs/windows_build.md](docs/windows_build.md) にあります。
