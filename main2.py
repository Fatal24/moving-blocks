import pygame
import socket
import threading
import time
import random
from enum import Enum
from copy import deepcopy
import backend_game
import backend_helper
from backend_helper import Direction, Tile, Box, Goal, Spawner
from helper import send_obj, recv_obj
from Config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS

# Game States
class GameState(Enum):
    MAIN_MENU = 0
    CONNECTING = 1
    LOBBY = 2
    PLANNING = 3
    SIMULATION = 4
    GAME_OVER = 5

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
BLUE = (100, 150, 255)
DARK_BLUE = (50, 100, 200)
GREEN = (100, 255, 100)
DARK_GREEN = (50, 200, 50)
RED = (255, 100, 100)
YELLOW = (255, 255, 100)

# Network Configuration
SERVER_IP = "127.0.0.1"  # Change to server IP
PORT = 6000

class Button:
    """Simple button class for UI"""
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
    
    def draw(self, screen, font):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        text_surface = font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class ArrowButton:
    """Arrow selection button for tile placement"""
    def __init__(self, x, y, size, direction):
        self.rect = pygame.Rect(x, y, size, size)
        self.direction = direction
        self.selected = False
    
    def draw(self, screen):
        color = YELLOW if self.selected else LIGHT_GRAY
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        # Draw arrow
        center = self.rect.center
        arrow_size = self.rect.width // 3
        
        points = []
        if self.direction == Direction.NORTH:
            points = [(center[0], center[1] - arrow_size),
                     (center[0] - arrow_size//2, center[1] + arrow_size//2),
                     (center[0] + arrow_size//2, center[1] + arrow_size//2)]
        elif self.direction == Direction.SOUTH:
            points = [(center[0], center[1] + arrow_size),
                     (center[0] - arrow_size//2, center[1] - arrow_size//2),
                     (center[0] + arrow_size//2, center[1] - arrow_size//2)]
        elif self.direction == Direction.EAST:
            points = [(center[0] + arrow_size, center[1]),
                     (center[0] - arrow_size//2, center[1] - arrow_size//2),
                     (center[0] - arrow_size//2, center[1] + arrow_size//2)]
        elif self.direction == Direction.WEST:
            points = [(center[0] - arrow_size, center[1]),
                     (center[0] + arrow_size//2, center[1] - arrow_size//2),
                     (center[0] + arrow_size//2, center[1] + arrow_size//2)]
        
        if points:
            pygame.draw.polygon(screen, BLACK, points)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Moving Blocks")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.title_font = pygame.font.Font(None, 72)
        self.large_font = pygame.font.Font(None, 48)
        self.medium_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Game state
        self.state = GameState.MAIN_MENU
        self.running = True
        
        # Network
        self.sock = None
        self.connected = False
        self.received = []
        self.send_queue = []
        self.network_thread = None
        
        # Game data
        self.game = None
        self.player_number = -1
        self.players_ready = [False, False, False, False]
        self.is_ready = False
        self.seed = None
        
        # Planning phase
        self.selected_direction = None
        self.placed_tile = False
        self.tile_placement = None
        self.all_players_placed = False
        
        # Simulation phase
        self.simulation_tick = 0
        self.max_simulation_ticks = 100
        self.tick_duration = 0.5  # seconds per tick
        self.last_tick_time = 0
        
        # UI elements
        self.create_ui_elements()
        
        # Grid rendering
        self.grid_offset_x = 50
        self.grid_offset_y = 100
        self.tile_size = 20
        
    def create_ui_elements(self):
        """Create UI buttons and elements"""
        # Main menu buttons
        button_width = 200
        button_height = 60
        button_x = SCREEN_WIDTH // 2 - button_width // 2
        
        self.connect_button = Button(
            button_x, 300, button_width, button_height,
            "Connect", GREEN, DARK_GREEN
        )
        
        self.quit_button = Button(
            button_x, 400, button_width, button_height,
            "Quit", RED, (200, 50, 50)
        )
        
        # Lobby ready button
        self.ready_button = Button(
            button_x, 500, button_width, button_height,
            "Ready", GREEN, DARK_GREEN
        )
        
        # Planning phase arrow buttons
        arrow_size = 60
        center_x = SCREEN_WIDTH - 150
        center_y = SCREEN_HEIGHT // 2
        spacing = 80
        
        self.arrow_buttons = {
            Direction.NORTH: ArrowButton(center_x, center_y - spacing, arrow_size, Direction.NORTH),
            Direction.SOUTH: ArrowButton(center_x, center_y + spacing, arrow_size, Direction.SOUTH),
            Direction.EAST: ArrowButton(center_x + spacing, center_y, arrow_size, Direction.EAST),
            Direction.WEST: ArrowButton(center_x - spacing, center_y, arrow_size, Direction.WEST),
        }
        
        # Confirm placement button
        self.confirm_button = Button(
            center_x - 75, center_y + spacing * 2, 150, 50,
            "Confirm", BLUE, DARK_BLUE
        )
    
    def connect_to_server(self, ip=SERVER_IP, port=PORT):
        """Establish connection to server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((ip, port))
            self.sock.settimeout(None)
            self.connected = True
            
            # Start network thread
            self.network_thread = threading.Thread(
                target=self.recv_loop, daemon=True
            )
            self.network_thread.start()
            
            # Send connection request
            self.send_packet({"type": "INIT_CONNECTION"})
            
            print(f"[CLIENT] Connected to {ip}:{port}")
            return True
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            self.connected = False
            return False
    
    def recv_loop(self):
        """Network receive loop (runs in separate thread)"""
        while self.running and self.connected:
            try:
                packet = recv_obj(self.sock)
                if packet is None:
                    print("[CLIENT] Disconnected from server")
                    self.connected = False
                    break
                self.received.append(packet)
            except Exception as e:
                print(f"[CLIENT] Receive error: {e}")
                break
    
    def send_packet(self, packet):
        """Queue packet for sending"""
        self.send_queue.append(packet)
    
    def process_send_queue(self):
        """Send queued packets"""
        while self.send_queue and self.connected:
            try:
                packet = self.send_queue.pop(0)
                send_obj(self.sock, packet)
            except Exception as e:
                print(f"[CLIENT] Send error: {e}")
                self.connected = False
                break
    
    def process_network_packets(self):
        """Process received network packets"""
        while self.received:
            packet = self.received.pop(0)
            
            if packet.get("type") == "PLAYER_NUMBER":
                self.player_number = packet["data"]["player_number"]
                print(f"[CLIENT] Assigned player number: {self.player_number}")
            
            elif packet.get("type") == "LOBBY_UPDATE":
                self.players_ready = packet["data"]["players_ready"]
            
            elif packet.get("type") == "INIT_GAME_STATE":
                self.seed = packet["data"]["seed"]
                self.max_simulation_ticks = packet["data"].get("max_ticks", 100)
                self.initialize_game()
                self.state = GameState.PLANNING
                print(f"[CLIENT] Game initialized with seed: {self.seed}")
            
            elif packet.get("type") == "ALL_PLAYERS_PLACED":
                # Receive all player placements
                placements = packet["data"]["placements"]
                self.apply_placements(placements)
                self.all_players_placed = True
                self.state = GameState.SIMULATION
                self.simulation_tick = 0
                self.last_tick_time = time.time()
                print("[CLIENT] Starting simulation phase")
            
            elif packet.get("type") == "SIMULATION_COMPLETE":
                # Return to planning phase
                self.reset_planning_phase()
                self.state = GameState.PLANNING
                print("[CLIENT] Simulation complete, returning to planning")
    
    def initialize_game(self):
        """Initialize game with received seed"""
        self.game = backend_game.Game([], self.seed)
        print(f"[CLIENT] Game board size: {len(self.game.game)}x{len(self.game.game)}")
    
    def apply_placements(self, placements):
        """Apply all player tile placements to the game board"""
        for placement in placements:
            coords = placement["coords"]
            direction = placement["direction"]
            try:
                x, y = coords
                tile = self.game.game[y][x]
                if isinstance(tile, Tile):
                    tile.direction = direction
                    print(f"[CLIENT] Applied placement at ({x}, {y}) with direction {direction}")
            except Exception as e:
                print(f"[CLIENT] Error applying placement: {e}")
    
    def reset_planning_phase(self):
        """Reset state for new planning phase"""
        self.selected_direction = None
        self.placed_tile = False
        self.tile_placement = None
        self.all_players_placed = False
        for button in self.arrow_buttons.values():
            button.selected = False
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEMOTION:
                pos = pygame.mouse.get_pos()
                if self.state == GameState.MAIN_MENU:
                    self.connect_button.check_hover(pos)
                    self.quit_button.check_hover(pos)
                elif self.state == GameState.LOBBY:
                    self.ready_button.check_hover(pos)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                
                if self.state == GameState.MAIN_MENU:
                    if self.connect_button.is_clicked(pos):
                        self.state = GameState.CONNECTING
                        if self.connect_to_server():
                            self.state = GameState.LOBBY
                        else:
                            self.state = GameState.MAIN_MENU
                    
                    elif self.quit_button.is_clicked(pos):
                        self.running = False
                
                elif self.state == GameState.LOBBY:
                    if self.ready_button.is_clicked(pos) and not self.is_ready:
                        self.is_ready = True
                        self.send_packet({"type": "PLAYER_READY"})
                
                elif self.state == GameState.PLANNING:
                    # Check arrow button clicks
                    for direction, button in self.arrow_buttons.items():
                        if button.is_clicked(pos):
                            self.selected_direction = direction
                            # Deselect all others
                            for btn in self.arrow_buttons.values():
                                btn.selected = False
                            button.selected = True
                    
                    # Check grid click for placement
                    if self.selected_direction and not self.placed_tile:
                        grid_click = self.get_grid_position(pos)
                        if grid_click:
                            x, y = grid_click
                            if self.is_valid_placement(x, y):
                                self.tile_placement = {"coords": (x, y), "direction": self.selected_direction}
                                # Visual feedback - update local game state
                                self.game.game[y][x].direction = self.selected_direction
                    
                    # Check confirm button
                    if self.confirm_button.is_clicked(pos) and self.tile_placement:
                        self.placed_tile = True
                        self.send_packet({
                            "type": "TILE_PLACE",
                            "data": self.tile_placement
                        })
                        print(f"[CLIENT] Placed tile at {self.tile_placement['coords']}")
    
    def get_grid_position(self, mouse_pos):
        """Convert mouse position to grid coordinates"""
        if not self.game:
            return None
        
        x = (mouse_pos[0] - self.grid_offset_x) // self.tile_size
        y = (mouse_pos[1] - self.grid_offset_y) // self.tile_size
        
        grid_size = len(self.game.game)
        if 0 <= x < grid_size and 0 <= y < grid_size:
            return (x, y)
        return None
    
    def is_valid_placement(self, x, y):
        """Check if tile placement is valid"""
        if not self.game:
            return False
        
        tile = self.game.game[y][x]
        # Can only place on empty tiles
        return isinstance(tile, Tile) and tile.direction == Direction.STILL
    
    def update(self):
        """Update game logic"""
        # Process network
        self.process_network_packets()
        self.process_send_queue()
        
        # Update based on state
        if self.state == GameState.SIMULATION:
            self.update_simulation()
    
    def update_simulation(self):
        """Update simulation phase"""
        current_time = time.time()
        
        if current_time - self.last_tick_time >= self.tick_duration:
            self.last_tick_time = current_time
            
            # Execute one game tick
            self.game.move_boxes()
            self.simulation_tick += 1
            
            print(f"[CLIENT] Simulation tick {self.simulation_tick}/{self.max_simulation_ticks}")
            
            # Check if simulation is complete
            if self.simulation_tick >= self.max_simulation_ticks:
                print("[CLIENT] Simulation phase complete")
                # Server will handle transition
    
    def draw(self):
        """Render the current state"""
        self.screen.fill(WHITE)
        
        if self.state == GameState.MAIN_MENU:
            self.draw_main_menu()
        elif self.state == GameState.CONNECTING:
            self.draw_connecting()
        elif self.state == GameState.LOBBY:
            self.draw_lobby()
        elif self.state == GameState.PLANNING:
            self.draw_planning()
        elif self.state == GameState.SIMULATION:
            self.draw_simulation()
        
        pygame.display.flip()
    
    def draw_main_menu(self):
        """Draw main menu screen"""
        title = self.title_font.render("Moving Blocks", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)
        
        self.connect_button.draw(self.screen, self.medium_font)
        self.quit_button.draw(self.screen, self.medium_font)
    
    def draw_connecting(self):
        """Draw connecting screen"""
        text = self.large_font.render("Connecting...", True, BLACK)
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(text, text_rect)
    
    def draw_lobby(self):
        """Draw lobby/waiting room"""
        title = self.large_font.render("Waiting Room", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)
        
        # Display player status
        y_offset = 200
        for i, ready in enumerate(self.players_ready):
            status = "Ready" if ready else "Waiting"
            color = GREEN if ready else RED
            
            player_text = self.medium_font.render(f"Player {i + 1}: {status}", True, color)
            self.screen.blit(player_text, (SCREEN_WIDTH // 2 - 100, y_offset + i * 50))
        
        if not self.is_ready:
            self.ready_button.draw(self.screen, self.medium_font)
        else:
            ready_text = self.medium_font.render("Waiting for others...", True, BLUE)
            ready_rect = ready_text.get_rect(center=(SCREEN_WIDTH // 2, 500))
            self.screen.blit(ready_text, ready_rect)
    
    def draw_planning(self):
        """Draw planning phase"""
        # Title
        title = self.medium_font.render("Planning Phase", True, BLACK)
        self.screen.blit(title, (10, 10))
        
        # Player info
        info = self.small_font.render(f"You are Player {self.player_number + 1}", True, BLACK)
        self.screen.blit(info, (10, 50))
        
        # Draw game grid
        self.draw_game_board()
        
        # Draw arrow selection UI
        instruction = self.small_font.render("Select direction and click a tile:", True, BLACK)
        self.screen.blit(instruction, (SCREEN_WIDTH - 300, 50))
        
        for button in self.arrow_buttons.values():
            button.draw(self.screen)
        
        # Draw spawner direction
        if self.game and self.game.spawner:
            spawner_text = self.small_font.render(
                f"Spawner facing: {self.game.spawner.direction.name}",
                True, BLACK
            )
            self.screen.blit(spawner_text, (SCREEN_WIDTH - 300, 100))
        
        # Show confirm button if tile is placed
        if self.tile_placement and not self.placed_tile:
            self.confirm_button.draw(self.screen, self.small_font)
        
        # Show waiting message if placed
        if self.placed_tile:
            waiting_text = self.medium_font.render("Waiting for other players...", True, BLUE)
            waiting_rect = waiting_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
            self.screen.blit(waiting_text, waiting_rect)
    
    def draw_simulation(self):
        """Draw simulation phase"""
        # Title
        title = self.medium_font.render("Simulation Phase", True, BLACK)
        self.screen.blit(title, (10, 10))
        
        # Tick counter
        tick_text = self.small_font.render(
            f"Tick: {self.simulation_tick}/{self.max_simulation_ticks}",
            True, BLACK
        )
        self.screen.blit(tick_text, (10, 50))
        
        # Draw game board with moving boxes
        self.draw_game_board()
    
    def draw_game_board(self):
        """Draw the game grid and entities"""
        if not self.game:
            return
        
        grid_size = len(self.game.game)
        
        # Calculate tile size to fit on screen
        available_width = SCREEN_WIDTH - 400  # Leave space for UI
        available_height = SCREEN_HEIGHT - 150
        
        self.tile_size = min(available_width // grid_size, available_height // grid_size)
        self.tile_size = max(15, min(self.tile_size, 30))  # Clamp between 15 and 30
        
        # Draw grid
        for y in range(grid_size):
            for x in range(grid_size):
                rect = pygame.Rect(
                    self.grid_offset_x + x * self.tile_size,
                    self.grid_offset_y + y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                
                tile = self.game.game[y][x]
                
                # Draw tile background
                pygame.draw.rect(self.screen, LIGHT_GRAY, rect)
                pygame.draw.rect(self.screen, DARK_GRAY, rect, 1)
                
                # Draw tile content
                if isinstance(tile, Spawner):
                    pygame.draw.rect(self.screen, BLUE, rect)
                    self.draw_arrow_in_rect(rect, tile.direction, BLACK)
                
                elif isinstance(tile, Goal):
                    colors = [RED, GREEN, BLUE, YELLOW]
                    color = colors[tile.player - 1] if tile.player <= 4 else BLACK
                    pygame.draw.circle(self.screen, color, rect.center, self.tile_size // 3)
                
                elif isinstance(tile, Tile) and tile.direction != Direction.STILL:
                    self.draw_arrow_in_rect(rect, tile.direction, DARK_BLUE)
        
        # Draw boxes
        if self.game.boxes:
            for box in self.game.boxes:
                bx, by = box.coords
                rect = pygame.Rect(
                    self.grid_offset_x + bx * self.tile_size,
                    self.grid_offset_y + by * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(self.screen, (139, 69, 19), rect)  # Brown box
                pygame.draw.rect(self.screen, BLACK, rect, 2)
    
    def draw_arrow_in_rect(self, rect, direction, color):
        """Draw a directional arrow in a rectangle"""
        center = rect.center
        arrow_size = rect.width // 4
        
        points = []
        if direction == Direction.NORTH:
            points = [(center[0], center[1] - arrow_size),
                     (center[0] - arrow_size//2, center[1] + arrow_size//2),
                     (center[0] + arrow_size//2, center[1] + arrow_size//2)]
        elif direction == Direction.SOUTH:
            points = [(center[0], center[1] + arrow_size),
                     (center[0] - arrow_size//2, center[1] - arrow_size//2),
                     (center[0] + arrow_size//2, center[1] - arrow_size//2)]
        elif direction == Direction.EAST:
            points = [(center[0] + arrow_size, center[1]),
                     (center[0] - arrow_size//2, center[1] - arrow_size//2),
                     (center[0] - arrow_size//2, center[1] + arrow_size//2)]
        elif direction == Direction.WEST:
            points = [(center[0] - arrow_size, center[1]),
                     (center[0] + arrow_size//2, center[1] - arrow_size//2),
                     (center[0] + arrow_size//2, center[1] + arrow_size//2)]
        
        if points:
            pygame.draw.polygon(self.screen, color, points)
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        # Cleanup
        if self.connected and self.sock:
            self.sock.close()
        pygame.quit()

if __name__ == "__main__":
    client = GameClient()
    client.run()