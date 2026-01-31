from enum import Enum

class Direction(Enum):
    STILL = 0
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

class Box:
    def __init__(self, coords, direction, date):
        self.coords = coords
        self.direction = direction
        self.date = date

        

class Goal:
    def __init__(self, player):
        self.player = player

class Tile:
    def __init__(self, direction=Direction.STILL, box=False):
        self.direction = direction
        self.box = box

class Spawner:
    def __init__(self, direction=Direction.NORTH, threshold=5):
        self.direction = direction
        self.spawn_epoch = 0
        self.epoch_threshold = threshold
    
    def spawn(self, force_spawn=False):
        if force_spawn:

