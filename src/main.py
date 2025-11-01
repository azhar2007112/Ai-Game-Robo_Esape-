import pygame, sys, random, math, time
from board import Board
from robot import Robot
from ai_strategies import ai_decision, ai_vs_ai_decision, predict_next_move

from config import GRID_WIDTH, GRID_HEIGHT, MAX_TURNS, NUM_RESOURCES, NUM_TRAPS, NUM_OBSTACLES, RESOURCE_TYPES, TRAP_TYPES
from utils import init_assets, start_music, get_image, play_sfx

# ---------- State Manager ----------
class GameState:
    def __init__(self):
        self.current = 'welcome'
    def set_state(self, new_state):
        self.current = new_state
    def get_state(self):
        return self.current

game_state = GameState()

# ---------- Constants ----------
CELL_SIZE = 64       # slightly larger for nicer sprites
HUD_HEIGHT = 140
FPS = 60
AI_LEVEL = 'easy'
RANGED_ATTACK_DELAY_TURNS = 1


def get_ai_interval(level):
    if level == "easy":
        return 0.5   # slower, more relaxed
    elif level == "medium":
        return 0.3   # moderate speed
    else:  # hard
        return 0.15  # very fast & challenging


pygame.init()
SCREEN_W = GRID_WIDTH*CELL_SIZE
SCREEN_H = GRID_HEIGHT*CELL_SIZE + HUD_HEIGHT
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Robo Rescue")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 64)
subtitle_font = pygame.font.SysFont(None, 32)
small_font = pygame.font.SysFont(None, 18)

# Init assets (auto-create placeholders if needed)
init_assets(CELL_SIZE, (SCREEN_W, SCREEN_H-HUD_HEIGHT))
start_music(loop=True)

ARROW_SPEED = 2.5
FX_ARROWS = []

def level_counts(level):
    if level=='easy':
        return int(NUM_RESOURCES*1.4), int(NUM_TRAPS*0.6), int(NUM_OBSTACLES*0.7)
    if level=='medium':
        return NUM_RESOURCES, NUM_TRAPS, NUM_OBSTACLES
    return int(NUM_RESOURCES*0.7), int(NUM_TRAPS*1.4), int(NUM_OBSTACLES*1.2)

def setup_level(level):
    nr, nt, no = level_counts(level)
    b = Board(GRID_WIDTH, num_resources=nr, num_traps=nt, num_obstacles=no)
    p = Robot("Player", (0,0))
    a = Robot("AI", (GRID_WIDTH-1, GRID_HEIGHT-1), random.choice(["Aggressive","Defensive","Balanced"]))
    return b, p, a

board, player, ai = setup_level(AI_LEVEL)
turn = 0
high_scores = {'easy':0, 'medium':0, 'hard':0}
last_round_new_high = False
round_result = ""
display_player_score = 0.0
display_ai_score = 0.0
recent_block = None

MODE = 'pve'  # or 'pvp_ai'
AI_TURN_INTERVAL = get_ai_interval(AI_LEVEL)

ai_turn_accum = 0.0
ai_paused = False

# Buttons (gameover)
PLAY_BTN_RECT = pygame.Rect(SCREEN_W//2-220, 230, 180, 48)
QUIT_BTN_RECT = pygame.Rect(SCREEN_W//2+40, 230, 180, 48)

# Smooth render positions
def tile_to_px(pos):  # (row,col) -> (px,py)
    return pos[1]*CELL_SIZE, pos[0]*CELL_SIZE

player_px, player_py = tile_to_px(player.pos)
ai_px, ai_py = tile_to_px(ai.pos)
MOVE_SPEED = CELL_SIZE*6  # px/s

# ----------- Visual juice -----------
# Particles (ambient sparks)
particles = []
def spawn_particle():
    x = random.randint(0, SCREEN_W-1)
    y = random.randint(0, GRID_HEIGHT*CELL_SIZE - 1)
    vx = random.uniform(-10, 10)
    vy = -random.uniform(20, 60)
    life = random.uniform(0.6, 1.4)
    particles.append([x, y, vx, vy, life])

def update_particles(dt):
    for p in particles[:]:
        p[0] += p[2]*dt
        p[1] += p[3]*dt
        p[4] -= dt
        if p[4] <= 0 or p[1] < -10:
            particles.remove(p)

def draw_particles():
    for p in particles:
        alpha = int(max(0, min(1, p[4])) * 160)
        s = pygame.Surface((3,3), pygame.SRCALPHA)
        s.fill((120,220,255, alpha))
        screen.blit(s, (int(p[0]), int(p[1])))

# ----------- Drawing -----------
def draw_board():
    # Background (no grid look)
    bg = get_image("background")
    screen.blit(bg, (0,0))

    # Recent blocked highlight
    if recent_block and recent_block[1] > 0:
        (rbx,rby),_ = recent_block
        rx,ry = rby*CELL_SIZE, rbx*CELL_SIZE
        s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        s.fill((120,120,200,80))
        screen.blit(s, (rx, ry))

    # World elements as images
    for i in range(GRID_HEIGHT):
        for j in range(GRID_WIDTH):
            cell = board.grid[i][j]
            px, py = j*CELL_SIZE, i*CELL_SIZE
            if cell == "X":
                screen.blit(get_image("obstacle"), (px, py))
            elif cell == "T":
                screen.blit(get_image("trap"), (px, py))
            elif cell == "E":
                # choose sprite by resource type
                r_type = board.resources.get((i,j))
                if r_type in ('health','heart'):
                    screen.blit(get_image("heart"), (px, py))
                elif r_type in ('coin','gold','score'):
                    screen.blit(get_image("coin"), (px, py))
                else:
                    # other bonuses, e.g. speed/shield
                    screen.blit(get_image("bonus"), (px, py))

    # Entities
    screen.blit(get_image("robot_blue"), (int(player_px), int(player_py)))
    screen.blit(get_image("robot_red"),  (int(ai_px),     int(ai_py)))

    # Health bars (thin)
    def draw_health_bar(px, py, health, color):
        bw = CELL_SIZE
        bh = 6
        x = int(px); y = int(py + CELL_SIZE - 8)
        pygame.draw.rect(screen, (0,0,0), (x, y, bw, bh), border_radius=3)
        hw = int(bw * max(0, min(1, health/100)))
        pygame.draw.rect(screen, color, (x, y, hw, bh), border_radius=3)
    draw_health_bar(player_px, player_py, player.health, (80,200,80))
    draw_health_bar(ai_px, ai_py, ai.health, (200,80,80))

    # Animated arrows (hard)
    if AI_LEVEL=='hard':
        for fx in FX_ARROWS:
            sx,sy = fx['start']; ex,ey = fx['end']; t = fx['t']
            cx = sx + (ex - sx)*t; cy = sy + (ey - sy)*t
            col = fx['color']
            pygame.draw.line(screen, col, (sx,sy), (cx,cy), 3)
            pygame.draw.circle(screen, col, (int(cx),int(cy)), 4)

    # Particles on top
    draw_particles()

def draw_stats():
    pygame.draw.rect(screen, (16,18,24), (0, GRID_HEIGHT*CELL_SIZE, SCREEN_W, HUD_HEIGHT))
    pygame.draw.line(screen, (40,48,60), (0, GRID_HEIGHT*CELL_SIZE), (SCREEN_W, GRID_HEIGHT*CELL_SIZE), 2)

    global display_player_score, display_ai_score
    display_player_score += (player.score - display_player_score)*0.2
    display_ai_score += (ai.score - display_ai_score)*0.2

    base_y = GRID_HEIGHT*CELL_SIZE
    left_x = 12

    blue_text = font.render(f"Blue: {player.health}   Score: {int(display_player_score)}", True, (120,170,255))
    red_text  = font.render(f"Red : {ai.health}   Score: {int(display_ai_score)}", True, (255,120,120))
    screen.blit(blue_text, (left_x, base_y+12))
    screen.blit(red_text,  (left_x, base_y+40))

    # Add ESC hint inside HUD bar
    esc_surface = small_font.render("ESC: Menu", True, (160,170,190))
    right_x = SCREEN_W - 12
    screen.blit(esc_surface, (right_x - esc_surface.get_width(), base_y+12))


def draw_esc_hint():
    esc_surface = small_font.render("ESC: Menu", True, (160,170,190))
    right_x = SCREEN_W - 12
    base_y = GRID_HEIGHT * CELL_SIZE 
    # place at the bottom of HUD area
    screen.blit(esc_surface, (right_x - esc_surface.get_width(), base_y + 10))

def draw_eesc_hint():
    esc_surface = small_font.render("ESC: Quit", True, (160,170,190))
    right_x = SCREEN_W - 12
    base_y = GRID_HEIGHT * CELL_SIZE 
    # place at the bottom of HUD area
    screen.blit(esc_surface, (right_x - esc_surface.get_width(), base_y + 10))


# ---------- UI Button ----------
class Button:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label
    def draw(self, surf, hover=False):
        bg = (245,248,255) if hover else (235,238,244)
        border = (90,120,200) if hover else (70,90,140)
        pygame.draw.rect(surf, bg, self.rect, border_radius=12)
        pygame.draw.rect(surf, border, self.rect, width=2, border_radius=12)
        text = subtitle_font.render(self.label, True, (30,40,60))
        surf.blit(text, (self.rect.centerx - text.get_width()//2, self.rect.centery - text.get_height()//2))
    def is_hover(self, pos):
        return self.rect.collidepoint(pos)