[English](README.md) · [한국어](README_KO.md) · [日本語](README_JA.md)

<p align="center">
  <img src="images/forest300_1.jpeg" alt="Cozy Lake Forest 전체 모습" width="32%" />
  <img src="images/forest300_2.jpeg" alt="호숫가 마을 모습" width="32%" />
  <img src="images/forest300_3.jpeg" alt="과수원과 정원 모습" width="32%" />
</p>

# Astra Blender Forest

## Cozy Lake Forest — 300 × 300m

`Cozy_Lake_Forest_300m`은 300 × 300m 부지에 로우폴리 숲, 호수와 연못, 산책로, 건물과 12개 랜드마크 구역을 생성하는 Blender Python 소스 패키지입니다. 완성된 `.blend`나 FBX 장면이 아니라 Blender에서 장면을 만드는 스크립트와 지원 파일을 제공합니다.

자세한 사용법은 [Cozy Lake Forest 한국어 가이드](Cozy_Lake_Forest_300m/README_KO.md)를 참고하세요. [영어 가이드](Cozy_Lake_Forest_300m/README.md)와 [일본어 가이드](Cozy_Lake_Forest_300m/README_JA.md)도 제공됩니다.

## 빠른 시작

1. 전체 저장소 또는 `Cozy_Lake_Forest_300m` 폴더를 쓰기 가능한 위치에 둡니다.
2. Blender 4.2 이상에서 **Scripting → Text Editor → Open**으로 `01_build_scene.py`를 엽니다.
3. 텍스트 편집기에 마우스를 두고 **Alt+P / Run Script**를 실행합니다.
4. 생성된 `CF_CozyLake_300m` 씬을 확인한 뒤 `.blend`를 직접 저장합니다.

기본 seed는 `42`입니다. 스크립트는 `.blend` 저장과 미리보기 렌더를 자동으로 실행하지 않습니다.

## 기본 규모

- 부지: 300 × 300m, 90,000m²
- 셀: 50 × 50m 셀 36개
- 숲 나무: 3,800그루
- 랜드마크 나무 포함 나무: 3,839그루
- 배치 인스턴스: 16,573개
- 재사용 메시: 127개
- 랜드마크 구역: 12곳

반복 오브젝트는 Blender Mesh 데이터블록을 공유합니다. Unreal 내보내기에서는 셀과 에셋 ID를 기준으로 반복 모델을 HISM으로 묶습니다.

## Unreal 및 검증

Blender에서 `02_export_unreal.py`를 실행하면 고유 메시별 FBX와 배치 JSON을 만듭니다. Unreal Editor에서는 **Python Editor Script Plugin**과 **Editor Scripting Utilities**를 활성화한 뒤 `03_import_unreal.py`를 실행합니다.

순수 Python 검증은 30개 테스트로 수행되었습니다. Blender와 Unreal Editor의 실제 실행 검증, 콜리전, LOD, World Partition, 애니메이션과 게임 로직은 포함하지 않습니다. 자세한 범위는 `Cozy_Lake_Forest_300m/TEST_REPORT.md`에서 확인할 수 있습니다.
