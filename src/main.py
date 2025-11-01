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
    # ---------- Main Loop ----------
running = True
while running:
    dt = clock.tick(FPS)/1000.0
    current_state = game_state.get_state()

    # occasional ambient particles
    if random.random() < 0.08:
        spawn_particle()
    update_particles(dt)

    if current_state == 'playing':
        player.update_buffs()
        ai.update_buffs()

    # DRAW
    if current_state == 'welcome':
        # cinematic background
        screen.blit(get_image("background"), (0,0))
        title = title_font.render("Robo Rescue", True, (240,245,255))
        # subtitle = subtitle_font.render("Futuristic Arena", True, (200,220,245))
        screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 70))
        # screen.blit(subtitle, (SCREEN_W//2 - subtitle.get_width()//2, 130))

        start_btn = Button((SCREEN_W//2-100, 220, 200, 52), 'Start')
        mx,my = pygame.mouse.get_pos()
        start_btn.draw(screen, start_btn.is_hover((mx,my)))
        draw_eesc_hint() 

    elif current_state == 'select':
        # Clear the whole screen (covers HUD too)
        screen.fill((0,0,0))  
        # Then draw background
        screen.blit(get_image("background"), (0,0))
        title = title_font.render("Select Difficulty", True, (240,245,255))
        screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 60))
        btns = [
            Button((SCREEN_W//2-220, 180, 140, 48), 'Easy'),
            Button((SCREEN_W//2-70,  180, 140, 48), 'Medium'),
            Button((SCREEN_W//2+80,  180, 140, 48), 'Hard'),
        ]
        mx,my = pygame.mouse.get_pos()
        for b in btns:
            b.draw(screen, b.is_hover((mx,my)))
        draw_eesc_hint()   # ESC = Quit


    elif current_state == 'mode':
        screen.fill((0,0,0)) 
        screen.blit(get_image("background"), (0,0))
        title = title_font.render("Choose Mode", True, (240,245,255))
        screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 60))
        btns = [
            Button((SCREEN_W//2-220, 180, 180, 48), 'AI vs Player'),
            Button((SCREEN_W//2+40,  180, 180, 48), 'AI vs AI'),
        ]
        mx,my = pygame.mouse.get_pos()
        for b in btns: b.draw(screen, b.is_hover((mx,my)))
        draw_esc_hint() 

    elif current_state == 'playing':
        draw_board()
        draw_stats()

        # Right side turn indicator (AI vs AI)
        if MODE == 'pvp_ai':
            current_ai = 'Blue' if turn % 2 == 0 else 'Red'
            turn_text = f"Turn {turn + 1}: {current_ai}"
            if ai_paused: turn_text += " (PAUSED)"
            right_x = SCREEN_W - 12
            base_y = GRID_HEIGHT*CELL_SIZE
            turn_surface = font.render(turn_text, True, (210,220,255))
            screen.blit(turn_surface, (right_x - turn_surface.get_width(), base_y+10))
            pause_surface = small_font.render("SPACE: Pause/Resume", True, (160,170,190))
            screen.blit(pause_surface, (right_x - pause_surface.get_width(), base_y+35))
            esc_surface = small_font.render("ESC: Menu", True, (160,170,190))
            screen.blit(esc_surface, (right_x - esc_surface.get_width(), base_y+55))
        
    elif current_state == 'gameover':
        
        pygame.draw.rect(screen, (16,18,24), (0,0,SCREEN_W, SCREEN_H))
        result = round_result or "Draw!"
        title = title_font.render("Game Over", True, (220,230,255))
        screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 64))
        rs = subtitle_font.render(result, True, (220,230,255))
        screen.blit(rs, (SCREEN_W//2 - rs.get_width()//2, 130))

        current_level = AI_LEVEL if AI_LEVEL else "Unknown"
        level_hs = high_scores.get(current_level, 0)
        level_name = current_level.title()
        msg = f"High Score ({level_name}): {level_hs}"
        hs = subtitle_font.render(msg, True, (180,190,220))
        screen.blit(hs, (SCREEN_W//2 - hs.get_width()//2, 170))

        mx,my = pygame.mouse.get_pos()
        play_btn = Button(PLAY_BTN_RECT, 'Play Again')
        quit_btn = Button(QUIT_BTN_RECT, 'Main Menu')
        play_btn.draw(screen, play_btn.is_hover((mx,my)))
        quit_btn.draw(screen, quit_btn.is_hover((mx,my)))

    pygame.display.flip()

    # EVENTS
    moved=False
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if current_state == 'welcome':
                pygame.quit(); sys.exit()   # Quit directly from welcome
            elif current_state == 'playing':
                game_state.set_state('select')  # Back to difficulty select
            elif current_state == 'mode':
                game_state.set_state('select')  # Back to difficulty select
            elif current_state == 'gameover':
                game_state.set_state('select')  # Back to difficulty select
            elif current_state == 'select':
                pygame.quit(); sys.exit()   # ESC from select also quits


        if current_state == 'welcome':
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                start_btn = Button((SCREEN_W//2-100, 220, 200, 52), 'Start')
                if start_btn.is_hover(event.pos):
                    game_state.set_state('select')

        elif current_state == 'select':
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                easy = Button((SCREEN_W//2-220, 180, 140, 48), 'Easy')
                medium = Button((SCREEN_W//2-70,  180, 140, 48), 'Medium')
                hard = Button((SCREEN_W//2+80,  180, 140, 48), 'Hard')
                if easy.is_hover(event.pos):
                    AI_LEVEL='easy'
                    AI_TURN_INTERVAL = get_ai_interval(AI_LEVEL)
                    game_state.set_state('mode')
                elif medium.is_hover(event.pos):
                    AI_LEVEL='medium'
                    AI_TURN_INTERVAL = get_ai_interval(AI_LEVEL)
                    game_state.set_state('mode')
                elif hard.is_hover(event.pos):
                    AI_LEVEL='hard'
                    AI_TURN_INTERVAL = get_ai_interval(AI_LEVEL)
                    game_state.set_state('mode')

        elif current_state == 'mode':
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                ai_player = Button((SCREEN_W//2-220, 180, 180, 48), 'AI vs Player')
                ai_ai = Button((SCREEN_W//2+40,  180, 180, 48), 'AI vs AI')
                if ai_player.is_hover(event.pos):
                    MODE='pve'
                    board, player, ai = setup_level(AI_LEVEL)
                    player_px, player_py = tile_to_px(player.pos)
                    ai_px, ai_py = tile_to_px(ai.pos)
                    turn=0; ai_turn_accum=0.0
                    game_state.set_state('playing')
                elif ai_ai.is_hover(event.pos):
                    MODE='pvp_ai'
                    board, player, ai = setup_level(AI_LEVEL)
                    player_px, player_py = tile_to_px(player.pos)
                    ai_px, ai_py = tile_to_px(ai.pos)
                    turn=0; ai_turn_accum=0.0
                    game_state.set_state('playing')

        elif current_state == 'gameover':
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if PLAY_BTN_RECT.collidepoint(event.pos):
                    board, player, ai = setup_level(AI_LEVEL)
                    player_px, player_py = tile_to_px(player.pos)
                    ai_px, ai_py = tile_to_px(ai.pos)
                    turn = 0
                    game_state.set_state('playing')
                elif QUIT_BTN_RECT.collidepoint(event.pos):
                    game_state.set_state('welcome')

        elif current_state == 'playing':
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_UP and MODE=='pve':
                    player.last_pos = player.pos
                    player.move(-1,0,board); moved=True
                elif event.key==pygame.K_DOWN and MODE=='pve':
                    player.last_pos = player.pos
                    player.move(1,0,board); moved=True
                elif event.key==pygame.K_LEFT and MODE=='pve':
                    player.last_pos = player.pos
                    player.move(0,-1,board); moved=True
                elif event.key==pygame.K_RIGHT and MODE=='pve':
                    player.last_pos = player.pos
                    player.move(0,1,board); moved=True

                elif event.key==pygame.K_f: player.attack(ai); moved=True
                elif event.key==pygame.K_r and AI_LEVEL!='hard':
                    if not hasattr(player,'pending_ranged') or player.pending_ranged is None:
                        player.pending_ranged = {'target_pos': ai.pos, 'turns': 1}
                        moved=True
                elif event.key==pygame.K_SPACE and MODE=='pvp_ai':
                    ai_paused = not ai_paused
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if AI_LEVEL=='hard' and MODE=='pve':
                    gx, gy = event.pos[0]//CELL_SIZE, event.pos[1]//CELL_SIZE
                    if 0<=gy<GRID_HEIGHT and 0<=gx<GRID_WIDTH and event.pos[1] < GRID_HEIGHT*CELL_SIZE:
                        start = (int(player_px+CELL_SIZE/2), int(player_py+CELL_SIZE/2))
                        end = (gx*CELL_SIZE+CELL_SIZE//2, gy*CELL_SIZE+CELL_SIZE//2)
                        FX_ARROWS.append({'start':start,'end':end,'t':0.0,'color':(60,140,255),'damage':20,'owner':'player','grid_target':(gy,gx)})
                        moved=True

    # GAME LOGIC
    if current_state == 'playing' and MODE=='pvp_ai' and not ai_paused:
        ai_turn_accum += dt
        if ai_turn_accum >= AI_TURN_INTERVAL:
            ai_turn_accum = 0.0
            if turn % 2 == 0:
                ai.last_pos = ai.pos
                ai_vs_ai_decision(player, ai, board, level=AI_LEVEL)
                if AI_LEVEL=='medium' and getattr(player,'last_collected',None) is not None:
                    x,y = player.last_collected
                    if board.grid[x][y]==".": board.grid[x][y] = "X"; board.obstacles.add((x,y)); recent_block=((x,y),50)
                    player.last_collected = None
                if AI_LEVEL=='hard' and hasattr(player,'pending_ranged') and player.pending_ranged:
                    start = (int(player_px+CELL_SIZE/2), int(player_py+CELL_SIZE/2))
                    tgt = player.pending_ranged['target_pos']
                    end = (tgt[1]*CELL_SIZE+CELL_SIZE//2, tgt[0]*CELL_SIZE+CELL_SIZE//2)
                    FX_ARROWS.append({'start':start,'end':end,'t':0.0,'color':(60,140,255),'damage':20,'owner':'player','grid_target':tgt})
                    player.pending_ranged = None
            else:
                ai.last_pos = ai.pos
                ai_vs_ai_decision(ai, player, board, level=AI_LEVEL)
                if AI_LEVEL=='medium' and getattr(ai,'last_collected',None) is not None:
                    x,y = ai.last_collected
                    if board.grid[x][y]==".": board.grid[x][y] = "X"; board.obstacles.add((x,y)); recent_block=((x,y),50)
                    ai.last_collected = None
                if AI_LEVEL=='hard' and hasattr(ai,'pending_ranged') and ai.pending_ranged:
                    start = (int(ai_px+CELL_SIZE/2), int(ai_py+CELL_SIZE/2))
                    tgt = ai.pending_ranged['target_pos']
                    end = (tgt[1]*CELL_SIZE+CELL_SIZE//2, tgt[0]*CELL_SIZE+CELL_SIZE//2)
                    FX_ARROWS.append({'start':start,'end':end,'t':0.0,'color':(255,90,90),'damage':20,'owner':'ai','grid_target':tgt})
                    ai.pending_ranged = None
            turn += 1

    elif current_state == 'playing' and moved:
        ai.last_pos = ai.pos
        ai_decision(ai, player, board, level=AI_LEVEL)
        if AI_LEVEL=='medium' and getattr(ai,'last_collected',None) is not None:
            x,y = ai.last_collected
            if board.grid[x][y]==".": board.grid[x][y] = "X"; board.obstacles.add((x,y)); recent_block=((x,y),50)
            ai.last_collected = None
        if AI_LEVEL=='hard':
            predicted = predict_next_move(player, board)
            start = (int(ai_px+CELL_SIZE/2), int(ai_py+CELL_SIZE/2))
            end = (predicted[1]*CELL_SIZE+CELL_SIZE//2, predicted[0]*CELL_SIZE+CELL_SIZE//2)
            FX_ARROWS.append({
                'start': start,
                'end': end,
                't': 0.4,
                'color': (255,90,90),
                'damage': 20,
                'owner': 'ai',
                'grid_target': predicted
            })

        if AI_LEVEL!='hard' and hasattr(player,'pending_ranged') and player.pending_ranged:
            player.pending_ranged['turns'] -= 1
            if player.pending_ranged['turns'] <= 0:
                target_pos = player.pending_ranged['target_pos']
                if ai.pos == target_pos:
                    ai.health -= 20
                player.pending_ranged = None
        turn += 1

        # high-score
        total_score = player.score
        if total_score > high_scores.get(AI_LEVEL,0):
            high_scores[AI_LEVEL] = total_score
            last_round_new_high = True
        else:
            last_round_new_high = False

    # Smooth approach to target tiles
    def approach(curr, target):
        if curr < target: curr = min(target, curr + MOVE_SPEED*dt)
        elif curr > target: curr = max(target, curr - MOVE_SPEED*dt)
        return curr
    tpx, tpy = tile_to_px(player.pos)
    apx, apy = tile_to_px(ai.pos)
    player_px = approach(player_px, tpx); player_py = approach(player_py, tpy)
    ai_px = approach(ai_px, apx);       ai_py = approach(ai_py, apy)

    # Update arrows + recent block fade
    if AI_LEVEL=='hard' and FX_ARROWS:
        remain=[]
        for fx in FX_ARROWS:
            fx['t'] += ARROW_SPEED*dt
            if fx['t'] >= 1.0:
                if fx['owner']=='player':
                    if ai.pos == fx['grid_target']: 
                        ai.health -= fx['damage']
                        play_sfx("attack") 
                else:
                    if player.pos == fx['grid_target']: 
                        player.health -= fx['damage']
                        play_sfx("attack")
            else:
                remain.append(fx)
        FX_ARROWS = remain
    if recent_block:
        (rbx,rby),frames = recent_block
        frames -= 1
        recent_block = None if frames<=0 else ((rbx,rby), frames)

    # Win conditions
    if current_state == 'playing':
        if hasattr(board,'end_player') and player.pos == board.end_player and player.health>0:
            round_result = 'Player wins!'
            play_sfx("playerwin")
            game_state.set_state('gameover')
        elif hasattr(board,'end_ai') and ai.pos == board.end_ai and ai.health>0:
            round_result = 'AI wins!'
            play_sfx("aiwin")
            game_state.set_state('gameover')
        elif player.health<=0:
            round_result = 'AI wins!'
            play_sfx("aiwin")
            game_state.set_state('gameover')
        elif ai.health<=0:
            round_result = 'Player wins!'
            play_sfx("playerwin")
            game_state.set_state('gameover')
        elif turn>=MAX_TURNS:
            if player.score>ai.score:
                round_result = 'Player wins!'
                play_sfx("playerwin")
            elif ai.score>player.score:
                round_result = 'AI wins!'
                play_sfx("aiwin")
            else:
                round_result = 'Draw!'
            game_state.set_state('gameover')

pygame.quit()
print("=== Game Over ===")
