# Cozy Broken Bridge v2

## 바로 사용할 파일

**`models/SM_BrokenBridge_v2.glb`** 는 완성된 다리 모델이다. 2K BaseColor·Normal·ORM을 내장했다. Blender 스크립트를 실행하지 않고도 가져올 수 있다.

**`01_build_blender_scene_v2.py`** 는 다리 메시를 다시 만들고, Blender의 조명·강바닥·강물 재질까지 구성한다. GLB를 불러오기만 하는 스크립트가 아니다. `data/bridge_recipe.json`의 부품 위치와 파손 윤곽을 읽어 저폴리 메시와 UV를 직접 생성한다.

기존 v1 및 300m 숲 파일은 변경하지 않았다. 이 패키지는 별도 v2다.

## 다리 최적화 결과

| 항목 | v1 | v2 |
|---|---:|---:|
| 다리 삼각형 | 27,016 | **6,732** |
| 원본 대비 비율 | 100% | **24.92%** |
| UV·노멀 경계 분리를 포함한 정점 레코드 | 56,824 | 14,352 |
| 완성형 메시 / 재질 | 1 / 1 | 1 / 1 |
| 내장 텍스처 | 2K × 3장 | **2K × 3장 유지** |
| 중앙의 열린 폭 | 약 2.339m | 약 2.339m |

크기는 길이 11.891m, 폭 4.229m, 높이 3.218m다. 단위는 미터이며 제작 좌표는 X=다리 길이, Y=다리 폭, Z=높이다. GLB는 Y-up으로 변환했다. 원점은 양쪽 둑의 발판 높이에 가까운 중앙 빈 공간이며 기초가 아래로 내려간다.

다리 전체에 일괄 Decimate를 적용하지 않았다. 판자·기둥의 실제 끝단 윤곽은 남기고 중간 길이 분할을 없앴다. 늘어진 판자, 큰 파편, 양쪽 발판, 난간 및 밧줄의 곡선, 주요 버섯 위치를 유지했다. 밧줄의 추가 꼬임 가닥, 이끼의 옆면·바닥면, 잎의 중복 뒷면과 과도한 버섯 분할을 줄였다. 나뭇결·오염·썩은 단면·잔이끼는 기존 아틀라스의 표현을 사용한다. 얇은 잎과 이끼 때문에 재질은 양면이다.

`previews/06_v1_v2_comparison.jpg`는 같은 시점의 실제 GLB 렌더 비교다. 3개 시점에서 이진 실루엣 중첩을 측정한 결과 약 96.7~97.3%였다. 이것은 **v1 모델과 v2 모델의 비교**이며, AI 레퍼런스 이미지와의 일치도나 외관 품질을 뜻하지 않는다.

텍스처를 축소하지 않았으므로 GLB/ZIP 용량이 삼각형 수처럼 1/4로 줄어드는 것은 아니다.

## Blender에서 실행

ZIP 전체를 압축 해제한다. Blender의 **Scripting → Open → `01_build_blender_scene_v2.py` → Run Script 또는 Alt+P** 순서로 실행한다. 대상 버전은 Blender 4.2 이상이다. Blender 기본 Python과 NumPy만 사용하므로, 씬 생성에 별도 pip 설치는 필요하지 않도록 작성했다.

새 `CF_BrokenBridge_v2` 씬을 만든다. 기존 작업 씬을 지우지 않으며, 다시 실행하면 이름에 `.001` 등이 붙은 새 씬이 만들어진다. 생성 후 F12로 렌더하고, File → Save As로 `.blend`를 저장한다. 전달 파일에는 미리 생성된 `.blend`는 포함하지 않았다.

스크립트 내용만 붙여넣어 경로를 찾지 못하면 파일 위쪽의 `PACKAGE_DIR`에 압축 해제한 패키지 폴더 경로를 지정한다. 스크립트를 Open으로 열면 보통 수정이 필요 없다.

### 생성되는 씬

| 컬렉션 | 구성 |
|---|---|
| `01_BRIDGE_6732_TRIS` | 텍스처가 적용된 다리. 기본은 단일 메시 |
| `02_RIVER_AND_BANKS` | 강바닥, 두 둑, 강물 볼륨, 주변 돌·갈대·수련 잎 |
| `03_LIGHTS_AND_CAMERAS` | 따뜻한 태양, 큰 보조광 2개, Hero·Top·Detail 카메라 |

**6,732삼각형은 다리 본체의 수치다.** 새로 추가한 전시용 강바닥·수면·둑·장식은 별도다. 기본 설정에서는 환경 배치를 포함한 전체 씬이 9,650삼각형이며, 조명·카메라는 여기에 삼각형을 추가하지 않는다. 반복 배치되는 돌·갈대·수련은 각각 동일 메시 데이터블록을 공유한다.

### 강물·강바닥 재질

강물은 평면 색상만 넣은 바닥이 아니라, 두께를 가진 닫힌 수체와 재질 노드로 구성한다. Principled의 투과, IOR 1.333, 낮은 거칠기, 두 겹의 잔물결 Bump, 청록색 Volume Absorption을 연결했다. 잔물결은 실제 메시 분할을 추가하지 않는다. 프레임 1~240에서 텍스처 좌표가 이동한다.

강바닥에는 모래·진흙·자갈의 색 변화와 미세 Bump를, 둑에는 젖은 모래에서 풀밭으로 이어지는 색 변화와 다리 진입 산책로를 설정했다. 기본 렌더 경로는 **Cycles**다. Eevee로 변경하면 투과·볼륨의 외관이 다를 수 있다.

**Blender의 절차적 강물 노드·볼륨·조명은 다리 GLB에 포함하지 않았다.** 동일한 노드 구성의 엔진 자동 이식도 제공하지 않는다. Unreal에서는 별도 물 재질로 구성해야 한다. `02_export_bridge_v2.py`도 강물과 조명을 제외하고 다리만 내보낸다.

## 설정 바꾸기

`scene_config.json`을 수정하고 생성 스크립트를 다시 실행한다.

| 설정 | 의미 |
|---|---|
| `build_environment` | 강바닥·강물·둑 생성 여부 |
| `environment_decoration` | 돌·갈대·수련 장식 추가 여부 |
| `build_modular_parts` | 다리를 좌측·우측·잔해 3개 메시로 생성 |
| `show_instance_example` | 같은 메시를 공유하는 다리 예제 2개 추가 |
| `water_level_m` | 수면 높이, 기본 -0.68m |
| `water_roughness` | 수면 거칠기 |
| `water_transmission` | 수면 투과 비율 |
| `water_absorption_density` | 깊이에 따른 색 흡수 정도 |
| `water_ripple_strength` / `water_ripple_distance_m` | 잔물결 세기·크기 |
| `render_samples` | Cycles 렌더 샘플 수, 기본 64 |
| `pack_textures` | Blender 이미지 데이터에 텍스처 패킹 |

## 파일 구성

`models/SM_BrokenBridge_v2.glb`는 전체 다리 1개 메시다. `modular/BrokenBridge_Modular_v2.glb`는 좌측·우측·잔해를 구분한 3개 메시이며 같은 2K 재질을 공유한다. `modular/Reuse_3_Instances_v2.glb`는 하나의 메시 인덱스를 세 노드가 참조하는 실제 재사용 예제다. `placement_transforms_v2.json`에는 동일 다리의 예제 트랜스폼을 기록했다. 이 데이터가 엔진의 HISM으로 자동 변환되는 기능까지 포함한 것은 아니다.

`02_export_bridge_v2.py`는 Blender에서 수정한 다리를 `models/SM_BrokenBridge_v2_blender_export.glb`로 내보낸다. 제공된 원래 v2 GLB를 덮어쓰지 않는다. `03_validate_blender_scene_v2.py`는 생성된 씬에서 삼각형·UV·재질·강물 노드를 검사하고, 사용자 환경의 실제 결과를 `validation/BLENDER_RUNTIME_USER_RESULT.json`에 기록한다.

`source/`에는 저폴리 메시 생성기, 공통 메시/GLB 작성 코드, 환경 형상 생성기, 기존 텍스처 합성기, GLB 검사기, 별도 렌더러의 미리보기 소스가 들어 있다. `data/bridge_recipe.json`의 고정 부품 위치와 파손 외곽을 수정해 재생성할 수 있다.

## 충돌·통행·재사용

다리 중앙에는 연결된 발판이 없다. 낮은 중앙 잔해도 발판 높이에 닿지 않는다. 실제 게임에서 점프까지 차단하려면 캐릭터 이동·점프·내비게이션 및 차단 볼륨을 별도로 설정해야 한다.

`collision/Deck_Proxies.glb`는 기존의 양쪽 발판용 보조 박스 2개를 유지했다. 자동 적용되는 충돌 설정이 아니다. **다리 전체에 단일 Convex Hull을 만들면 빈 중앙까지 충돌면으로 덮일 수 있으므로**, 양쪽을 분리해서 설정한다. 콜리전과 주변 강바닥은 다리 본체의 삼각형 수에서 제외했다.

같은 다리를 여러 번 사용할 때는 완성형 메시 데이터를 공유하고 트랜스폼만 바꾼다. Blender 생성기의 예제도 `instance.data = original.data` 구조를 사용한다. v2에는 별도 LOD 체인, 자동 엔진 HISM 생성 또는 게임 프로젝트 파일은 포함하지 않는다.

## 텍스처·레퍼런스

이번 v2에서는 새 AI 이미지를 생성하지 않았다. v1에서 전달된 2K 색상 아틀라스 및 노멀·ORM을 유지했고, 재질별 크롭 원본과 합성 코드도 함께 넣었다. 미세 노멀·AO·Height는 원래 색상 텍스처에서 추정한 값이며 **고해상도 메시를 저해상도 메시로 베이크한 결과가 아니다.**

GLB와 Blender 생성기는 `Normal_GL`을 사용한다. `Normal_DX`도 별도 편집용으로 동봉했다. ORM은 R=AO, G=Roughness, B=Metallic이다. 색상 맵은 sRGB, 노멀과 ORM은 Non-Color로 설정한다.

`reference/AI_concept_reference.png`는 앞서 생성한 설계 참고 이미지다. 이미지 안의 폴리곤 수·LOD·형식 등의 문구는 이번 납품의 사양이 아니다. 실제 사양은 이 문서와 `validation/model_stats_v2.json`을 기준으로 한다.

## 검증 범위

완성형·분리형·재사용 예제·콜리전 GLB 4개를 실제로 다시 읽고 검사했다. 버퍼·인덱스·UV·노멀·탄젠트·삼각형 면적·내장 2K PNG를 검사하고 Trimesh 재로딩을 통과했다. 순수 Python 소스/기하 데이터 검사 43개도 통과했다.

**Blender와 Unreal 프로그램 안에서 실행하거나 Cycles로 렌더링한 검증은 하지 못했다.** `previews/01`~`04`는 실제 전달 GLB를 VTK로 다시 불러온 렌더다. `05_river_layout_vtk.jpg`는 동일 환경 형상을 사용하는 **배치 미리보기**이며, 물은 VTK용 근사 표현이다. Blender 물 재질 렌더 결과로 제시한 이미지가 아니다.

검사는 프로젝트 자체 검사이며 Khronos 공식 Validator 결과는 아니다. 자세한 기록은 `validation/`에 있다.

## 일반 Python으로 재생성 — 선택 사항

Blender 안에서 씬을 생성할 때는 아래 설치가 필요 없다. Blender 밖에서 GLB나 미리보기를 다시 만들 때만 사용한다.

```sh
python -m pip install -r source/requirements.txt
python source/generate_bridge_v2.py
python source/validate_glb.py
python source/test_package.py
```

GLB 생성 자체에는 NumPy만 필요하다. 텍스처 합성에는 Pillow·SciPy, 외부 검사는 Trimesh, 별도 미리보기에는 VTK가 추가로 필요하다. `source/render_previews.py`와 `source/render_river_preview.py`는 Blender가 아닌 VTK 렌더러다.

Blender 명령줄 실행 예:

```sh
blender --background --python 01_build_blender_scene_v2.py -- --save-blend --render
```

생성 스크립트가 성공하면 패키지 폴더에 `.blend`를 저장하고 `previews/Blender_Hero_v2.png`를 렌더하도록 작성했다. 이 명령의 실제 Blender 실행은 제작 환경에서 검증하지 않았다.
