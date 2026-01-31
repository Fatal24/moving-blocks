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

class Box:
    def __init__(self, coords, direction, date):
        self.coords = coords
        self.direction = direction
        self.date = date
        self.img = pygame.image.load(box_path)

    def move_one_place:
        

class Goal:
    def __init__(self, player):
        self.player = player
        self.img = pygame.image.load(goal_path)

class Tile:
    def __init__(self, direction=Direction.STILL, box=False):
        self.direction = direction
        self.box = box
        if self.direction != Direction.STILL and not box:
            self.img = pygame.transform.rotate(pygame.image.load(arrow_path), (self.direction - direction.NORTH) * 90)
        elif box:
            self.img = pygame.image.load(box_path)
        else:
            self.img = pygame.image.load(background_path)


class Spawner:
    def __init__(self, direction=Direction.NORTH, threshold=5):
        self.direction = direction
        self.spawn_epoch = 0
        self.epoch_threshold = threshold
        self.img = pygame.image.load(spawner_path)
    
    def spawn(self, force_spawn=False):
        if force_spawn:

