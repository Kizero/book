from pathlib import Path
import zipfile,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    items=json.loads((ROOT/'album.json').read_text())['items']
    with zipfile.ZipFile(ROOT/'export/free-stickers-upload-draft.zip','w',zipfile.ZIP_DEFLATED) as z:
        for item in items:
            for folder,ext in [('gif','gif'),('png','png'),('thumbnails','png')]:
                p=ROOT/f'export/{folder}/{item["id"]}.{ext}';z.write(p,p.relative_to(ROOT/'export'))
        for p in (ROOT/'export/album').glob('*.png'):z.write(p,p.relative_to(ROOT/'export'))
        z.write(ROOT/'README.md','README.md')
    manifest={}
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.suffix not in ('.zip','.pyc') and p.name!='manifest.json':manifest[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(ROOT/'export/cream-otter-free-v7-editable-project.zip','w',zipfile.ZIP_DEFLATED) as z:
        for rel in [*manifest,'manifest.json']:z.write(ROOT/rel,rel)
    for p in (ROOT/'export').glob('*.zip'):
        with zipfile.ZipFile(p) as z:assert z.testzip() is None;print(p.name,len(z.namelist()),round(p.stat().st_size/1024/1024,2),'MiB')
if __name__=='__main__':main()
