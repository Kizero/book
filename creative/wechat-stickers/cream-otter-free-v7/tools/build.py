"""Re-edit approved layered poses into complete acting loops; 40 ms exposure units."""
from pathlib import Path
import json, io, base64, math, hashlib
from PIL import Image, ImageChops, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
TICK=40
DEFAULT=[2,2,2,2,2,2,2,2,2,2,2,3,3,4,6,2]
def read_layers(path):
    doc=json.loads(path.read_text()); layers=[]; defs=[]
    for raw in doc['piskel']['layers']:
        d=json.loads(raw); defs.append(d)
        strip=Image.open(io.BytesIO(base64.b64decode(d['chunks'][0]['base64PNG'].split(',')[1]))).convert('RGBA')
        layers.append([strip.crop((i*240,0,(i+1)*240,240)) for i in range(d['frameCount'])])
    return doc,defs,layers

def pose_spans(kind):
    counts=[3]*16 if kind=='night' else [2]*14+[4,4] if kind in ('received','thanks','laugh','cheer','bye') else DEFAULT[:]
    ids=list(range(1,17))
    if kind=='angry':counts.pop(12);ids.remove(13)
    cur=0; spans={}
    for pose,n in zip(ids,counts):spans[pose]=list(range(cur,cur+n));cur+=n
    return spans

def compose(layers,fx=True):
    out=Image.new('RGBA',(240,240))
    for i,im in enumerate(layers):
        if fx or i not in (1,3):out.alpha_composite(im)
    return out

def gif_save(frames,path):
    # A common palette avoids color changes at holds and across the loop boundary.
    sample=Image.new('RGB',(240*8,240*math.ceil(len(frames)/8)),(255,255,255))
    for i,f in enumerate(frames):sample.paste(f.convert('RGB'),((i%8)*240,(i//8)*240))
    pal=sample.quantize(colors=255,method=Image.Quantize.MEDIANCUT)
    palette=pal.getpalette()[:765]; converted=[]
    for f in frames:
        q=f.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE)
        q=q.point(lambda x:x+1);q.putpalette([0,0,0]+palette)
        q.paste(0,mask=f.getchannel('A').point(lambda a:255 if a<128 else 0));q.info['transparency']=0
        converted.append(q)
    converted[0].save(path,save_all=True,append_images=converted[1:],duration=TICK,loop=0,transparency=0,disposal=2,optimize=False)
    decoded=Image.open(path); seq=[];delays=[]; margin=240
    for i in range(decoded.n_frames):
        decoded.seek(i);f=decoded.convert('RGBA');seq.append(f.copy());delays.append(decoded.info['duration'])
        box=f.getbbox()
        if box:margin=min(margin,*box[:2],240-box[2],240-box[3])
    assert sum(delays)==len(frames)*TICK
    assert seq[0].tobytes()==seq[-1].tobytes(),(path,'loop seam differs')
    assert path.stat().st_size<=500*1024,(path,'over working file budget')
    assert margin>=4,(path,margin)
    return dict(encoded_frames=len(seq),duration_ms=sum(delays),bytes=path.stat().st_size,loop_seam_identical=True,minimum_margin_px=margin,loop=decoded.info.get('loop'))

def save_piskel(doc,defs,layers,path):
    out=[]
    for d,frames in zip(defs,layers):
        d=dict(d);strip=Image.new('RGBA',(240*len(frames),240))
        for i,im in enumerate(frames):strip.paste(im,(i*240,0))
        b=io.BytesIO();strip.save(b,format='PNG')
        d.update(frameCount=len(frames),chunks=[dict(layout=[[i] for i in range(len(frames))],base64PNG='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode())]);out.append(json.dumps(d))
    doc['piskel'].update(name=doc['piskel']['name'].replace('第五版','第七版'),fps=25,layers=out,hiddenFrames=[],description='Approved original character poses re-edited into acting loops. Shared opening/closing rest; brief FX tails; 25 FPS exposure frames.')
    path.write_text(json.dumps(doc))
    _,_,roundtrip=read_layers(path)
    assert all(a.tobytes()==b.tobytes() for la,lb in zip(layers,roundtrip) for a,b in zip(la,lb))

def review_sheets():
    plan=json.loads((ROOT/'edit-plan.json').read_text())
    for slug in ['06-coming','09-cheer','12-speechless','15-goodnight']:
        beats=plan[slug]['beats'];sheet=Image.open(ROOT/f'preview/{slug}-frames.png')
        out=Image.new('RGB',(1440,270*math.ceil(len(beats)/6)),(250,247,240));draw=ImageDraw.Draw(out);cursor=0
        for i,b in enumerate(beats):
            x=i%6*240;y=i//6*270
            f=sheet.crop((cursor%8*240,cursor//8*240,cursor%8*240+240,cursor//8*240+240))
            out.paste(f,(x,y),f);draw.text((x+10,y+244),f"pose{b['pose']:02}  {b['ms']}ms",fill=(30,30,30));cursor+=b['ms']//40
        out.save(ROOT/f'docs/{slug}-beats.png')

def run():
    plan=json.loads((ROOT/'edit-plan.json').read_text());meta=json.loads((ROOT/'source/input-album.json').read_text());previous={i['id']:i for i in json.loads((ROOT/'reference-v6/album.json').read_text())['items']};report=[]
    for item in meta['items']:
        slug=item['id']; beats=plan[slug]['beats'];assert beats[0]['pose']==beats[-1]['pose']
        doc,defs,original=read_layers(ROOT/f'source/input-piskel/{slug}.piskel');spans=pose_spans(item['animation']); layers=[[] for _ in original];pose_map=[];source_map=[]
        for bi,beat in enumerate(beats):
            span=spans[beat['pose']];n=beat['ms']//TICK;assert n*TICK==beat['ms']
            rest=bi in (0,len(beats)-1)
            for j in range(n):
                # Rest exposures use the exact same settled microframe at both ends.
                src=span[0] if rest else span[min(len(span)-1, j*len(span)//min(n,max(2,len(span))))]
                source_map.append(src);pose_map.append(beat['pose'])
                for li in range(5):
                    im=original[li][src].copy()
                    if li in (1,3):
                        # Release effects while acting holds; do not freeze airborne particles.
                        factor=0 if rest or beat.get("fx") is False else max(0,min(1,(240-j*TICK)/160)) if n*TICK>=240 else 1
                        if factor==0:im=Image.new('RGBA',(240,240))
                        elif factor<1:im.putalpha(im.getchannel('A').point(lambda a:round(a*factor)))
                    layers[li].append(im)
        assert all(l[0].tobytes()==l[-1].tobytes() for l in layers)
        approved={hashlib.sha256(f.tobytes()).digest() for f in original[2]}
        assert all(hashlib.sha256(f.tobytes()).digest() in approved for f in layers[2])
        frames=[compose([l[i] for l in layers]) for i in range(len(pose_map))]
        bare=[compose([l[i] for l in layers],False) for i in range(len(pose_map))]
        qa={}
        for suffix,imgs in [('',frames),('-no-fx',bare)]:
            qa[suffix or 'main']=gif_save(imgs,ROOT/f'export/gif/{slug}{suffix}.gif')
            imgs[0].save(ROOT/f'export/png/{slug}{suffix}.png')
        frames[0].resize((120,120),Image.Resampling.LANCZOS).save(ROOT/f'export/thumbnails/{slug}.png')
        save_piskel(doc,defs,layers,ROOT/f'source/piskel/{slug}.piskel')
        sheet=Image.new('RGBA',(1920,240*math.ceil(len(frames)/8)))
        for i,f in enumerate(frames):sheet.paste(f,((i%8)*240,(i//8)*240))
        sheet.save(ROOT/f'preview/{slug}-frames.png')
        item.update(previous_duration_ms=previous[slug]['duration_ms'],duration_ms=len(frames)*TICK,frames=len(frames),original_frames=len(frames),frame_map=list(range(len(frames))),source_frame_map=source_map,pose_map=pose_map,poster=0,timing_note=plan[slug]['note'],artwork_preserved=True,approved_sample_preserved=False,seam_rest_ms=beats[0]['ms']+beats[-1]['ms'])
        if item['animation']=='night':item['story']='闭眼睡着，轻轻拢拢被子，再安心睡回去。'
        if item['animation']=='blank':item['story']='半垂着眼听完，转身叹气，摊手后还是一脸无语。'
        report.append(dict(id=slug,gif=qa,character_layers_from_approved_source=True,piskel_roundtrip_exact=True,all_layers_seam_identical=True,seam_rest_ms=item['seam_rest_ms'],beats=beats))
        print(slug,item['duration_ms'],'ms',qa['main']['bytes'],'bytes',flush=True)
    meta.update(version=7,edition='演完，歇一口气')
    (ROOT/'album.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));(ROOT/'preview/album-data.js').write_text('window.albumData='+json.dumps(meta,ensure_ascii=False)+';')
    (ROOT/'docs/timing-qa.json').write_text(json.dumps(dict(status='PASS',scope='Encoding, original character preservation, identical boundary and layered roundtrip. Not an aesthetic score.',items=report),ensure_ascii=False,indent=2))
    lines=['# 第七版动作节奏','','沿用已有角色画面，重新剪辑动作顺序与曝光时间。开头和结尾共用安定姿势；跨循环的停留是有意保留的呼吸。角色未补画中间帧，因此大幅转身仍受现有关键姿势数量限制。','','|表情|上版|本版|首尾连续休息|处理|','|---|---:|---:|---:|---|']
    for i in meta['items']:lines.append(f'|{i["meaning"]}|{i["previous_duration_ms"]} ms|{i["duration_ms"]} ms|{i["seam_rest_ms"]} ms|{i["timing_note"]}|')
    (ROOT/'docs/timing-notes.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':
    run()
    review_sheets()
