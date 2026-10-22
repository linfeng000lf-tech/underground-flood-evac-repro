# -*- coding: utf-8 -*-
"""
Verify every packaged file against MANIFEST.sha256 (offline, no network).

Usage:
    python scripts/verify_hashes.py
Exit 0 when all hashes match; exit 1 on any MISMATCH or missing file.
The manifest lists relative paths from the package root and excludes itself.
"""
import hashlib, os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
MAN=os.path.join(ROOT,'MANIFEST.sha256')

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(65536),b''): h.update(chunk)
    return h.hexdigest()

def main():
    if not os.path.exists(MAN):
        print('MANIFEST.sha256 missing; generate it before verification.'); sys.exit(1)
    bad=0; checked=0
    for line in open(MAN,encoding='utf-8'):
        line=line.strip()
        if not line or line.startswith('#'): continue
        h,rel=line.split(None,1); rel=rel.lstrip('./').replace('\\','/')
        fp=os.path.join(ROOT,*rel.split('/'))
        if not os.path.exists(fp):
            print(f'MISSING {rel}'); bad+=1; continue
        checked+=1
        actual=sha256(fp)
        if actual!=h:
            print(f'MISMATCH {rel}'); bad+=1
    print(f'checked={checked} mismatches={bad}')
    print('RESULT:', 'PASS' if bad==0 else 'FAIL')
    sys.exit(0 if bad==0 else 1)

if __name__=='__main__': main()
