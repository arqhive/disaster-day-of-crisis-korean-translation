"""번역 검수용 JSON 내보내기: 원문(게임에서 추출)과 번역(translation/ko.json)을 나란히 담는다.
결과: work/디재스터_텍스트.json  [{id, 분류, 화자, 위치, 원문, 번역}]
고친 뒤에는 python tools/ko_import.py work/디재스터_텍스트.json 으로 되돌려 넣는다.
사용법: python tools/export_text.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, extract_text

OUT = os.path.join(paths.WORK, '디재스터_텍스트.json')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if not os.path.exists(paths.MASTER):
        extract_text.main()
    master = {u['id']: u for u in json.load(open(paths.MASTER, encoding='utf-8'))}
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    rows = [dict(id=u['id'], 분류=u['분류'], 화자=u['화자'], 위치=u['위치'], 원문=master[u['id']]['ja'], 번역=u['ko']) for u in ko]
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(rows), '개 ->', paths.rel(OUT))


if __name__ == '__main__':
    main()
