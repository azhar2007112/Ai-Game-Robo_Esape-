import random
from config import GRID_WIDTH, GRID_HEIGHT, NUM_RESOURCES, NUM_TRAPS, NUM_OBSTACLES, RESOURCE_TYPES, TRAP_TYPES

class Board:
    def __init__(self, size, num_resources=None, num_traps=None, num_obstacles=None):
        self.size = size
        self.grid = [["." for _ in range(size)] for _ in range(size)]
        self.resources = {}  # (x,y): resource_type
        self.traps = {}      # (x,y): trap_type
        self.obstacles = set()

        # End goals
        self.end_player = (self.size-1, self.size-1)
        self.end_ai     = (0, 0)

        # AI vs AI mode goals (explicitly reserved too)
        self.end_blue   = (self.size-1, self.size-1)
        self.end_red    = (0, 0)

        self.num_resources = num_resources if num_resources is not None else NUM_RESOURCES
        self.num_traps = num_traps if num_traps is not None else NUM_TRAPS
        self.num_obstacles = num_obstacles if num_obstacles is not None else NUM_OBSTACLES

        # Reserve goal cells so nothing spawns there
        self.reserved_cells = {self.end_player, self.end_ai, self.end_blue, self.end_red}

        self.place_items()

    def place_items(self):
        # Place resources
        for _ in range(self.num_resources):
            x,y = self._random_empty()
            r_type = random.choice(list(RESOURCE_TYPES.keys()))
            self.grid[x][y] = "E"
            self.resources[(x,y)] = r_type

        # Place traps
        for _ in range(self.num_traps):
            x,y = self._random_empty()
            t_type = random.choice(list(TRAP_TYPES.keys()))
            self.grid[x][y] = "T"
            self.traps[(x,y)] = t_type

        # Place obstacles
        for _ in range(self.num_obstacles):
            x,y = self._random_empty()
            self.grid[x][y] = "X"
            self.obstacles.add((x,y))

    def _random_empty(self):
        while True:
            x = random.randrange(self.size)
            y = random.randrange(self.size)
            if self.grid[x][y] == "." and (x,y) not in self.reserved_cells:
                return x,y
