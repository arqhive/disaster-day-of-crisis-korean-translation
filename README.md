# 디재스터 데이 오브 크라이시스 (Wii) 한글 패치

*Disaster: Day of Crisis* (Wii, 일본판 `RDZJ01`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

**제작: arqhive** · **최신 버전: [v0.1](../../releases/tag/v0.1)**

- 대사 전체를 한글화했습니다(스테이지 대사, 무전·라디오 방송, 조작 안내, 컷신 자막 65편).
- 메뉴와 게임 안 데이터를 한글화했습니다(타이틀·설정·일시정지 메뉴, 세이브 메시지, 재해 파일, 무기·아이템 설명, 칭호, 레스큐 목록).
- 글씨가 그려진 이미지 209장을 한글화했습니다(튜토리얼, 인물·장소 소개, 로딩 힌트, 스테이지 제목, 홈 버튼, 스트랩 경고).
- 게임 폰트의 한자 자리에 한글 957자를 새로 그려 넣었습니다.
- **바뀐 게임 파일에만 차분을 적용하는 패처로 배포합니다. ISO, WBFS 등 덤프 형태와 상관없이 적용됩니다.**

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판 디스크 이미지(게임 ID `RDZJ01`). 북미판·유럽판에는 적용할 수 없습니다.
  - ISO, WBFS 모두 됩니다. 아래 지원 형식을 참고하세요.
- Windows 10 이상. 패처에 필요한 도구(wit, xdelta3)가 들어 있어 따로 설치할 것이 없습니다.
- 빈 공간 약 10GB(풀어 둔 파일과 결과 이미지).

### 지원 형식

| 원본 | 적용 | 결과 |
|---|---|---|
| ISO (정본 덤프, WBFS에서 변환한 ISO 등) | ○ | ISO |
| WBFS | ○ | WBFS |
| CISO, WIA, WDF | ○ | ISO |
| RVZ | × | Dolphin에서 ISO로 변환한 뒤 적용 |
| NKit | × | NKit 도구로 원본 ISO로 복원한 뒤 적용 |

덤프·변환 방법에 따라 MD5가 달라도 게임 파일만 같으면 적용됩니다.

### 적용 방법

1. [배포 페이지](../../releases/latest)에서 `Disaster_KO_v0.1.zip`을 받아 압축을 풉니다.
2. 원본 이미지(ISO 또는 WBFS)를 `패치하기.bat` 위에 끌어다 놓습니다.
   - 원본을 `패치하기.bat`과 같은 폴더에 넣고 더블클릭해도 됩니다.
   - 폴더에 이미지가 여러 개 있으면 경로를 물어봅니다. 파일을 창에 끌어다 놓고 Enter를 누르세요.
3. 창에 `완료`가 나올 때까지 기다립니다(1분에서 2분 정도). 진행 중에는 창을 닫지 마세요.
4. 원본과 같은 폴더에 결과 파일이 생깁니다. 원본은 바뀌지 않습니다.
   - ISO 원본 → `Disaster (Korean) [RDZJ01].iso`
   - WBFS 원본 → `Disaster (Korean) [RDZJ01].wbfs`

#### 결과 형식을 바꾸고 싶을 때

ISO 원본에서 WBFS를 만들거나 그 반대로 하려면, 패처 폴더에서 PowerShell을 열고 결과 파일 이름을 원하는 확장자로 지정합니다.

```
powershell -ExecutionPolicy Bypass -File patch.ps1 "원본.iso" "결과.wbfs"
```

#### 오류가 날 때

| 메시지 | 원인·해결 |
|---|---|
| 디재스터 데이 오브 크라이시스(RDZJ01)가 아닙니다 | 북미판·유럽판이거나 다른 게임입니다. 일본판만 됩니다. |
| 원본 게임 파일이 다릅니다 | 이미 패치한 이미지거나 손상된 덤프입니다. 원본 일본판에 적용하세요. |
| RVZ는 지원하지 않습니다 | Dolphin 게임 목록에서 우클릭 → 파일 변환 → ISO로 바꾼 뒤 다시 실행하세요. |
| wit.exe 실행 실패 | 빈 공간(약 10GB)이 모자라거나 원본 파일이 손상됐습니다. |

패처는 이미지를 풀어 바뀐 게임 파일 322개에만 파일별 차분을 적용하고 다시 묶습니다. 파일마다 적용 전후 MD5를 검사하므로 원본이 맞지 않으면 멈추고 알려 줍니다.
결과 이미지의 MD5는 원본 덤프에 따라 달라질 수 있지만 게임 내용은 같습니다.

자세한 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

### 실행 환경

- **확인함**: Dolphin.

### 알려진 문제

- 홈 버튼 메뉴의 안내 문장(Wii 메뉴로 돌아갈지 묻는 문장 등)과 Wii 메뉴에 표시되는 게임 이름은 Wii 본체의 시스템 폰트로 그려져 일본어 그대로 두었습니다. 홈 버튼 메뉴의 버튼 그림은 한글화했습니다.
- 게임 화면의 조작 표시(HUD)와 결과 화면 문구는 일본판 원본부터 영문 디자인이라 그대로 두었습니다.
- 컷신 영상 안에 그려진 영어 지명 글씨는 영상의 일부라 바꾸지 않았습니다. 자막은 모두 한글로 나옵니다.
- 스페셜 메뉴의 설정 자료 원화에 적힌 손글씨 메모는 원화 그대로 두었습니다.
- 게임 안 이미지 12,575종을 전수 확인했습니다. 위에 적은 것 말고 일본어가 들어간 이미지는 모두 한글화했습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.11 이상. `pip install -r requirements.txt`로 numpy, Pillow를 설치합니다. 이미지 압축(DXT1)에 Pillow 11.2 이상이 필요합니다.
- 일본판 ISO. 저장소 루트나 `iso/`에 두거나 환경 변수 `DISASTER_JP_ISO`로 지정합니다.
- 맑은 고딕(`C:/Windows/Fonts/malgun.ttf`). 한글 글자를 그리는 데 씁니다.
- [wit](https://wit.wiimm.de/)(Wiimms ISO Tools, cygwin64 판)와 xdelta3. `tools/bin/wit-v3.05a-r8638-cygwin64/`, `tools/bin/xdelta3.exe`에 둡니다. 시험용 ISO만 만들 때는 PATH나 환경 변수 `WIT`, `XDELTA3`로 지정해도 됩니다. 배포용 패처는 이 파일들을 함께 묶으므로 `tools/bin/`에 있어야 합니다.

### 빌드

```bash
# 배포용 패처: 빌드한 뒤 파일별 차분을 만들어 release/Disaster_KO_v0.1/ 과 .zip 으로 묶음
python tools/make_patcher.py 0.1

# 시험용 한글 ISO만 빨리 만들기 (work/Disaster_KO.iso)
python tools/build.py
python tools/inplace.py
```

처음 실행하면 일본판 ISO의 데이터 파티션을 `work/extract`에 추출합니다. `build.py`는 번역을 검사한 뒤 바뀐 파일 322개를 `work/out/files`에 만듭니다. `make_patcher.py`는 이 파일들의 차분과 `patcher/`의 사용자용 스크립트를 묶고, `inplace.py`는 원본 ISO의 배치를 그대로 두고 이 파일들만 교체한 시험용 ISO를 만듭니다.
같은 입력이면 결과는 바이트 단위로 같습니다. Windows Git Bash에서는 `PYTHONIOENCODING=utf-8`을 붙이세요.

### 번역 수정

- 번역: [`translation/ko.json`](translation/ko.json)의 `ko` 값을 고친 뒤 빌드합니다. `id`는 원문 단위 번호이고, 같은 원문이 여러 곳에 쓰이면 한 번만 번역합니다. `분류`, `화자`, `위치`는 참고용입니다.
- 원문 대조: `python tools/export_text.py`를 실행하면 일본어 원문과 번역을 나란히 담은 `work/디재스터_텍스트.json`이 만들어집니다. 이 파일의 `번역`을 고친 뒤 `python tools/ko_import.py work/디재스터_텍스트.json`으로 되돌려 넣을 수 있습니다.
- 검사: 빌드할 때 태그(`<n>`, `<w=숫자>`, `<p>` 등)가 원문과 다르거나 가나가 남아 있으면 빌드를 멈춥니다.
- 그림 글씨: [`tools/assets/`](tools/assets)의 PNG를 원본과 같은 크기로 고친 뒤 빌드합니다. 들어갈 위치는 [`tools/data/textures.json`](tools/data/textures.json)에 있습니다.

`translation/ko.json`에는 **번역문만** 들어 있습니다(원문 단위 번호, 분류, 화자, 위치, 한국어).
일본어 원문은 게임 데이터라 넣지 않았으며, 빌드할 때 게임에서 직접 추출해 번호를 맞춥니다.

### 폴더 구조

```
patcher/           사용자용 패처 (패치하기.bat, patch.ps1)
tools/             빌드·패처·원문 추출 도구 (paths.py가 기준 경로를 잡음)
  assets/          한글화 이미지 209장
  data/            이미지가 들어갈 파일과 위치
  bin/             (git 제외) wit, xdelta3
translation/
  ko.json          번역 JSON
docs/
  TECHNICAL.md     파일 포맷과 한글화 방식
  releases/        릴리즈 노트 사본
release/           사용자 설명서 (패처 폴더·zip은 git 제외, 릴리즈에만 첨부)
work/              (git 제외) 추출본, 빌드 결과, 원문
```

### 기술 문서

파일 포맷과 한글화 방식은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).
- 패처에 동봉하는 [wit](https://wit.wiimm.de/)은 GPL-2.0, [xdelta3](https://github.com/jmacd/xdelta)는 Apache-2.0입니다.
- `tools/inplace.py`, `tools/wiidisc.py`는 같은 제작자의 「죄와 벌 우주의 후계자」 한글 패치 도구를 바탕으로 했습니다.

## 면책

비공식 팬 번역이며 Nintendo와 관련이 없습니다. 「디재스터 데이 오브 크라이시스」 관련 상표·저작권은 Nintendo와 Monolith Soft에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
