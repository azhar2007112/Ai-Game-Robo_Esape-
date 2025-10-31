# robot.py
import time
from config import RESOURCE_TYPES, TRAP_TYPES
from utils import play_sfx

class Robot:
    def __init__(self, name, pos, personality='Balanced'):
        self.name = name
        self.pos = pos
        self.health = 100
        self.score = 0
        self.buffs = {}  # store active buffs with expiry time, e.g. {"shield": expiry_time}
        self.personality = personality
        self.last_collected = None
        self.last_pickup_type = None

    def has_buff(self, buff_name):
        """Check if buff is still active."""
        now = time.time()
        if buff_name in self.buffs:
            if self.buffs[buff_name] > now:
                return True
            else:
                # expired buff
                del self.buffs[buff_name]
        return False

    def update_buffs(self):
        """Remove expired buffs."""
        now = time.time()
        expired = [b for b, exp in self.buffs.items() if exp <= now]
        for b in expired:
            del self.buffs[b]

    def move(self, dx, dy, board):
        newx, newy = self.pos[0] + dx, self.pos[1] + dy
        if 0 <= newx < board.size and 0 <= newy < board.size:
            if board.grid[newx][newy] == "X":  
                # obstacle handling
                if self.has_buff("shield"):
                    board.grid[newx][newy] = "."  # break obstacle
                    if (newx, newy) in board.obstacles:
                        board.obstacles.remove((newx, newy))
                    print(f"{self.name} used SHIELD to break obstacle at {(newx,newy)}!")
                    del self.buffs["shield"]  # consume shield immediately
                    self.pos = (newx, newy)
                else:
                    return  # blocked by obstacle
            else:
                self.pos = (newx, newy)
                self.check_cell(board)

    def check_cell(self, board):
        if self.pos in board.resources:
            r_type = board.resources.pop(self.pos)
            props = RESOURCE_TYPES[r_type]
            self.last_pickup_type = r_type
            if 'score' in props:
                self.score += props['score']
            if 'heal' in props:
                self.health = min(100, self.health + props['heal'])
            if 'buff' in props:
                buff_name = props['buff']
                if buff_name == "shield":
                    self.buffs["shield"] = time.time() + 5  # 5 seconds
                    print(f"{self.name} gained SHIELD for 5s!")
                else:
                    self.buffs[buff_name] = time.time() + 5  # generic buff, default 5s
            board.grid[self.pos[0]][self.pos[1]] = "."
            self.last_collected = self.pos

            # --- Sounds by resource type
            if r_type.lower() in ('coin', 'gold', 'score'):
                play_sfx('coin')
            elif r_type.lower() in ('health', 'heart'):
                play_sfx('health')
            else:
                play_sfx('bonus')  # includes shield
            print(f"{self.name} collected {r_type}!")

        elif self.pos in board.traps:
            t_type = board.traps.pop(self.pos)
            damage = TRAP_TYPES[t_type]['damage']
            self.health -= damage
            board.grid[self.pos[0]][self.pos[1]] = "."
            play_sfx('trap')
            print(f"{self.name} stepped on {t_type}! -{damage} health")

    def attack(self, other):
        if self.distance(other) <= 2:
            other.health -= 15
            play_sfx('attack')
            setattr(self, 'last_attacked', True)
            print(f"{self.name} attacked {other.name}! -15 health")

    def distance(self, other):
        return abs(self.pos[0] - other.pos[0]) + abs(self.pos[1] - other.pos[1])
