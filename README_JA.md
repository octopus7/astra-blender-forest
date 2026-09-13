[English](README.md) · [한국어](README_KO.md) · [日本語](README_JA.md)

<p align="center">
  <img src="images/forest300_1.jpeg" alt="Cozy Lake Forest 全体" width="32%" />
  <img src="images/forest300_2.jpeg" alt="湖畔の村" width="32%" />
  <img src="images/forest300_3.jpeg" alt="果樹園と庭園" width="32%" />
</p>

# Astra Blender Forest

## Cozy Lake Forest — 300 × 300 m

`Cozy_Lake_Forest_300m` は、300 × 300 m の敷地にローポリ風の森、湖と池、遊歩道、建物、12 のランドマークエリアを生成する Blender Python ソースパッケージです。完成済みの `.blend` や FBX シーンではなく、Blender 内でシーンを生成するスクリプトと関連ファイルを収録しています。

このプロジェクトは Codex ではなく、ChatGPT との会話を通して作成されました。

詳しい手順は [Cozy Lake Forest 日本語ガイド](Cozy_Lake_Forest_300m/README_JA.md)をご覧ください。[英語ガイド](Cozy_Lake_Forest_300m/README.md)と[韓国語ガイド](Cozy_Lake_Forest_300m/README_KO.md)もあります。

## クイックスタート

1. リポジトリ全体、または `Cozy_Lake_Forest_300m` フォルダーを、書き込み可能な場所に置きます。
2. Blender 4.2 以降で **Scripting → Text Editor → Open** を選び、`01_build_scene.py` を開きます。
3. Text Editor にマウスカーソルを置き、**Alt+P / Run Script** を実行します。
4. 生成された `CF_CozyLake_300m` シーンを確認し、`.blend` を手動で保存します。

デフォルトの seed は `42` です。スクリプトは `.blend` の保存やプレビューのレンダリングを自動では行いません。

## デフォルトの規模

- 敷地: 300 × 300 m、90,000 m²
- セル: 50 × 50 m のセル 36 個
- 森の樹木: 3,800 本
- ランドマークの樹木を含む樹木数: 3,839 本
- 配置インスタンス: 16,573 個
- 再利用メッシュ: 127 個
- ランドマークエリア: 12 か所

繰り返し配置するオブジェクトは Blender の Mesh データブロックを共有します。Unreal へのエクスポートでは、セルとアセット ID ごとに繰り返しモデルを HISM としてまとめます。

## Unreal と検証

Blender で `02_export_unreal.py` を実行すると、固有メッシュごとの FBX と配置 JSON が出力されます。Unreal Editor では **Python Editor Script Plugin** と **Editor Scripting Utilities** を有効にしてから、`03_import_unreal.py` を実行します。

純粋な Python の検証は 30 テストで実施済みです。Blender と Unreal Editor の実行検証、コリジョン、LOD、World Partition、アニメーション、ゲームロジックは含まれません。詳しい範囲は `Cozy_Lake_Forest_300m/TEST_REPORT.md` をご確認ください。
