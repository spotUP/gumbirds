# Hand-drawn maps, profile facing right. Blocks pasted on 16-wide canvases; shading drawn per block (light upper left).
def cv(h): return [['.']*W for _ in range(h)]
def paste(c, block, x, y):
    for j,r in enumerate(block):
        for i,ch in enumerate(r):
            if ch != '.' and 0<=y+j<len(c) and 0<=x+i<W: c[y+j][x+i] = ch
def done(c): return [''.join(r) for r in c]
def make_body(head, torso, legs, tail, skin, cloth=('3','2'), open_hand=False):
    c = cv(18)
    paste(c, tail, 0, 9)
    paste(c, torso, 3, 9)
    paste(c, legs, 4, 15)
    paste(c, head, 8, 3)
    # raised arm (near side) in front: fist at top, forearm down to the shoulder
    s1, s2 = skin
    k1, k2 = cloth
    for y in range(3, 11):
        c[y][4]='o'; c[y][5]=k1 if y%2 else k2; c[y][6]='o'
    fist = ["ooo", "o"+s1+"o", "o"+s2+"o"] if not open_hand else ["o.o", "o"+s1+"o", "o"+s2+"o"]
    for j,r in enumerate(fist):
        for i,ch in enumerate(r):
            if ch != '.': c[j][4+i] = ch
    if open_hand: c[0][5]='.'
    for y in range(0,3): c[y][3]='.'
    return done(c)

def wing(poly, cols, root, far=False, trim=True):
    """Filled polygon, hard 4-band cel: outline o, then cols=(dark,mid,light,edge). Band by distance from root."""
    m = Image.new('L',(W,26),0); ImageDraw.Draw(m).polygon(poly, fill=255)
    px = m.load(); pts = {(x,y) for y in range(26) for x in range(W) if px[x,y]}
    g = cv(26)
    far_d = max(math.dist((x,y),root) for x,y in pts) or 1
    for (x,y) in pts:
        edge = any((x+dx,y+dy) not in pts for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
        t = math.dist((x,y),root)/far_d
        top = (x,y-1) not in pts
        if edge: g[y][x] = 'o'
        elif top and trim: g[y][x] = cols[3]
        else: g[y][x] = cols[2] if t < .38 else cols[1] if t < .72 else cols[0]
    return g
def wings(far_col, near_col, polys, root=(7,16)):
    out = {}
    for pose,(near,farp) in polys.items():
        c = wing(farp, far_col, root, trim=False)
        n = wing(near, near_col, root)
        for y in range(26):
            for x in range(W):
                if n[y][x] != '.': c[y][x] = n[y][x]
        out[pose] = done(c)
    return out

# ================= A Sootling : soot imp, goggles, pointed cap swept back, bat wings =================
A_HEAD = ["..oooo..",
          ".o3344o.",
          "o3344 2o".replace(' ',''),
          "o14ooowo",
          ".o8oowwo",
          ".o89oooo",
          "..o899o.",
          "...oooo."]
A_TORSO = ["..ooooo.",
           ".o33442o",
           "o334221o",
           "o2221o5o",
           ".o11oo6o",
           "..oooo7o"]
A_LEGS = ["o22o.o2o", "o1o..o1o", ".oo.ooo."]
A_TAIL = ["........", "..o.....", ".o5o....", "o65o....", "o76o....", ".o7o....", "..o....."]
A_HEAD[2] = "o334422o"
A_HEAD[3] = "o1oooowo"
D['A'] = dict(name="Sootling", idea="Soot imp seen from the side: goggled head, cap swept back, long ember tail; big scrap-bat wings flare ember orange; lime gas pods.",
  body=make_body(A_HEAD, A_TORSO, A_LEGS, A_TAIL, ('9','8'),('4','3')), body0=make_body(A_HEAD, A_TORSO, A_LEGS, A_TAIL, ('9','8'),('4','3'), True),
  pal=dict(o='#0c0818',**{'1':'#1c203a','2':'#344068','3':'#6078aa','4':'#a4c0ea','5':'#6e203c','6':'#de542c','7':'#ffb054','8':'#b06864','9':'#f6aa80'},
           w='#f0f8ff',s='#b8c0e0',a='#14543c',b='#2eaa46',c='#96e846'),
  cpal=dict(**{'1':'#2c161c','2':'#642c28','3':'#b05c42','4':'#f0b090','5':'#104058','6':'#1e96aa','7':'#6ee6dc'},a='#601028',b='#cc2434',c='#ff6e46'),
  wcols=(('5','6','7','7'),('5','5','6','6')))
_WP = {'glide': ([(7,18),(4,12),(0,3),(2,9),(2,13),(0,17),(3,19),(5,22)], [(9,16),(8,8),(7,1),(10,6),(12,11)]),
       'up':    ([(7,18),(4,10),(0,0),(3,5),(3,9),(0,12),(4,14)],              [(9,16),(10,7),(11,0),(13,5),(13,11)]),
       'down':  ([(7,18),(2,19),(0,25),(3,23),(5,25),(8,21)],                  [(9,17),(8,21),(10,24),(13,20)])}
D['A']['wings'] = wings(*D['A']['wcols'], _WP)
D["A"]["dead"] = ["..o.o...........",
 ".o2o2o..........",
 ".o2o2o..........",
 "..o1o.....oo....",
 "..o22o...o99o...",
 "...o332oo9oo....",
 "..o5o3322oo.....",
 ".o65o2211o......",
 "o76o.o11oooo....",
 ".o7o..oo4332o...",
 "..o...o33442o...",
 ".......o1o8ooo..",
 ".......o1oxxo2o.",
 "........o8oxxo..",
 "........o89oooo.",
 ".........o99o...",
 "..........oo....",
 "................",
 "................",
 "................"]
D['A']['dead'] = [r.replace('x','w') for r in D['A']['dead']]

# ================= B Hoodie Tom : alley cat in a teal hoodie, ears through the hood, cape flaps =================
B_HEAD = [".oo..oo.",
          "o43oo34o",
          "o566773o",
          "o5oo3wwo",
          ".o5o4338",
          ".oo.o488",
          "...o9ooo",
          "....oo.."]
B_HEAD[4] = ".o5o433o"; B_HEAD[5] = ".oo.o48o"
B_TORSO = ["..ooooo.",
           ".o66777o",
           "o566677o",
           "o5666 6o".replace(' ',''),
           ".o5566oo",
           "..o2221o"]
B_LEGS = ["o22o.o2o", "o1o..o1o", "o11o.oo1o"[:8]]
B_TAIL = ["........", "........", "..o.....", ".o3o....", "o43o....", "o32o....", ".o2o...."]
D['B'] = dict(name="Hoodie Tom", idea="Alley cat in profile: teal hoodie, ears poking through the hood, snout and eye to the right, curled tail; the hood cape flaps as the wing; magenta pods.",
  body=make_body(B_HEAD, B_TORSO, B_LEGS, B_TAIL, ('9','8'),('7','6')), body0=make_body(B_HEAD, B_TORSO, B_LEGS, B_TAIL, ('9','8'),('7','6'), True),
  pal=dict(o='#0e0a1e',**{'1':'#2a2448','2':'#4c4482','3':'#8478c0','4':'#cac4f0','5':'#0c3c4c','6':'#188c96','7':'#64e2c4','8':'#b04a6a','9':'#f6a0a8'},
           w='#f6fad2',s='#c4cce8',a='#5c1060',b='#c828a0',c='#ff6ec8'),
  cpal=dict(**{'1':'#3c1e12','2':'#7a4020','3':'#c07838','4':'#f6d090','5':'#541030','6':'#b02040','7':'#f66464'},a='#603800',b='#d48c10',c='#ffd23c'),
  wcols=(('5','6','7','7'),('1','5','5','6')))
_WPB = {'glide': ([(6,17),(1,14),(0,20),(2,19),(0,24),(4,22),(7,23),(8,20)], [(8,16),(5,9),(3,4),(8,8),(11,12)]),
        'up':    ([(6,17),(2,9),(0,2),(3,6),(4,10),(1,13),(5,15)],               [(9,16),(8,6),(6,1),(11,5),(12,10)]),
        'down':  ([(6,17),(0,18),(0,25),(3,22),(5,25),(8,21)],                    [(9,17),(8,21),(10,24),(13,20)])}
D['B']['wings'] = wings(*D['B']['wcols'], _WPB)
D['B']['dead'] = [r for r in D['A']['dead']]
# ================= C Lantern Moth : slim moth bearer, antennae, broad amber wings with eye-spots =================
C_HEAD = ["..o...o.",
          "...o.o..",
          "..ooooo.",
          ".o33442o",
          "o33oowwo",
          "o3o9owwo",
          ".o88o9o.",
          "..oooo.."]
C_TORSO = ["...oooo.",
           "..o3442o",
           ".o33421o",
           ".o3221oo",
           "..o21o6o",
           "...oo.7o"]
C_LEGS = ["o2o..o2o", "o1o..o1o", ".oo..ooo"]
C_TAIL = ["........", "........", ".o......", "o2o.....", "o32o....", ".o3o....", "..oo...."]
D['C'] = dict(name="Lantern Moth", idea="Slim moth bearer in profile: antennae, big eye, fuzzy thorax; the broad amber wings with eye-spots do the flapping; aqua pods.",
  body=make_body(C_HEAD, C_TORSO, C_LEGS, C_TAIL, ('9','8'),('4','3')), body0=make_body(C_HEAD, C_TORSO, C_LEGS, C_TAIL, ('9','8'),('4','3'), True),
  pal=dict(o='#0a081e',**{'1':'#181440','2':'#3c3882','3':'#6a68c0','4':'#b4b8f4','5':'#8c3a2e','6':'#d67828','7':'#ffd664','8':'#7a5090','9':'#e0b8f0'},
           w='#f0faff',s='#b8c8e8',a='#0a465c',b='#14a0b0',c='#6eecdc'),
  cpal=dict(**{'1':'#102820','2':'#2c6046','3':'#4a9a6a','4':'#a8e8a8','5':'#321c64','6':'#7e46c4','7':'#d6a0ff'},a='#60101e',b='#d22828',c='#ff7850'),
  wcols=(('5','6','7','7'),('5','5','6','6')))
_WPC = {'glide': ([(7,18),(3,9),(0,2),(0,10),(1,16),(0,22),(4,22),(7,21)], [(8,16),(5,6),(4,0),(9,4),(13,10)]),
        'up':    ([(7,18),(4,6),(0,0),(0,8),(1,12),(3,14)],                  [(9,16),(9,5),(10,0),(14,5),(14,11)]),
        'down':  ([(7,18),(1,19),(0,25),(4,24),(5,25),(8,21)],               [(9,17),(8,21),(10,24),(13,20)])}
D['C']['wings'] = wings(*D['C']['wcols'], _WPC)
D['C']['dead'] = [r for r in D['A']['dead']]

def _ov(rows, pix):
    g=[list(r) for r in rows]
    for x,y,ch in pix: g[y][x]=ch
    return [''.join(r) for r in g]
D['A']['dead'] = _ov(D['A']['dead'], [(13,14,'o'),(14,15,'o')])           # cap tip hanging
D['B']['dead'] = _ov(D['B']['dead'], [(13,13,'o'),(14,14,'3'),(14,15,'o'),(12,15,'o')])  # ears
D['C']['dead'] = _ov(D['C']['dead'], [(14,11,'o'),(15,12,'o'),(15,13,'o'),(13,17,'o'),(14,18,'o'),(5,10,'6'),(4,11,'7'),(6,11,'6')])  # antennae, wing scrap
