# utils.py
import os, math, random
import pygame

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
IMG_DIR = os.path.join(ASSET_DIR, "images")
SND_DIR = os.path.join(ASSET_DIR, "sounds")
ROBOTS_DIR = os.path.join(IMG_DIR, "robots")

# ---------- Globals ----------
IMAGES = {}
SFX = {}
CELL_IMG_SIZE = 64  # overwritten by init_assets(cell_size)

# ---------- Helpers ----------
def _ensure_pygame_inited():
    if not pygame.get_init():
        pygame.init()

def _ensure_mixer_inited():
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ---------- Asset auto-generation (only images now) ----------
def _save_surface_png(surface, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pygame.image.save(surface, path)

def _mk_robot(color_body=(70,130,230), visor=(40,220,255)):
    s = pygame.Surface((CELL_IMG_SIZE, CELL_IMG_SIZE), pygame.SRCALPHA)
    cx, cy = CELL_IMG_SIZE//2, CELL_IMG_SIZE//2
    pygame.draw.rect(s, color_body, (cx-16, cy-14, 32, 28), border_radius=10)
    pygame.draw.rect(s, (60,60,60), (cx-14, cy+12, 10, 12), border_radius=4)
    pygame.draw.rect(s, (60,60,60), (cx+4, cy+12, 10, 12), border_radius=4)
    pygame.draw.rect(s, (50,90,200), (cx-26, cy-8, 10, 18), border_radius=4)
    pygame.draw.rect(s, (50,90,200), (cx+16, cy-8, 10, 18), border_radius=4)
    pygame.draw.rect(s, (35,35,40), (cx-14, cy-28, 28, 18), border_radius=6)
    pygame.draw.rect(s, visor, (cx-10, cy-23, 20, 8), border_radius=4)
    return s

def _mk_coin():
    s = pygame.Surface((CELL_IMG_SIZE, CELL_IMG_SIZE), pygame.SRCALPHA)
    cx, cy = CELL_IMG_SIZE//2, CELL_IMG_SIZE//2
    pygame.draw.circle(s, (255,212,70), (cx,cy), CELL_IMG_SIZE//3)
    pygame.draw.circle(s, (255,238,160), (cx,cy), CELL_IMG_SIZE//5)
    return s

def _mk_heart():
    s = pygame.Surface((CELL_IMG_SIZE, CELL_IMG_SIZE), pygame.SRCALPHA)
    cx, cy = CELL_IMG_SIZE//2, CELL_IMG_SIZE//2
    r = CELL_IMG_SIZE//6
    pygame.draw.circle(s, (230,60,90), (cx-r,cy-r), r)
    pygame.draw.circle(s, (230,60,90), (cx+r,cy-r), r)
    pygame.draw.polygon(s, (230,60,90), [(cx-2*r,cy-r),(cx+2*r,cy-r),(cx,cy+r*2)])
    return s

def _mk_bonus():
    s = pygame.Surface((CELL_IMG_SIZE, CELL_IMG_SIZE), pygame.SRCALPHA)
    cx, cy = CELL_IMG_SIZE//2, CELL_IMG_SIZE//2
    pygame.draw.polygon(s, (100,230,255), [(cx,cy-18),(cx+18,cy),(cx,cy+18),(cx-18,cy)])
    pygame.draw.circle(s, (170,255,255), (cx,cy), 6)
    return s

def _mk_trap():
    s = pygame.Surface((CELL_IMG_SIZE, CELL_IMG_SIZE), pygame.SRCALPHA)
    cx, cy = CELL_IMG_SIZE//2, CELL_IMG_SIZE//2
    pygame.draw.circle(s, (30,30,40), (cx,cy), CELL_IMG_SIZE//3)
    for a in range(0,360,45):
        rad = math.radians(a)
        x1 = cx + int(math.cos(rad)*(CELL_IMG_SIZE//4))
        y1 = cy + int(math.sin(rad)*(CELL_IMG_SIZE//4))
        x2 = cx + int(math.cos(rad)*(CELL_IMG_SIZE//2-4))
        y2 = cy + int(math.sin(rad)*(CELL_IMG_SIZE//2-4))
        pygame.draw.line(s, (200,40,40), (x1,y1), (x2,y2), 3)
    return s

def _mk_obstacle():
    s = pygame.Surface((CELL_IMG_SIZE, CELL_IMG_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(s, (60,65,80), (6,6,CELL_IMG_SIZE-12,CELL_IMG_SIZE-12), border_radius=10)
    return s

def _mk_background(w=1280, h=720):
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1,h-1)
        col = (int(100+80*t), int(200-100*t), int(255-50*t))
        pygame.draw.line(s, col, (0,y), (w,y))
    return s

def ensure_assets(screen_size):
    """Create placeholder images if missing. Returns background path."""
    _ensure_pygame_inited()
    os.makedirs(ASSET_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(SND_DIR, exist_ok=True)
    os.makedirs(ROBOTS_DIR, exist_ok=True)

    # Robots
    blue_path = os.path.join(ROBOTS_DIR, "blue.png")
    red_path  = os.path.join(ROBOTS_DIR, "red.png")
    if not os.path.exists(blue_path): _save_surface_png(_mk_robot((70,130,230),(80,200,255)), blue_path)
    if not os.path.exists(red_path):  _save_surface_png(_mk_robot((190,60,60),(255,110,110)), red_path)

    # Items
    items = {
        "coin.png": _mk_coin(),
        "heart.png": _mk_heart(),
        "bonus.png": _mk_bonus(),
        "trap.png": _mk_trap(),
        "obstacle.png": _mk_obstacle(),
    }
    for fname, surf in items.items():
        path = os.path.join(IMG_DIR, fname)
        if not os.path.exists(path):
            _save_surface_png(surf, path)

    # Background
    bg_path = os.path.join(IMG_DIR, "background.png")
    if not os.path.exists(bg_path):
        w, h = screen_size
        _save_surface_png(_mk_background(w, h), bg_path)

    return bg_path

# ---------- Loading & API ----------
def init_assets(cell_size, screen_size):
    global CELL_IMG_SIZE, IMAGES, SFX
    CELL_IMG_SIZE = cell_size
    bg_path = ensure_assets(screen_size)

    # Load images
    def load_scale(name, sub=None):
        path = os.path.join(IMG_DIR if not sub else os.path.join(IMG_DIR, sub), name)
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, (CELL_IMG_SIZE, CELL_IMG_SIZE))

    IMAGES = {
        "robot_blue": load_scale("blue.png", sub="robots"),
        "robot_red":  load_scale("red.png", sub="robots"),
        "coin":       load_scale("coin.png"),
        "heart":      load_scale("heart.png"),
        "bonus":      load_scale("bonus.png"),
        "trap":       load_scale("trap.png"),
        "obstacle":   load_scale("obstacle.png"),
    }

    bg_raw = pygame.image.load(os.path.join(IMG_DIR, "background.png")).convert()
    IMAGES["background"] = bg_raw

    # Load SFX as MP3
    _ensure_mixer_inited()
    SFX = {}
    for key in ["coin","health","bonus","trap","attack","playerwin","aiwin"]:
        path = os.path.join(SND_DIR, f"{key}.mp3")
        if os.path.exists(path):
            SFX[key] = pygame.mixer.Sound(path)
            SFX[key].set_volume(0.5)

def start_music(loop=True):
    _ensure_mixer_inited()
    for fname in ["bg_music.mp3", "bg_music.ogg"]:  # try mp3 first
        music_path = os.path.join(SND_DIR, fname)
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(0.25)
            pygame.mixer.music.play(-1 if loop else 0)
            break

def get_image(key):
    return IMAGES.get(key)

def play_sfx(key):
    snd = SFX.get(key)
    if snd:
        snd.play()
