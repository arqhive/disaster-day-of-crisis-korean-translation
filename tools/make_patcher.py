"""배포용 패처 만들기: 빌드 → 바뀐 게임 파일마다 원본과의 xdelta 차분 → 패처 폴더·zip.
ISO 통째 차분과 달리 원본 덤프 형태(정본 ISO, WBFS, WBFS에서 변환한 ISO 등)와 상관없이 적용된다.
사용자용 패처(patcher/패치하기.bat, patch.ps1)와 wit·xdelta3 를 함께 묶는다 (disc-file-patcher 방식).
사용: python tools/make_patcher.py 0.1
결과: release/Disaster_KO_v{버전}/ 과 같은 이름의 .zip"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths

GAME_ID = 'RDZJ01'
TITLE = '디재스터 데이 오브 크라이시스'
RESULT = f'Disaster (Korean) [{GAME_ID}]'
PATCHER = os.path.join(paths.ROOT, 'patcher')
WIT_DIR = os.path.join(HERE, 'bin', 'wit-v3.05a-r8638-cygwin64')
WIT_FILES = ('bin/wit.exe', 'bin/cygwin1.dll', 'bin/cygz.dll', 'bin/cygcrypto-1.1.dll', 'bin/cygncursesw-10.dll')


def md5(b):
    return hashlib.md5(b).hexdigest()


def changed_files():
    """(파티션 안 경로, 원본 경로, 빌드 결과 경로) — 원본과 내용이 다른 것만"""
    for dp, _, fs in os.walk(paths.OUT):
        for f in sorted(fs):
            new = os.path.join(dp, f)
            rel = os.path.relpath(new, paths.OUT).replace(os.sep, '/')
            old = os.path.join(paths.EXTRACT, rel)
            if not os.path.exists(old):
                raise SystemExit(f'원본에 없는 파일(추가 파일은 지원 안 함): {rel}')
            if open(old, 'rb').read() != open(new, 'rb').read():
                yield rel, old, new


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        raise SystemExit('사용법: python tools/make_patcher.py <버전>')
    name = f'Disaster_KO_v{sys.argv[1]}'
    out = os.path.join(paths.RELEASE, name)
    import build
    build.main()

    print('파일별 차분 만드는 중...')
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, 'data'))
    xd = os.path.abspath(paths.xdelta3())   # 상대경로 그대로면 Windows에서 실행 파일을 못 찾음
    lines = []
    for i, (rel, old, new) in enumerate(sorted(changed_files())):
        patch = f'{i:03d}.xdelta'
        subprocess.run([xd, '-e', '-f', '-9', '-S', 'djw', '-s', old, new, os.path.join(out, 'data', patch)], check=True)
        # 모드, 차분 파일, 경로, 원본 MD5, 결과 MD5
        lines.append('\t'.join(('raw', patch, rel, md5(open(old, 'rb').read()), md5(open(new, 'rb').read()))))
    open(os.path.join(out, 'data', 'manifest.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    open(os.path.join(out, 'data', 'config.txt'), 'w', encoding='utf-8', newline='\n').write(
        f'id={GAME_ID}\ntitle={TITLE}\nresult={RESULT}\n')

    for f in os.listdir(PATCHER):
        shutil.copy2(os.path.join(PATCHER, f), os.path.join(out, f))
    shutil.copy2(os.path.join(paths.RELEASE, 'README_한국어.txt'), os.path.join(out, 'README_한국어.txt'))
    os.makedirs(os.path.join(out, 'bin'))
    for f in WIT_FILES:
        shutil.copy2(os.path.join(WIT_DIR, f), os.path.join(out, 'bin', os.path.basename(f)))
    shutil.copy2(os.path.join(WIT_DIR, 'gpl-2.0.txt'), os.path.join(out, 'bin', 'wit-gpl-2.0.txt'))
    shutil.copy2(xd, os.path.join(out, 'bin', 'xdelta3.exe'))

    zpath = out + '.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, _, fs in os.walk(out):
            for f in sorted(fs):
                p = os.path.join(dp, f)
                z.write(p, os.path.join(name, os.path.relpath(p, out)))
    size = sum(os.path.getsize(os.path.join(out, 'data', f)) for f in os.listdir(os.path.join(out, 'data')))
    print(f'파일 {len(lines)}개, 차분 합계 {size / 1e6:.2f} MB, zip {os.path.getsize(zpath) / 1e6:.2f} MB')
    print('패처:', paths.rel(out))


if __name__ == '__main__':
    main()
