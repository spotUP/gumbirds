# Flier drafts v2: side view, 2 big overlapping pods. 16x48 sprite (3 tiles tall in one column).
# run: PYTHONPATH=<pil dir> python3 gen_v3.py
import json, math
from PIL import Image, ImageDraw
OUT = "/Users/spot/Code/ArcadeGame/thoughts/shared/drafts/2026-11-10-flier/"
W, H, BY = 16, 32, 21   # sprite w/h, body top row, wing-overlay top row
def hexc(s): return tuple(int(s[i:i+2],16) for i in (1,3,5))

# ---- pods: two side-by-side ellipses (overlap 2 px), hard cel steps, hand gloss ----
def pod(g, cx, cy, rx, ry, gloss):
    m = set()
    for y in range(H):
        for x in range(W):
            if ((x+.5-cx)/rx)**2 + ((y+.5-cy)/ry)**2 <= 1: m.add((x,y))
    for (x,y) in m:
        edge = any((x+dx,y+dy) not in m for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
        t = ((x+.5-cx)/rx + (y+.5-cy)/ry)*0.7
        g[y][x] = 'o' if edge else ('c' if t < -.45 else 'b' if t < .2 else 'a')
    for (dx,dy) in gloss:
        x,y = int(cx)+dx, int(cy)+dy
        if (x,y) in m and g[y][x] != 'o': g[y][x] = 'w'
    kx, ky = int(round(cx)), max(y for _,y in m)+1
    g[ky][kx] = 'o'
    return (kx, ky)
GLOSS = [(-2,-2),(-2,-1),(-1,-3)]
def pods(g, n):
    if n == 2: return [pod(g, 4.9, 12.5, 4.0, 4.5, GLOSS), pod(g, 10.9, 12.5, 4.0, 4.5, GLOSS)]
    if n == 1: return [pod(g, 7.9, 12.5, 4.0, 4.5, GLOSS)]
    return []
def line(a, b):
    (x0,y0),(x1,y1)=a,b; n=max(abs(x1-x0),abs(y1-y0)) or 1
    return [(round(x0+(x1-x0)*i/n), round(y0+(y1-y0)*i/n)) for i in range(n+1)]
HAND = (4, 20)
def strings(g, ks):
    for k in ks:
        for (x,y) in line(k, HAND):
            if g[y][x] == '.': g[y][x] = 's'

def blit(g, rows, ox, oy):
    for y,r in enumerate(rows):
        for x,c in enumerate(r):
            if c != '.' and 0 <= oy+y < H and 0 <= ox+x < W: g[oy+y][ox+x] = c
def pad(rows, n): return rows + ['.'*W]*(n-len(rows))
D = {}
import math
exec(open(OUT+"designs_v3.py").read())

def sprite(d, pose, n, dead=False):
    g = [['.']*W for _ in range(H)]
    if dead:
        blit(g, d['dead'], 0, BY); return g
    for (blk,wx,wy) in d['wings'].get(pose,[]): blit(g, blk, wx, wy)
    ks = pods(g, n)
    strings(g, ks)
    # arm is part of body; hands up even with 0 pods (grabbing at air)
    blit(g, d['body'] if n else d['body0'], 0, BY)
    return g
def render(g, pal, scale=1):
    im = Image.new('RGBA',(W,H),(0,0,0,0)); p = im.load()
    for y in range(H):
        for x in range(W):
            if g[y][x] != '.': p[x,y] = pal[g[y][x]]+(255,)
    return im if scale == 1 else im.resize((W*scale,H*scale), Image.NEAREST)
FR = [('glide2',('glide',2,False)),('up2',('up',2,False)),('down2',('down',2,False)),
      ('glide1',('glide',1,False)),('up1',('up',1,False)),('glide0',('glide',0,False)),('fall',('glide',0,True))]
def pals(d):
    pp = {k:hexc(v) for k,v in d['pal'].items()}; cp = dict(pp)
    cp.update({k:hexc(v) for k,v in d['cpal'].items()}); return pp, cp
def sheet(d, scale, box):
    pp, cp = pals(d); pitch = W+4
    im = Image.new('RGBA',((len(FR)*pitch+2)*scale,(2*(H+4)+2)*scale),(26,29,36,255)); dr = ImageDraw.Draw(im)
    for row,pal in enumerate((pp,cp)):
        for i,(n,(pose,pc,dead)) in enumerate(FR):
            s = render(sprite(d,pose,pc,dead),pal,scale)
            ox,oy = (2+i*pitch)*scale,(2+row*(H+4))*scale
            dr.rectangle([ox-scale,oy-scale,ox+W*scale,oy+H*scale],fill=(36,40,50,255))
            im.alpha_composite(s,(ox,oy))
            if box and row == 0 and n in ('glide2','glide0'):
                h = 11 if n == 'glide2' else 7
                dr.rectangle([ox+6*scale,oy+(H-h)*scale,ox+10*scale-1,oy+H*scale-1],outline=(255,60,80,255))
    return im
def used(d):
    s=set()
    for _,(pose,pc,dead) in FR:
        for r in sprite(d,pose,pc,dead): s |= set(r)
    s.discard('.'); return s
def scene(d):
    pp, cp = pals(d)
    im = Image.new('RGBA',(320,224),(0,0,0,255)); dr = ImageDraw.Draw(im)
    for y0,y1,c in((0,60,(8,10,28)),(60,120,(12,16,44)),(120,180,(20,26,66))): dr.rectangle([0,y0,319,y1-1],fill=c)
    for (x,y) in [(14,10),(60,30),(97,8),(150,44),(201,18),(250,6),(290,36),(310,70),(40,80),(180,90),(120,110),(270,100)]: dr.point((x,y),(214,222,247))
    for bx,bw,bh in((0,40,30),(46,28,48),(80,36,22),(130,30,40),(190,44,34),(250,30,52),(284,36,26)):
        dr.rectangle([bx,180-bh,bx+bw-1,179],fill=(10,12,34))
        for wy in range(180-bh+5,176,8):
            for wx in range(bx+4,bx+bw-4,9):
                if (wx*7+wy*3)%5<2: dr.rectangle([wx,wy,wx+1,wy+2],fill=(239,165,115))
    plats = ((20,134,70),(220,120,64),(120,88,60),(250,160,70),(0,164,50))
    for bx,by,w in plats:
        dr.rectangle([bx,by,bx+w-1,by+7],fill=(52,60,110)); dr.rectangle([bx,by,bx+w-1,by],fill=(140,156,198))
        dr.rectangle([bx,by+1,bx+w-1,by+1],fill=(90,100,160)); dr.rectangle([bx,by+7,bx+w-1,by+7],fill=(28,32,70))
    dr.rectangle([0,180,319,223],fill=(16,36,90))
    for y,c in((184,(41,80,150)),(192,(30,60,120)),(202,(24,48,104)),(214,(20,42,92))):
        for x in range(0,320,16): dr.rectangle([x+(y%12),y,x+(y%12)+7,y],fill=c)
    def put(g,pal,cx,by,flip=False):
        s = render(g,pal)
        if flip: s = s.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(s,(cx-8,by-H))
    put(sprite(d,'glide',2),pp,60,134)               # standing on platform, faces right
    put(sprite(d,'up',2),cp,160,100,True)            # computer, facing left
    put(sprite(d,'down',1),pp,240,80)
    put(sprite(d,'glide',2),cp,270,160)
    v2 = Image.open(OUT+f"{d['v2']}_v2_sheet_1x.png").crop((2,2,18,50)).convert('RGBA')
    im.alpha_composite(v2,(296,10))
    out = im.convert('RGB').resize((960,672),Image.NEAREST)
    from PIL import ImageFont; ImageDraw.Draw(out).text((850,80),"v2",fill=(255,230,120),font=ImageFont.load_default(size=22))
    return out
res = {}
OUTK = None
for k,d in D.items():
    sheet(d,1,False).save(OUT+f"{k}_v3_sheet_1x.png"); sheet(d,4,True).save(OUT+f"{k}_v3_sheet_4x.png")
    scene(d).save(OUT+f"{k}_v3_scene_3x.png")
    u = used(d); pu = len(u)
    pp, cp = pals(d)
    print(k, 'colours used', pu, 'palette keys', len(d['pal']), 'unused', set(d['pal'])-u)
    res[k] = dict(name=d['name'],idea=d['idea'],n=len(d['pal']),pal=list(d['pal'].values()),cpal=[d['cpal'].get(c,d['pal'][c]) for c in d['pal']])
json.dump(res, open(OUT+'res_v3.json','w'))

# ---- index page ----
CSS = open(OUT+"index_v2.html").read().split("<style>")[1].split("</style>")[0]
sw = lambda cols: '<div class="sws">'+''.join(f'<span class="sw" style="background:{c}"></span>' for c in cols)+'</div>'
h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Flier character drafts v3</title><style>'+CSS+'</style></head><body><h1>Flier character drafts, round 3</h1><p>Compact proportions: art 16 x 24 px in a 16 x 32 slot (one column, two tiles), pods side by side above the head, chibi body, short strings. Side view facing right. Hand-placed pixels, 3x night arena mock; the small figure in the corner of each scene is the v2 flier at the same scale. Pick one.</p>']
for k,v in res.items():
    h.append(f'<section><h2>{k}: {v["name"]}</h2><p>{v["idea"]}</p>')
    h.append('<p>Size: art 16 x 24 px, rows 8 to 31 of a 16 x 32 slot (rows 0 to 7 empty), feet on row 31. Hitbox 4 x 11 with pods, 4 x 7 without: art columns 6 to 9, bottom edge on row 31; red outline on the 4x sheet marks it (glide with 2 pods, glide with 0 pods).</p>')
    h.append('<p>Palette: 15 colours plus transparent. Computer opponent swaps body ramps and pod hue, same sprite.</p>'+sw(v['pal'])+sw(v['cpal']))
    h.append('<p class="n">Sheet columns: glide (2 pods), flap up, flap down, glide (1 pod), flap up (1 pod), glide (0 pods), falling. Top row player, bottom row computer.</p>')
    h.append(f'<img src="{k}_v3_sheet_4x.png" style="width:100%;max-width:1136px"><p><img src="{k}_v3_sheet_1x.png" style="width:284px"> 1x sheet</p><img src="{k}_v3_scene_3x.png" style="width:960px;max-width:100%"></section>')
h.append('</body></html>')
open(OUT+'index_v3.html','w').write(''.join(h))
