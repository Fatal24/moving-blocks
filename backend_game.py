import math
import random
import numpy as np
from backend_helper import Goal, Tile

MAX_GAME_SIDE_LENGTH = 31
MIN_GAME_SIDE_LENGTH = 15

global game = []

def iter_game():

def play_game(seed:int, *ips:list[list[int]]):
    #initialisation of game
    np.set_printoptions(edgeitems=30, linewidth=100000)
    dirn = seed % 4
    # 0: up, 1: right, 2: down, 3: left, initial dirn (rotates clockwise every turn)
    size = int(15 + (seed % ((MAX_GAME_SIDE_LENGTH - MIN_GAME_SIDE_LENGTH)/2))*2)
    game = np.zeros((size, size))
    game[random.randint(2,size//2 - 2)][random.randint(2,size//2 - 2)] = 1
    game[random.randint(size//2 + 2, size - 2)][random.randint(2,size//2 - 2)] = 2
    game[random.randint(2, size // 2 - 2)][random.randint( size//2 + 2, size - 2)] = 3
    game[random.randint(size//2 + 2, size - 2)][random.randint( size//2 + 2, size - 2)] = 4


if __name__ == '__main__':
    seed = random.randint(0, 2**32 - 1)
    play_game(seed=seed)
    
