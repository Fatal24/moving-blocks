import math
from copy import deepcopy
import random
from typing import Dict, List
import numpy as np
from backend_helper import Goal, Tile, Direction, Spawner

MAX_GAME_SIDE_LENGTH = 25
MIN_GAME_SIDE_LENGTH = 15

class Game:
    def __init__(self, ips, seed):
        self.ips = ips
        self.seed = seed
        dirn = Direction(seed % 4) + Direction.NORTH
        # 0: up, 1: right, 2: down, 3: left, initial dirn (rotates clockwise every turn)
        size = int(MIN_GAME_SIDE_LENGTH + (seed % ((MAX_GAME_SIDE_LENGTH - MIN_GAME_SIDE_LENGTH) / 2)) * 2)
        Grid = List[List[Tile | Spawner | Goal]]
        self.game : Grid = [[Tile() for _ in range(size)] for _ in range(size)]
        self.game[size // 2][size // 2] = Spawner((size//2, size//2))
        random.seed(self.seed)
        self.game[random.randint(2, size // 2 - 2)][random.randint(2, size // 2 - 2)] = Goal(1)
        self.game[random.randint(size // 2 + 2, size - 2)][random.randint(2, size // 2 - 2)] = Goal(2)
        self.game[random.randint(2, size // 2 - 2)][random.randint(size // 2 + 2, size - 2)] = Goal(3)
        self.game[random.randint(size // 2 + 2, size - 2)][random.randint(size // 2 + 2, size - 2)] = Goal(4)

        self.boxes = []
        self.old = []
        self.animation_boxes = []
        self.spawner = Spawner((size // 2, size // 2))
        self.scores = [0, 0, 0, 0]

        
    def move_boxes(self):

        if self.boxes:
            self.spawner.spawn()

            temp = []
            temp_animation = []

            for idx, x in enumerate(self.boxes):
                temp_coords = x.coords

                match x.direction:
                    case Direction.NORTH:
                        temp_coords = (temp_coords[0], (temp_coords[1] - 1) % len(self.game))
                    case Direction.SOUTH:
                        temp_coords = (temp_coords[0], (temp_coords[1] + 1) % len(self.game))
                    case Direction.EAST:
                        temp_coords = ((temp_coords[0] + 1) % len(self.game), temp_coords[1])
                    case Direction.WEST:
                        temp_coords = ((temp_coords[0] - 1) % len(self.game), temp_coords[1])
                
                conflict = False

                for idy, y in enumerate(temp[:-1]):
                    if temp_coords == y.coords:
                        conflict = True
                        temp_animation.append((x.coords,Direction.STILL))
                        break

                if not conflict:
                    x.coords = temp_coords
                    if type(self.game[x.coords[1]][x.coords[0]]) == Goal:
                        self.scores[self.game[x.coords[1]][x.coords[0]].player - 1] += 1
                    
                    
                    else:
                        temp_animation.append((x.coords,x.direction))
                        if self.game[x.coords[1]][x.coords[0]].direction != Direction.STILL and self.game[x.coords[1]][x.coords[0]] != x.direction:
                            x.direction = self.game[x.coords[1]][x.coords[0]].direction 
                            temp.append(x)


            self.old = self.boxes
            self.boxes = deepcopy(temp)
            self.animation_boxes = deepcopy(temp_animation)

        else:
            new_box = self.spawner.spawn(True)
            self.boxes.append(new_box)

if __name__ == '__main__':
    seed = random.randint(0, 2**32 - 1)
    game = Game([], seed=seed)