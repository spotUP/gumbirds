# v4: no tails, no pack-like shapes behind the body; (strings meet at one centre point; raised fist at cols 6-9): art 16x24 in a 16x32 slot (feet row 31). Hand-drawn parts. Keys: o outline, 1-4 body ramp (dark..light), 5-7 accent ramp, 8/9 skin, w gloss, s string, a/b/c pod ramp.
def cv(h): return [['.']*W for _ in range(h)]
def paste(c, block, x, y):
    for j,r in enumerate(block):
        for i,ch in enumerate(r):
            if ch != '.' and 0<=y+j<len(c) and 0<=x+i<W: c[y+j][x+i] = ch
def done(c): return [''.join(r) for r in c]
def make_body(P, open_hand=False):
    c = cv(11)  # rows 21..31
    paste(c, P['tail'], *P['tail_at']); paste(c, P['torso'], *P['torso_at']); paste(c, P['legs'], *P['legs_at'])
    paste(c, P['arm'], 4, 3)
    paste(c, P['head'], *P['head_at'])
    # raised fist at cols 6-9 (fill 7-8) directly under the string apex (8,20), held in front of the head's back
    paste(c, ["oooo","o99o","o98o"] if not open_hand else ["o..o","o99o","o98o"], 6, 0)
    return done(c)
def flipv(rows): return rows[::-1]
def mk(P, wings, **kw):
    return dict(body=make_body(P), body0=make_body(P, True), wings=wings, dead=flipv(make_body(P, True)), **kw)

# ============ A Sootling: round soot imp, goggles, cap, wide stance, ember tail, scalloped bat wing ============
A = dict(
 head=["..oooo..",".o3344o.","o334422o","o1owwo9o",".o2o899o","..oooo.."], head_at=(7,0),
 torso=["ooooooo","o22566o","o11566o",".oooooo"], torso_at=(7,5),
 legs=[".o2o.o2o",".ooo.ooo"], legs_at=(7,9),
 tail=[], tail_at=(0,0),
 arm=["o43o","o33o","o32o","o22o"])
A_W = dict(
 glide=[(["o....","o6o..","o76o.",".o65o","..ooo"],2,23)],
 up   =[(["o.....","oo....","o6o...","o66o..","o766o.",".o766o",".o5665",".oo55o","..oooo"],0,18)],
 down =[(["..o5oo",".o65o.","o66o..","o7o...","oo...."],0,27)])
D['A'] = mk(A, A_W, name="Sootling", idea="Soot imp in profile: round goggled head under a cap, wide stance, no tail; a scalloped bat wing flares ember orange; lime gas pods.",
  pal=dict(o='#0c0818',**{'1':'#1c203a','2':'#344068','3':'#6078aa','4':'#a4c0ea','5':'#6e203c','6':'#de542c','7':'#ffb054','8':'#b06864','9':'#f6aa80'},
           w='#f0f8ff',s='#b8c0e0',a='#14543c',b='#2eaa46',c='#96e846'),
  cpal=dict(**{'1':'#2c161c','2':'#642c28','3':'#b05c42','4':'#f0b090','5':'#104058','6':'#1e96aa','7':'#6ee6dc'},a='#601028',b='#cc2434',c='#ff6e46'),
  v2='A')

# ============ B Hoodie Tom: tall-eared cat, teal hoodie with pocket, upright tail, cape wing ============
B = dict(
 head=[".oo..oo.",".o9oo9o.","o333344o","o33ow4o9",".o3344oo","..oooo.."], head_at=(7,0),
 torso=["ooooooo","o56677o","o55oo6o",".o5oo5o"], torso_at=(7,5),
 legs=[".o2o.o1o",".ooo.ooo"], legs_at=(7,9),
 tail=[], tail_at=(0,0),
 arm=["o65o","o55o","o65o","o55o"])
B_W = dict(
 glide=[(["oo...","o6o..","o66o.",".o65o","..ooo"],2,23)],
 up   =[(["oo....","o6o...","o6o...","o76o..","o766o.","o7666o","o5665o",".o555o","..oooo"],0,18)],
 down =[(["..o66o",".o766o","o5665o","o555o.","oooo.."],0,27)])
D['B'] = mk(B, B_W, name="Hoodie Tom", idea="Alley cat in profile: tall ears through a teal hoodie, snout and eye to the right, the hood cape flaps as the wing; magenta pods.",
  pal=dict(o='#0e0a1e',**{'1':'#2a2448','2':'#4c4482','3':'#8478c0','4':'#cac4f0','5':'#0c3c4c','6':'#188c96','7':'#64e2c4','8':'#b04a6a','9':'#f6a0a8'},
           w='#f6fad2',s='#c4cce8',a='#541030',b='#b02040',c='#f66464'),
  cpal=dict(**{'1':'#3c1e12','2':'#7a4020','3':'#c07838','4':'#f6d090','5':'#541030','6':'#b02040','7':'#f66464'},a='#603800',b='#d48c10',c='#ffd23c'),
  v2='B')

# ============ C Lantern Moth: slim, narrow thorax, antennae, big eye, long thin legs, leaf wing with eye-spot ============
C = dict(
 head=["o.....o",".oooooo","o33442o","o3owwoo","o3oo9o.",".ooooo."], head_at=(7,0),
 torso=["o344o","o232o",".o1o."], torso_at=(8,5),
 legs=["o2o.o2o","o1o.o1o","ooo.ooo"], legs_at=(7,8),
 tail=[], tail_at=(0,0),
 arm=["o32o","o22o","o32o","o22o"])
C_W = dict(
 glide=[(["oo...","o6o..","o78o.",".o65o","..ooo"],2,23)],
 up   =[(["..o...",".o6o..","o66o..","o686o.","o766o.","o7667o",".o566o",".o555o","..ooo."],0,18)],
 down =[(["..oo..",".o66o.","o6786o","o7667o",".o55o.","..oo.."],0,26)])
D['C'] = mk(C, C_W, name="Lantern Moth", idea="Slim moth bearer in profile: antennae, big eye, narrow thorax on long thin legs, no abdomen blob; one broad amber leaf wing with an eye-spot flaps; aqua pods.",
  pal=dict(o='#0a081e',**{'1':'#2c2470','2':'#5a54b4','3':'#9490f0','4':'#d8dcff','5':'#8c3a2e','6':'#d67828','7':'#ffd664','8':'#7a5090','9':'#e0b8f0'},
           w='#f0faff',s='#b8c8e8',a='#0a465c',b='#14a0b0',c='#6eecdc'),
  cpal=dict(**{'1':'#102820','2':'#2c6046','3':'#4a9a6a','4':'#a8e8a8','5':'#321c64','6':'#7e46c4','7':'#d6a0ff'},a='#60101e',b='#d22828',c='#ff7850'),
  v2='C')
