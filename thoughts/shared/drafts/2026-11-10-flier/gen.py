import sys, json
from PIL import Image, ImageDraw
OUT = "/Users/spot/Code/ArcadeGame/thoughts/shared/drafts/2026-11-10-flier/"
W, H, BY = 16, 28, 12   # cell, body y offset
POD = [".oooo.", "obccco", "obceco", "oabbco", "oaabbo", ".oaao.", "..oo.."]
SHADE = {'3':'2','2':'1','6':'5','5':'4','9':'8','8':'7'}   # right side darker (light from left)
def mir(half, right_shade=True):
    out = []
    for r in half:
        assert len(r) == 8, r
        rr = ''.join(SHADE.get(c, c) if right_shade else c for c in reversed(r))
        out.append(r + rr)
    return out

D = {}
# ---------------- A: Sootling ----------------
D['A'] = dict(
 name="Sootling", wings_front=False,
 body=["....oooo","...o2233","..o22333","..o11111","..owwwco","..owwcco","..o78999","...o7889",
       "..o44556","..o22333","..o22333","...o2233","...o122o","...o122o","..oo222o","..oooooo"],
 wings=dict(
  glide=["........","........","........","........","........","........","........","..oo....",
         "oo44oooo","o5566o..",".o55o...","..oo...."],
  up=["........","........","o.......","o4o.....","o54o....","o554o...",".o55oo..","..o55o..",
      "...o55oo","........","........","........"],
  down=["........","........","........","........","........","........","........","........",
        "..oo44oo",".o5544..","o55o....","o5o....."]),
 pal=dict(
  p={'o':(12,8,24),'1':(28,32,58),'2':(52,64,104),'3':(96,120,170),'4':(110,32,60),'5':(222,84,44),'6':(255,176,84),
     '7':(92,52,78),'8':(176,104,100),'9':(246,170,128),'w':(240,248,255),
     'a':(20,84,60),'b':(46,170,70),'c':(150,232,70),'e':(240,255,190)},
  c={'1':(44,22,28),'2':(100,44,40),'3':(176,92,66),'4':(16,64,88),'5':(30,150,170),'6':(110,230,220),
     'a':(96,16,40),'b':(204,36,52),'c':(255,110,70),'e':(255,230,190)}),
 idea="Soot imp with goggles and a pointed cap; scrap-bat wings flare ember orange; lime gas pods.")
# ---------------- B: Tomcat ----------------
D['B'] = dict(
 name="Hoodie Tom", wings_front=False,
 body=["..oo....","..o8oo..","..o89999","..o89999","..o8wo99","..o89997","...o8888","..o44555",
       "..o45556","..o45566","..o44555","...o4455","...o1223","...o1223","..oo2223","..oooooo"],
 wings=dict(
  glide=["........","........","........","........","........","........","........","..oo....",
         ".o44o...","o554o...","o65o....",".oo....."],
  up=["........","........","........","..o.....",".o4o....","o54o....","o54o....","o55oo...",
      "o655o...",".o66o...","........","........"],
  down=["........","........","........","........","........","........","........","........",
        ".oooo...","o444o...","o5554o..","o6666oo."]),
 pal=dict(
  p={'o':(14,10,30),'1':(22,26,52),'2':(40,56,110),'3':(80,120,190),'4':(12,60,76),'5':(24,140,150),'6':(100,226,196),
     '7':(84,70,110),'8':(150,128,168),'9':(222,206,230),'w':(246,250,210),
     'a':(92,16,96),'b':(200,40,160),'c':(255,110,200),'e':(255,230,246)},
  c={'4':(84,16,48),'5':(176,32,64),'6':(246,100,100),'7':(110,52,30),'8':(210,120,48),'9':(255,206,120),
     'a':(96,56,0),'b':(212,140,16),'c':(255,210,60),'e':(255,246,190)}),
 idea="Alley cat in a teal hoodie; ears break the head silhouette, hoodie cape flaps; magenta pods.")
# ---------------- C: Lantern Moth ----------------
D['C'] = dict(
 name="Lantern Moth", wings_front=False,
 body=["..o.....","...o....","....o233","...o2333","...owcc3","...o2333","....o233","....o455",
       "....o236","....o233","....o122","....o1o.","....o1o.","...o11o.","..oo1oo.","....o1o.","....o1o.","...o11o."],
 wings=dict(
  glide=["........","........","........","........","oo......","o4oo....","o554oo..","o6c55ooo",
         "o66554oo",".o665o..","..oooo..","........"],
  up=["o.......","o4o.....","o54oo...","o55c4o..","o6554o..",".o6654o.","..o665oo","...oooo.",
      "........","........","........","........"],
  down=["........","........","........","........","........","........","........","...ooo..",
        "..o544o.",".o6554oo","o66c54o.","oo6oo..."]),
 pal=dict(
  p={'o':(10,8,30),'1':(24,20,64),'2':(60,56,130),'3':(132,140,220),'4':(96,36,70),'5':(214,120,40),'6':(255,214,100),
     '7':(60,56,130),'8':(132,140,220),'9':(132,140,220),'w':(240,250,255),
     'a':(10,70,92),'b':(20,160,176),'c':(110,236,220),'e':(230,255,250)},
  c={'1':(20,44,40),'2':(44,96,70),'3':(110,170,110),'4':(50,28,100),'5':(126,70,196),'6':(214,160,255),
     'a':(96,16,30),'b':(210,40,40),'c':(255,120,80),'e':(255,236,200)}),
 idea="Slim moth bearer; the big wings are the flap, with eye-spot patterning; amber wings, aqua pods.")

def line(pts):
    (x0,y0),(x1,y1)=pts; out=[]
    n=max(abs(x1-x0),abs(y1-y0)) or 1
    for i in range(n+1): out.append((round(x0+(x1-x0)*i/n), round(y0+(y1-y0)*i/n)))
    return out
SLOTS = {3:[(0,4),(5,0),(10,4)], 2:[(2,3),(8,3)], 1:[(5,2)], 0:[]}
def blit(g, rows, ox, oy, flip=False):
    if flip: rows = rows[::-1]
    for y,r in enumerate(rows):
        for x,c in enumerate(r):
            if c!='.' and 0<=oy+y<H: g[oy+y][ox+x]=c
def sprite(d, pose, pods, dead=False):
    g=[['.']*W for _ in range(H)]
    wing=mir(d['wings']['up' if dead else pose]+['........']*4, False)
    body=mir(d['body'])
    if dead:
        blit(g,wing,0,BY-2,True); blit(g,body,0,BY,True)
        return g
    blit(g,wing,0,BY)
    for (px,py) in SLOTS[pods]:   # tethers to head top
        kx,ky=px+2,py+7
        tx = 6 if kx<7 else (9 if kx>8 else kx)
        for (x,y) in line(((kx+1 if kx<7 else kx, ky),(tx,BY))):
            if g[y][x]=='.': g[y][x]='o'
        if kx==7 or px==5:
            for y in range(py+7,BY): g[y][7]='o'; g[y][8]='o'
    blit(g,body,0,BY)
    for (px,py) in SLOTS[pods]: blit(g,POD,px,py)
    return g
def render(g, pal, scale=1):
    im=Image.new('RGBA',(W,H),(0,0,0,0)); p=im.load()
    for y in range(H):
        for x in range(W):
            if g[y][x]!='.': p[x,y]=pal[g[y][x]]+(255,)
    return im if scale==1 else im.resize((W*scale,H*scale),Image.NEAREST)
def palettes(d):
    pp=d['pal']['p']; cp=dict(pp); cp.update(d['pal']['c']); return pp,cp
def frames(d):
    return [('idle3',('glide',3,False)),('flapup3',('up',3,False)),('flapdown3',('down',3,False)),
            ('pods2',('glide',2,False)),('pods1',('glide',1,False)),('pods0',('glide',0,False)),('fall',('glide',0,True))]
def sheet(d, scale, box):
    pp,cp=palettes(d); fr=frames(d); pitch=W+4
    im=Image.new('RGBA',((len(fr)*pitch+2)*scale,(2*(H+4)+2)*scale),(26,29,36,255))
    dr=ImageDraw.Draw(im)
    for row,pal in enumerate((pp,cp)):
        for i,(n,(pose,pods,dead)) in enumerate(fr):
            s=render(sprite(d,pose,pods,dead),pal,scale)
            ox,oy=(2+i*pitch)*scale,(2+row*(H+4))*scale
            dr.rectangle([ox-scale,oy-scale,ox+W*scale,oy+H*scale],fill=(36,40,50,255))
            im.alpha_composite(s,(ox,oy))
            if box and row==0 and n in('idle3','pods0'):
                h=11 if n=='idle3' else 7
                dr.rectangle([ox+6*scale,oy+(H-h)*scale,ox+10*scale-1,oy+H*scale-1],outline=(255,60,80,255))
    return im
def used(d,pal):
    s=set()
    for _,(pose,pods,dead) in frames(d):
        for r in sprite(d,pose,pods,dead): s|=set(r)
    s.discard('.'); return len(s)
def scene(d, key):
    pp,cp=palettes(d)
    im=Image.new('RGBA',(320,224),(0,0,0,255)); dr=ImageDraw.Draw(im)
    for y0,y1,c in((0,60,(8,10,28)),(60,120,(12,16,44)),(120,180,(20,26,66))): dr.rectangle([0,y0,319,y1-1],fill=c)
    for (x,y) in [(14,10),(60,30),(97,8),(150,44),(201,18),(250,6),(290,36),(310,70),(40,80),(180,90),(120,110),(270,100)]:
        dr.point((x,y),(214,222,247))
    for bx,bw,bh in((0,40,30),(46,28,48),(80,36,22),(130,30,40),(190,44,34),(250,30,52),(284,36,26)):
        dr.rectangle([bx,180-bh,bx+bw-1,179],fill=(10,12,34))
        for wy in range(180-bh+5,176,8):
            for wx in range(bx+4,bx+bw-4,9):
                if (wx*7+wy*3)%5<2: dr.rectangle([wx,wy,wx+1,wy+2],fill=(239,165,115))
    for bx,by,w in((20,134,70),(220,120,64),(120,88,60),(250,160,70),(0,164,50)):
        dr.rectangle([bx,by,bx+w-1,by+7],fill=(52,60,110)); dr.rectangle([bx,by,bx+w-1,by],fill=(140,156,198))
        dr.rectangle([bx,by+1,bx+w-1,by+1],fill=(90,100,160)); dr.rectangle([bx,by+7,bx+w-1,by+7],fill=(28,32,70))
    dr.rectangle([0,180,319,223],fill=(16,36,90))
    for y,c in((184,(41,80,150)),(192,(30,60,120)),(202,(24,48,104)),(214,(20,42,92))):
        for x in range(0,320,16): dr.rectangle([x+(y%12),y,x+(y%12)+7,y],fill=c)
    def put(g,pal,cx,by):
        s=render(g,pal); im.alpha_composite(s,(cx-8,by-H))
    put(sprite(d,'glide',3),pp,60,134)
    put(sprite(d,'up',2),cp,170,86)
    put(sprite(d,'down',1),cp,240,60)
    return im.convert('RGB').resize((960,672),Image.NEAREST)
res={}
for k,d in D.items():
    sheet(d,1,False).save(OUT+f"{k}_sheet_1x.png"); sheet(d,4,True).save(OUT+f"{k}_sheet_4x.png")
    scene(d,k).save(OUT+f"{k}_scene_3x.png")
    pp,cp=palettes(d)
    res[k]=dict(name=d['name'],idea=d['idea'],pu=used(d,pp)+1,cu=used(d,cp)+1,
       pal=[('#%02x%02x%02x'%v) for v in pp.values()],cpal=[('#%02x%02x%02x'%v) for v in cp.values()])
json.dump(res,open(sys.argv[1],'w'))
print({k:(v['pu'],v['cu']) for k,v in res.items()})
