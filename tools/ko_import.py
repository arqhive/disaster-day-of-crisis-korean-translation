"""검수한 JSON(export_text.py 형식)의 번역·화자를 translation/ko.json 에 되돌려 넣는다. 원문은 저장하지 않는다.
사용법: python tools/ko_import.py work/디재스터_텍스트.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        raise SystemExit('사용법: python tools/ko_import.py <검수 JSON>')
    rows = {u['id']: u for u in json.load(open(sys.argv[1], encoding='utf-8'))}
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    changed = 0
    for u in ko:
        r = rows.get(u['id'])
        if r is None:
            continue
        new = dict(u, 화자=r.get('화자', u['화자']), ko=r['번역'])
        changed += new != u
        u.update(new)
    json.dump(ko, open(paths.KO_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{changed}개 바뀜 -> {paths.rel(paths.KO_JSON)}')


if __name__ == '__main__':
    main()
