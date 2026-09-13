[English](README.md) · [한국어](README_KO.md) · [日本語](README_JA.md)

<p align="center">
  <img src="images/forest300_1.jpeg" alt="Overview of the Cozy Lake Forest scene" width="32%" />
  <img src="images/forest300_2.jpeg" alt="Lakeside village view" width="32%" />
  <img src="images/forest300_3.jpeg" alt="Orchard and garden view" width="32%" />
</p>

# Astra Blender Forest

## Cozy Lake Forest — 300 × 300 m

`Cozy_Lake_Forest_300m` is a Blender Python source package that generates a stylized low-poly forest scene on a **300 × 300 m** site. It creates terrain, a lake and ponds, connected trails, forests, and 12 landmark areas such as a lakeside village, campground, orchard, and lookout.

The package generates the scene inside Blender. It does not include a prebuilt `.blend` or FBX scene.

## Quick start

1. Open the complete repository or package folder in a writable location.
2. In Blender 4.2 or newer, open `Cozy_Lake_Forest_300m/01_build_scene.py` from **Scripting → Text Editor → Open**.
3. Run the script with **Alt+P / Run Script**.
4. Select the generated `CF_CozyLake_300m` scene and save the `.blend` file manually.

The generator uses seed `42` by default and does not automatically save a `.blend` or render a preview. Keep the package folder together because the scripts import the supporting Python modules and JSON configuration from the same directory.

## Default output

| Item | Default |
| --- | ---: |
| Site | 300 × 300 m (90,000 m²) |
| Cells | 36 cells of 50 × 50 m |
| Forest trees | 3,800 |
| Trees including landmark trees | 3,839 |
| Placed instances | 16,573 |
| Reusable mesh assets | 127 |
| Landmark areas | 12 |
| Random seed | 42 |

Repeated objects share mesh datablocks in Blender. The default Unreal export groups repeated assets by cell and asset ID for HISM placement, while unique objects use regular Static Mesh Actors.

## Documentation

The complete English guide is available here:

- [Cozy Lake Forest 300 m guide](Cozy_Lake_Forest_300m/README.md)
- [한국어 사용 가이드](Cozy_Lake_Forest_300m/README_KO.md)
- [日本語ガイド](Cozy_Lake_Forest_300m/README_JA.md)

The package also includes `START_HERE.txt`, `TEST_REPORT.md`, `OPEN_PREVIEWS.html`, and generated statistics in `default_generation_stats.json`.

## Unreal workflow

Run `02_export_unreal.py` in Blender to export one FBX per unique mesh plus placement manifests. Enable **Python Editor Script Plugin** and **Editor Scripting Utilities** in Unreal Editor, then run `03_import_unreal.py` from **Tools → Execute Python Script**.

Collision, production LODs, World Partition, runtime streaming, animation, and gameplay logic are outside the scope of this package. See the detailed guide before using the result in a playable level.

## Validation

The pure-Python test suite contains 30 tests covering geometry, placement, deterministic generation, shared assets, cell bounds, and Blender-to-Unreal transform conversion. Blender and Unreal Editor runtime execution is not included in the recorded validation.

```text
Cozy_Lake_Forest_300m/tests/reports/unit_tests.txt
Cozy_Lake_Forest_300m/tests/reports/full_python_validation.json
```

## License

See [LICENSE](LICENSE).
