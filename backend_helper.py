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
        if other.value == 0 or self.value + other.value < 5:
            return self.value + other.value
        return Direction((self.value + other.value + 1)%5)
    def __sub__(self, other):
        if other.value == 0 or self.value - other.value > 0:
            return self.value - other.value
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
        self.score = 0
        self.img = pygame.image.load(goal_path)

class Tile:
    def __init__(self, directions=[], lifespan = 5):
        # TODO: REVERT TO directions when we decide to tolerate multiple directions
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

    def change_direction(self, direction):
        pass
        """if not self.directions:
            self.directions += direction
        else:
            breakflag = False
            for dirn in self.directions:
                if (dirn.value + 2) % 4 == self.direction.value:
                    self.directions.remove(self.direction.value)
                    breakflag = True
                    break
            if not breakflag:
                self.directions += direction"""

class Spawner:
    def __init__(self, coords, direction=Direction.NORTH, threshold=5):
        self.direction = direction
        self.date = 0
        self.spawn_epoch = 0
        self.epoch_threshold = threshold
        self.coords = coords
        self.img = pygame.image.load(spawner_path)
    
    #return box after initialising
    def spawn(self, force_spawn=False):

        self.date += 1
        self.spawn_epoch += 1

        if force_spawn or self.spawn_epoch == self.epoch_threshold:
            self.direction = self.direction + Direction.NORTH
            self.spawn_epoch = 0
            return Box(self.coords, self.direction, self.date)
	
        return None
        

