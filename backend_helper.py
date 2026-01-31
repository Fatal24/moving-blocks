import os.path
import pygame
from enum import Enum

background_path = os.path.join("Assets", "Tile_Background.png")
arrow_path = os.path.join("Assets", "Tile_Arrow.png")
box_path = os.path.join("Assets", "Box.png")
goal_path = os.path.join("Assets", "Goal.png")
spawner_path = os.path.join("Assets", "Spawner.png")

class Direction(Enum):
    STILL = 0
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

    def __add__(self, other):
        if other.value == 0:
            return self.value
        return Direction((self.value + other.value + 1)%5)
    def __sub__(self, other):
        if other.value == 0:
            return self.value
        return Direction((self.value - other.value - 1) % 5)

class Box:
    def __init__(self, coords, direction, date):
        self.coords = coords
        self.direction = direction
        self.date = date
        self.img = pygame.image.load(box_path)


class Goal:
    def __init__(self, player):
        self.player = player
        self.img = pygame.image.load(goal_path)

class Tile:
    def __init__(self, directions=[], lifespan = 5):
        self.directions = directions
        if not directions:
            self.direction = Direction.STILL
        else:
            self.direction = directions[0]
        self.lifespan = lifespan
        self.i = 0

    def get_direction(self):
        if not self.directions:
            return Direction.STILL

        return_dir = self.directions[self.i]
        self.i = (self.i+1) % len(self.directions)
        
        return return_dir


    

class Spawner:
    def __init__(self, coords, direction=Direction.NORTH, threshold=5):
        self.direction = direction
        self.date = 0
        self.spawn_epoch = 0
        self.epoch_threshold = threshold
        self.img = pygame.image.load(spawner_path)
    
    #return box after initialising
    def spawn(self, force_spawn=False):
        successors = {NORTH : EAST, EAST : SOUTH, SOUTH : WEST, WEST : NORTH}

        self.date += 1
        self.spawn_epoch += 1

	if force_spawn or self.spawn_epoch == self.epoch_threshold:
            self.direction = successors[self.direction]
            self.spawn_epoch = 0
            return Box(coords, self.direction, self.date)
	
        return None
        

