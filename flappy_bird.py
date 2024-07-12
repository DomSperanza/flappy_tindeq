import pygame
import random
import asyncio
import struct
import uuid
from bleak import BleakScanner, BleakClient
from tindeq_backend.tindeq import TindeqProgressor  # Assuming tindeq.py is in the same directory

# Initialize Pygame and variables
pygame.init()

# Define a scale factor to make the game scalable
scale_factor = 1.5  # Adjust this to scale the game

screen_width, screen_height = int(400 * scale_factor), int(600 * scale_factor)
screen = pygame.display.set_mode((screen_width, screen_height))

bird = pygame.Rect(int(100 * scale_factor), screen_height // 2, int(30 * scale_factor), int(30 * scale_factor))  # Bird's rectangle
bird2 = pygame.Rect(int(100 * scale_factor), screen_height // 2, int(30 * scale_factor), int(30 * scale_factor))  # Bird's rectangle
game_active = True
pipes = []  # List to store pipes
pipe_height = [int(200 * scale_factor), int(300 * scale_factor), int(400 * scale_factor)]  # Possible pipe heights
pipe_surface = pygame.Surface((int(100 * scale_factor), int(500 * scale_factor)))  # Pipe surface
pipe_surface.fill((0, 255, 0))  # Green pipes
SPAWNPIPE = pygame.USEREVENT
pipe_spawn_interval = int(1200 / scale_factor)  # Adjust pipe spawn interval based on scale factor
pygame.time.set_timer(SPAWNPIPE, pipe_spawn_interval)  # Event timer for spawning pipes
pipe_gap = int(200 * scale_factor)  # Gap between upper and lower pipe

# Function to update the bird's position based on force data
def update_bird_position(force):
    global bird2
    # Update bird's position based on force and user input
    bird2.y =force
    #bird.y = max(0, min(bird.y, screen_height - bird.height))  # Ensure bird stays within screen bounds
    print(force)
    print(f"Bird position: {bird2.y}")  # Debug print

# Define functions for game mechanics
def draw_pipes(pipes):
    for pipe in pipes:
        if pipe.bottom >= screen_height:  # Lower pipe
            screen.blit(pipe_surface, pipe)
        else:  # Upper pipe, flip vertically
            flip_pipe = pygame.transform.flip(pipe_surface, False, True)
            screen.blit(flip_pipe, pipe)

def move_pipes(pipes):
    for pipe in pipes:
        pipe.centerx -= int(5 * scale_factor)  # Adjust pipe speed based on scale factor
    return [pipe for pipe in pipes if pipe.right > -50]

def create_pipe():
    pipe_pos = random.choice(pipe_height)
    bottom_pipe = pipe_surface.get_rect(midtop=(screen_width + int(100 * scale_factor), pipe_pos))
    top_pipe = pipe_surface.get_rect(midbottom=(screen_width + int(100 * scale_factor), pipe_pos - pipe_gap))
    return bottom_pipe, top_pipe

# Adjust initial bird movement and gravity
bird_movement = 0
gravity = 0.25 * scale_factor  # Adjust gravity based on scale factor

# Comment out the check_collision function for simplicity
# def check_collision(pipes):
#     global game_active
#     for pipe in pipes:
#         if bird.colliderect(pipe):
#             print("Collision with pipe.")
#             game_active = False
#     # Allow the bird to be slightly off the screen before ending the game
#     if bird.top <= -10 * scale_factor or bird.bottom >= screen_height + 10 * scale_factor:  # Adjusted bounds check
#         print("Bird out of bounds.")
#         game_active = False

# Wrapper class to handle force data logging
class Wrapper:
    def log_force_sample(self, time, weight):
        print(f"Received force sample: {weight} at time {time}")  # Debug print
        update_bird_position(weight)

# Main game loop
async def main_game_loop(queue):
    global game_active, pipes, bird_movement
    while game_active:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_active = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird_movement = -6 * scale_factor

            if event.type == SPAWNPIPE:
                pipes.extend(create_pipe())

        # Check for new weight data from the queue
        try:
            # Non-blocking check; adjust as needed based on your game's design
            weight_data = queue.get_nowait()
            # Use weight_data to adjust bird's position or other game mechanics
        except asyncio.QueueEmpty:
            # No new data, proceed with the game loop as usual
            pass

        screen.fill((0, 0, 0))
        bird = bird2
        pipes = move_pipes(pipes)
        draw_pipes(pipes)
        pygame.draw.rect(screen, (255, 0, 0), bird)
        pygame.display.update()
        clock.tick(60)

    pygame.quit()

async def main():
    queue = asyncio.Queue()
    wrap = Wrapper()
    async with TindeqProgressor(wrap) as tindeq:
        # Start logging weight and passing data to the queue
        asyncio.create_task(tindeq.start_logging_weight(queue))
        # Pass the queue to the game loop so it can use the data
        await main_game_loop(queue)

# Start the event loop
asyncio.run(main())