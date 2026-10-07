"""Validate concise Chinese case room labels without silently truncating meaning."""
import argparse,json,re

def validate(case,max_chars=3):
    rows=[];state=case['initialState']['rooms'];seen=set()
    for room in case['model']['rooms']:
        label=room['name'];current=state[room['id']]['name']
        if not isinstance(label,str) or not label.strip() or current!=label:
            raise ValueError('Missing or inconsistent room label: '+room['id'])
        if re.search('[\u3400-\u9fff]',label) and len(label)>max_chars:
            raise ValueError('Chinese room label exceeds limit: '+label)
        if label in seen:raise ValueError('Use distinct concise room labels: '+label)
        seen.add(label);rows.append({'id':room['id'],'name':label,'characters':len(label)})
    return rows
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('case');args=ap.parse_args()
    with open(args.case)as f:case=json.load(f)
    print(json.dumps({'pass':True,'rooms':validate(case)},ensure_ascii=False,indent=2))
