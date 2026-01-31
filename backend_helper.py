from enum import Enum

class Direction(Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

class Box:
    def __init__(self, coords, direction, date):
        self.coords = coords
        self.direction = direction
        self.date = date

    def move_one_place:
        

class Goal:
    def __init__(self, player):
        self.player = player

class Tile:
    def __init__(self, direction=None, box=False):
        self.direction = direction
        self.box = box
