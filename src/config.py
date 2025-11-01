
GRID_WIDTH = 12
GRID_HEIGHT = 12

# Resources
NUM_RESOURCES = 12
RESOURCE_TYPES = {
    'coin': {
        'score': 10,
        'color': (255, 255, 0)          # yellow
    },
    'health': {
        'score': 0,
        'heal': 20,
        'color': (0, 255, 0)            # green
    },
    'shield': {'score': 0, 'buff': 'shield', 'color': (0,255,255)},  # cyan

}

# Traps
NUM_TRAPS = 8
TRAP_TYPES = {
    'spike': {
        'damage': 10,
        'color': (255, 0, 0)            # red
    },
    'fire': {
        'damage': 15,
        'color': (255, 100, 0)          # orange
    },
}

NUM_OBSTACLES = 18
MAX_TURNS = 90
