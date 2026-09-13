[English](README.md) · [한국어](README_KO.md) · [日本語](README_JA.md)

<p align="center">
  <img src="../images/forest300_1.jpeg" alt="Cozy Lake Forest 全体" width="32%" />
  <img src="../images/forest300_2.jpeg" alt="湖畔の村" width="32%" />
  <img src="../images/forest300_3.jpeg" alt="果樹園と庭園" width="32%" />
</p>

# Cozy Lake Forest — 300 × 300 m

`Cozy_Lake_Forest_300m` は、300 × 300 m の敷地にスタイライズされたローポリ風の森を生成する Blender Python ソースパッケージです。大きな湖、小さな池 2 つ、小川、遊歩道、森、自然物、建物、12 か所のランドマークエリアを作成します。

このプロジェクトは Codex ではなく、ChatGPT との会話を通して作成されました。

完成済みの `.blend` や FBX は含まれていません。Blender でシーンを生成するスクリプトと設定・検証ファイルを収録しています。実行時はフォルダー全体を同じ場所に置いてください。

## 必要環境

- Blender 4.2 以降
- 外部 Python パッケージの追加インストールは不要
- 書き込み可能なパッケージフォルダー

## Blender シーンを生成する

1. `Cozy_Lake_Forest_300m` フォルダー全体を Blender で利用できる場所に置きます。
2. **Scripting → Text Editor → Open** から `01_build_scene.py` を開きます。
3. Text Editor にマウスカーソルを置き、**Alt+P / Run Script** を実行します。
4. 生成された `CF_CozyLake_300m` シーンを確認し、`.blend` を手動で保存します。

デフォルト設定は `cozy_config.json` と seed `42` です。生成スクリプトは `.blend` の保存とプレビューのレンダリングを自動では行いません。再生成すると、このパッケージが所有する前回の 300 m シーンが置き換わるため、手作業の変更は先に保存してください。

## デフォルトの生成規模

| 項目 | 値 |
| --- | ---: |
| 敷地 | 300 × 300 m、90,000 m² |
| セル | 50 × 50 m、6 × 6 = 36 個 |
| 森の樹木 | 3,800 本 |
| ランドマークの樹木を含む樹木数 | 3,839 本 |
| 配置インスタンス | 16,573 個 |
| 再利用メッシュ | 127 個 |
| ランドマーク | 12 か所 |

繰り返し配置するオブジェクトは同じ Mesh データブロックを共有します。地形は 36 個の通常の Static Mesh タイルとして生成され、Unreal Landscape ではありません。

## Unreal へのエクスポートとインポート

Blender で `02_export_unreal.py` を実行すると、固有メッシュごとの FBX、全体の配置マニフェスト、セルごとの JSON が `output/unreal_export/` に出力されます。配置だけを更新する場合は、スクリプト上部の `TRANSFORMS_ONLY = True` を使えます。メッシュを変更した場合や新しいアセットを追加した場合は、フルエクスポートに戻してください。

Unreal Editor で **Python Editor Script Plugin** と **Editor Scripting Utilities** を有効にし、**Tools → Execute Python Script** から `03_import_unreal.py` を実行します。デフォルトでは繰り返しモデルをセルとアセット ID ごとの HISM にまとめます。必要に応じて `PLACEMENT_MODE = 'ACTORS'` に変更できます。

一部のセルだけを更新する場合:

```python
ONLY_CELL_IDS = ['C03_03', 'C04_03']
```

空のリスト `[]` は全セルを意味します。オブジェクトを別セルへ移動した場合は、移動元と移動先の両方を更新するか、全体を更新してください。

## 表示範囲と軽量設定

`05_focus_region.py` で一部のセルやランドマークだけを表示できます。

```python
MODE = 'ZONE'
ZONE_ID = 'camp'
```

全体を表示するには `MODE = 'ALL'`、セルを直接選ぶには `MODE = 'CELLS'` と `CELL_IDS` を使います。軽量化する場合は `presets/cozy_config_light.json` を `cozy_config.json` にコピーして再生成してください。

## ファイルと検証

| ファイル | 役割 |
| --- | --- |
| `01_build_scene.py` | Blender シーン、共有メッシュ、配置を生成 |
| `02_export_unreal.py` | 固有 FBX と配置 JSON を出力 |
| `03_import_unreal.py` | Unreal のアセットと HISM / Actor を配置 |
| `04_validate_blender_scene.py` | Blender シーンのメッシュ共有を検証 |
| `05_focus_region.py` | 選択したセルやランドマークを表示 |
| `OPEN_PREVIEWS.html` | オフラインのプレビューギャラリー |
| `tests/` | 純粋な Python のテストと全体検証 |

純粋な Python の検証では、形状、配置、セル境界、共有メッシュ、決定的な seed、座標変換を対象に 30 テストが成功しています。Blender と Unreal Editor の実行検証、LOD、コリジョン、World Partition、アニメーション、ゲームロジックは含まれていません。

```text
python -m unittest discover -s tests -v
python tests/validate_full_scene.py
```

詳細な英語ガイドは [README.md](README.md)、韓国語ガイドは [README_KO.md](README_KO.md) です。
