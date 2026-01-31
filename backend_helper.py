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
    def __init__(self, directions=[], lifespan = 5):
        self.directions = directions
        if directions == []:
            self.direction = STILL
	else:
            self.direction = directions[0]
        self.lifespan = lifespan
        self.i = 0

    def get_direction(self):
        if self.directions == []:
            return STILL

        return_dir = self.directions[i]
        i = (i+1) % len(self.directions)
        
        return return_dir


    

class Spawner:
    def __init__(self, coords, direction=Direction.NORTH, threshold=5):
        self.direction = direction
        self.date = 0
        self.spawn_epoch = 0
        self.epoch_threshold = threshold
    
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
        

