"""기준 경로와 외부 도구 위치 (어느 폴더에서 실행해도 같게 동작)."""
import os, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ASSETS = os.path.join(HERE, 'assets')              # 한글화 이미지 209장 (PNG)
DATA = os.path.join(HERE, 'data')                  # textures.json: 이미지가 들어갈 위치
KO_JSON = os.path.join(ROOT, 'translation', 'ko.json')
RELEASE = os.path.join(ROOT, 'release')
WORK = os.path.join(ROOT, 'work')                  # (git 제외) 추출본·빌드 결과
EXTRACT = os.path.join(WORK, 'extract')            # wit 로 푼 DATA 파티션 (읽기 전용 입력)
SRC = os.path.join(EXTRACT, 'files')
OUT = os.path.join(WORK, 'out')                    # 빌드 결과: 파티션 루트 형식 (바뀐 파일만 files/ 아래에)
OUT_FILES = os.path.join(OUT, 'files')
MASTER = os.path.join(WORK, 'master.json')         # 원문 단위와 게임 안 위치 (extract_text.py)

JP_ISO_NAME = 'Disaster [RDZJ01].iso'


def jp_iso():
    """일본판 ISO: 환경 변수 DISASTER_JP_ISO → 저장소 루트 → iso/ 순서로 찾는다."""
    for p in (os.environ.get('DISASTER_JP_ISO'), os.path.join(ROOT, JP_ISO_NAME), os.path.join(ROOT, 'iso', JP_ISO_NAME)):
        if p and os.path.isfile(p):
            return p
    raise SystemExit(f'일본판 ISO를 찾을 수 없습니다. 저장소 루트에 "{JP_ISO_NAME}"를 두거나 DISASTER_JP_ISO로 지정하세요.')


def tool(env, exe, local):
    """외부 도구: 환경 변수 → tools/bin → PATH."""
    for p in (os.environ.get(env), os.path.join(HERE, 'bin', *local)):
        if p and os.path.isfile(p):
            return p
    p = shutil.which(exe)
    if p:
        return p
    raise SystemExit(f'{exe}를 찾을 수 없습니다. PATH에 두거나 환경 변수 {env}로 지정하세요.')


def wit():
    return tool('WIT', 'wit', ('wit-v3.05a-r8638-cygwin64', 'bin', 'wit.exe'))


def xdelta3():
    return tool('XDELTA3', 'xdelta3', ('xdelta3.exe',))


def rel(p):
    """cygwin wit 는 한글이 든 절대경로를 못 읽으므로 ROOT 기준 상대경로로 넘긴다."""
    return os.path.relpath(p, ROOT)


def run_wit(*args):
    subprocess.run([rel(wit()), *args, '-q'], check=True, cwd=ROOT)


def ensure_extract():
    """work/extract 가 없으면 일본판 ISO 의 DATA 파티션을 푼다."""
    if not os.path.isdir(SRC):
        print('일본판 ISO 추출 중...')
        os.makedirs(WORK, exist_ok=True)
        run_wit('x', rel(jp_iso()), rel(EXTRACT), '--psel', 'data')
    return SRC
