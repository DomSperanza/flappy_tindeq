import pygame
import random
import asyncio
from tindeq_backend.tindeq import TindeqProgressor

# Initialize Pygame
pygame.init()

# Scaling factor
SCALE = 3  # Adjust this value to scale the entire game

# Screen dimensions
WIDTH, HEIGHT = int(800 * SCALE), int(600 * SCALE)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Bird properties
bird_x = int(50 * SCALE)
bird_y = HEIGHT // 2
bird_radius = int(10 * SCALE)

# Pipe properties
pipe_width = int(100 * SCALE)
pipe_gap = int(200 * SCALE)
pipe_speed = int(5 * SCALE)
pipe_frequency = int(1500 )  # milliseconds
last_pipe = pygame.time.get_ticks() - pipe_frequency

pipes = []

def draw_bird():
    pygame.draw.circle(screen, RED, (bird_x, int(bird_y)), bird_radius)

def draw_pipes():
    for pipe in pipes:
        pygame.draw.rect(screen, BLACK, pipe)

def update_pipes():
    global pipes
    for pipe in pipes:
        pipe.x -= pipe_speed
    pipes = [pipe for pipe in pipes if pipe.x + pipe_width > 0]

def create_pipe():
    height = random.randint(int(100 * SCALE), HEIGHT - int(100 * SCALE) - pipe_gap)
    top_pipe = pygame.Rect(WIDTH, 0, pipe_width, height)
    bottom_pipe = pygame.Rect(WIDTH, height + pipe_gap, pipe_width, HEIGHT - height - pipe_gap)
    pipes.append(top_pipe)
    pipes.append(bottom_pipe)

def check_collision():
    return False
    bird_rect = pygame.Rect(bird_x - bird_radius, bird_y - bird_radius, bird_radius * 2, bird_radius * 2)
    for pipe in pipes:
        if bird_rect.colliderect(pipe):
            return True
    if bird_y <= 0 or bird_y >= HEIGHT:
        return True
    return False

class Wrapper:
    def __init__(self, weight_queue):
        self.weight_queue = weight_queue

    def log_force_sample(self, time, weight):
        self.weight_queue.put_nowait(weight)

async def initialize_tindeq(tindeq):
    await tindeq.get_batt()
    await asyncio.sleep(0.5)
    await tindeq.get_fw_info()
    await asyncio.sleep(0.5)
    await tindeq.get_err()
    await asyncio.sleep(0.5)
    await tindeq.clear_err()
    await asyncio.sleep(0.5)
    await tindeq.soft_tare()
    await asyncio.sleep(1)

async def log_weight(tindeq, weight_queue):
    while True:
        try:
            await tindeq.start_logging_weight()
        except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(1)

async def tindeq_task(weight_queue, initialization_complete):
    wrap = Wrapper(weight_queue)
    async with TindeqProgressor(wrap) as tindeq:
        await initialize_tindeq(tindeq)
        initialization_complete.set()  # Signal that initialization is complete
        await log_weight(tindeq, weight_queue)

async def main_game(weight_queue, initialization_complete):
    await initialization_complete.wait()  # Wait for initialization to complete

    global bird_y, last_pipe, pipes  # Ensure these are global

    weight_min = 5
    weight_max = 20
    running = True

    clock = pygame.time.Clock()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Check weight input
        while not weight_queue.empty():
            weight = await weight_queue.get()

            mapped_weight = HEIGHT - ((weight - weight_min) / (weight_max - weight_min) * HEIGHT)
            
            bird_y = max(0, min(mapped_weight, HEIGHT))  # Ensure bird_y stays within screen bounds
            print(f"Weight: {weight}, Bird Y: {bird_y}, Min: {weight_min}, Max: {weight_max}")

        # Pipe management
        current_time = pygame.time.get_ticks()
        if current_time - last_pipe > pipe_frequency:
            create_pipe()
            last_pipe = current_time

        update_pipes()

        # Drawing
        screen.fill(WHITE)
        draw_bird()
        draw_pipes()
        pygame.display.flip()

        if check_collision():
            running = False

        await asyncio.sleep(0.03)  # Cap the frame rate at 30 FPS

    pygame.quit()

async def main():
    weight_queue = asyncio.Queue()
    initialization_complete = asyncio.Event()

    # Run the Tindeq task and game loop concurrently
    tindeq_future = asyncio.ensure_future(tindeq_task(weight_queue, initialization_complete))
    game_future = asyncio.ensure_future(main_game(weight_queue, initialization_complete))

    await asyncio.gather(tindeq_future, game_future)

if __name__ == "__main__":
    asyncio.run(main())

