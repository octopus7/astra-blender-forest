# Cozy Broken Bridge — 실제 GLB 모델 패키지

## 바로 사용할 파일

**`models/SM_BrokenBridge.glb`** 를 가져오면 된다. 생성 스크립트 실행은 필요 없다.
메시, UV, 노멀, 탄젠트, 재질, 2K BaseColor·Normal·ORM 이미지가 모두 GLB에 내장되어 있다.
외부 텍스처 경로를 찾을 필요가 없는 완성형이다. 기존 300m 숲 패키지는 변경하지 않았다.

중앙 경간이 무너지고, 양쪽 받침 부분만 남은 다리다. 연결된 바닥판·난간·밧줄은 없다.
쪼개진 들보와 매달린 판자, 검게 오염된 목재와 썩은 단면, 이끼·덩굴·버섯을 넣었다.
석재 기초와 바닥 잔해도 포함한다. 호수·숲·지면은 포함하지 않는다.

## 파일 구성

| 파일 | 용도 |
|---|---|
| `models/SM_BrokenBridge.glb` | 전체 다리. 메시 1개·재질 1개로 배치하기 좋은 버전 |
| `modular/BrokenBridge_Modular.glb` | 좌측·우측·잔해를 각각 편집할 수 있는 3개 노드 버전 |
| `modular/SM_BrokenBridge_Left.glb` | 좌측만, 별도 로컬 원점 |
| `modular/SM_BrokenBridge_Right.glb` | 우측만, 별도 로컬 원점 |
| `modular/SM_BrokenBridge_Debris.glb` | 낮게 떨어진 중앙 잔해만 |
| `modular/placement_transforms.json` | 분리된 부분을 원래 위치에 조립할 트랜스폼 |
| `modular/Reuse_3_Instances.glb` | 한 메시를 3개 노드가 참조하는 실제 인스턴스 예제 |
| `collision/Deck_Proxies.glb` | 양쪽 발판용 박스 2개. 엔진에서 직접 콜리전으로 지정할 보조 형상 |
| `textures/` | 내장한 텍스처의 외부 PNG와 편집용 보조 맵 |
| `texture_sources/` | 이전 합성 아틀라스와 재질별 13개 크롭 원본 |
| `source/` | 메시 생성, 텍스처 합성, 검사, 미리보기 렌더링 소스 |

## 실제 모델 수치

전체 완성형은 **27,016 삼각형**, UV/노멀 경계 분리를 포함한 **56,824 정점**, **재질 1개**다.
외곽의 돌까지 포함한 크기는 길이 약 **11.89m**, 폭 **4.23m**, 높이 **3.24m**다.
목재 59개, 가시 형태의 파편 63개, 돌 40개, 버섯 36개, 이끼 덩어리 103개,
덩굴 16줄기와 잎 144개 등이 들어 있다. 하나의 정적 메시 안에 합쳐진 구성 요소 수다.

원점은 중앙 빈 공간의 중심, 양쪽 둑의 발판 높이 부근에 있다. 기초와 잔해는 원점보다 아래로 내려간다.
원본 설계 좌표는 X=길이, Y=폭, Z=위쪽이며 단위는 미터다. GLB에는 Y-up으로 변환하여 기록했다.
분리형 파일의 조립 위치는 `placement_transforms.json`에 Z-up·미터로 명시했다.

## Blender / Unreal 사용

Blender에서는 `File → Import → glTF 2.0 (.glb/.gltf)`에서 완성형 또는 분리형을 선택한다.
가져온 뒤 Material Preview에서 텍스처를 확인한다.
원래 상태를 편집하려면 분리형, 여러 곳에 동일한 다리를 배치하려면 완성형이 편하다.
선택 사항으로 `source/import_to_blender.py`도 제공한다.

Unreal에서는 glTF 가져오기를 이용해 완성형을 하나의 Static Mesh 자산으로 만든 뒤 재사용한다.
개별 배치마다 메시 파일을 다시 가져오지 말고 같은 자산에 위치·회전·스케일을 적용한다.
`Reuse_3_Instances.glb` 안에서도 실제로 메시 인덱스 0을 세 노드가 공유한다.
이 glTF 노드 구조가 엔진의 HISM으로 자동 변환되는 것까지 보장하는 예제는 아니다.

### 파손 구간과 콜리전

**전체 다리에 단일 Convex Hull을 만들면 중앙 빈 구간까지 막힌 충돌면이 생길 수 있다.**
양쪽 발판에 각각 별도 콜리전을 지정해야 한다. 보조 박스 모델은 자동 적용되는 콜리전이 아니다.
`Deck_Proxies.glb`를 참고해 엔진에서 따로 설정한다. 장식용 잎·버섯·가는 파편까지 충돌 처리할 필요는 없다.

이 모델에는 두 둑을 이어 주는 경로가 없다. 게임에서 점프까지 포함해 통행을 완전히 차단하려면
캐릭터의 점프 거리, 차단 볼륨, 내비게이션도 함께 설정한다. 이 ZIP은 게임플레이 설정을 실행하지 않는다.
LOD, 풍화 애니메이션, 자동 HISM 구성, 게임 엔진 프로젝트 파일은 포함하지 않았다.

## 텍스처와 출처

직전 작업에서 제공된 `T_CB_BaseColor.png` 합성 아틀라스를 재사용했다.
이번 수정에서 새 AI 이미지를 생성한 것은 아니다. 해당 이미지를 목재·썩은 단면·이끼·버섯 갓·주름·밧줄·금속·잎·돌 등
13개 용도별 영역으로 나누고, 가장자리 패딩과 색 보정을 적용해 다시 합성했다.
실제 사용 영역은 `textures/atlas_layout.json`에서 확인할 수 있다.

`reference/AI_concept_reference.png`는 앞서 생성한 **설계 참고 이미지**다.
그 이미지 안에 그려진 폴리곤 수·LOD·파일 형식 등의 글자는 납품 파일의 사양이 아니다.
실제 모델의 수치는 위 표기와 `validation/model_stats.json`을 기준으로 한다.
실제 GLB를 다시 가져와 렌더링한 결과만 `previews/`에 넣었다.

| 맵 | 용도 |
|---|---|
| BaseColor | 색상 아틀라스 |
| Normal_GL | GLB에 내장한 OpenGL 방향 탄젠트 노멀 |
| Normal_DX | 별도로 제공한 녹색 채널 반전 버전 |
| ORM | R=AO, G=Roughness, B=Metallic |
| Roughness | 독립 거칠기 맵 |
| AO_Derived / Height_Derived | 텍스처 밝기에서 추정한 보조 맵 |

노멀·AO·높이는 **고해상도 원본 메시에서 베이크한 맵이 아니다.** 색상 텍스처로부터 추정한 표면 디테일이다.
썩어서 부러진 외곽선과 판자의 구멍, 돌·버섯·덩굴 등은 실제 메시로 만들었다.

## 검증한 범위

7개 GLB 모두 구조·버퍼·인덱스·UV·노멀·탄젠트·삼각형 면적·내장 PNG 검사를 통과했다.
모든 파일을 Trimesh로 다시 불러왔고, 완성형과 분리형의 조립 경계가 일치하는 것도 검사했다.
인스턴스 예제의 1개 메시 / 3개 노드 구조, 양쪽 콜리전 사이의 빈 공간도 확인했다.

완성형은 **VTK의 별도 glTF 가져오기 기능으로 다시 불러온 뒤 4개 시점에서 실제 렌더링**했다.
미리보기의 조명과 회녹색 바닥은 렌더링용이며 GLB에 들어 있지 않다.

Blender·Unreal 프로그램 안에서의 실행 검증은 하지 않았다.
검사는 프로젝트 자체 검사이며 Khronos 공식 glTF Validator 실행 결과가 아니다.
세부 결과는 `validation/`에 들어 있다.

## 재생성 — 선택 사항

수정하거나 다시 만들 때만 실행한다. 이미 완성된 GLB를 이용할 때는 필요 없다.

```sh
python -m pip install numpy Pillow scipy
python source/compose_textures.py
python source/build_broken_bridge.py
```

검사는 `trimesh`, 미리보기 렌더링은 `vtk`가 추가로 필요하다.
`source/tested_versions.json`은 실제 제작 환경의 버전 기록이다.

## 형식·가져오기 공식 문서

- Blender glTF: https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html
- Unreal glTF import: https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-gltf-files-into-unreal-engine
- Khronos glTF 2.0: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
