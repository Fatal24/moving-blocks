import math
import random
from typing import Dict
import numpy as np
from backend_helper import Goal, Tile

MAX_GAME_SIDE_LENGTH = 31
MIN_GAME_SIDE_LENGTH = 15

class Game:
    def __init__(self, ips, seed):
        self.ips = ips
        self.seed = seed
        dirn = seed % 4 # TODO: change to enum when available (by below)
        # 0: up, 1: right, 2: down, 3: left, initial dirn (rotates clockwise every turn)
        size = int(15 + (seed % ((MAX_GAME_SIDE_LENGTH - MIN_GAME_SIDE_LENGTH) / 2)) * 2)
        game = [[Tile()] * size] * size
        game[size // 2][size // 2] = 9
        game[random.randint(2, size // 2 - 2)][random.randint(2, size // 2 - 2)] = 1
        game[random.randint(size // 2 + 2, size - 2)][random.randint(2, size // 2 - 2)] = 2
        game[random.randint(2, size // 2 - 2)][random.randint(size // 2 + 2, size - 2)] = 3
        game[random.randint(size // 2 + 2, size - 2)][random.randint(size // 2 + 2, size - 2)] = 4

        self.boxes = [] 


    def move_boxes:
        


# debug: np.set_printoptions(edgeitems=30, linewidth=100000)

    # game initialised, begin iteration
    # while([recieving packets]):


if __name__ == '__main__':
    seed = random.randint(0, 2**32 - 1)
    game = Game([], seed=seed)
    
