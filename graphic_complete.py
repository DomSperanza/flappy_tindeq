import pygame
import random
import time
import asyncio
from pygame.locals import *
from tindeq_backend.tindeq import TindeqProgressor

# TARGET VARIABLES FOR SCALING
TARGET_SCREEN_WIDTH = 1200
TARGET_SCREEN_HEIGHT = 1500

# SCALING FACTOR
SCALING_FACTOR = TARGET_SCREEN_WIDTH / 400

SCREEN_WIDTH = int(400 * SCALING_FACTOR)
SCREEN_HEIGHT = int(600 * SCALING_FACTOR)
GAME_SPEED = 20

GROUND_WIDTH = 2 * SCREEN_WIDTH
GROUND_HEIGHT = int(100 * SCALING_FACTOR)

PIPE_WIDTH = int(80 * SCALING_FACTOR)
PIPE_HEIGHT = int(500 * SCALING_FACTOR)

PIPE_GAP = int(10 * SCALING_FACTOR)

wing = 'assets/audio/wing.wav'
hit = 'assets/audio/hit.wav'

pygame.mixer.init()

class Bird(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.images = [
            pygame.transform.scale(pygame.image.load('assets/sprites/bluebird-upflap.png').convert_alpha(), (int(34 * SCALING_FACTOR), int(24 * SCALING_FACTOR))),
            pygame.transform.scale(pygame.image.load('assets/sprites/bluebird-midflap.png').convert_alpha(), (int(34 * SCALING_FACTOR), int(24 * SCALING_FACTOR))),
            pygame.transform.scale(pygame.image.load('assets/sprites/bluebird-downflap.png').convert_alpha(), (int(34 * SCALING_FACTOR), int(24 * SCALING_FACTOR)))
        ]
        self.current_image = 0
        self.image = self.images[self.current_image]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDTH / 6
        self.rect[1] = SCREEN_HEIGHT / 2

    def update(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]

    def set_position(self, y):
        self.rect[1] = max(0, min(y, SCREEN_HEIGHT - self.rect.height))

    def begin(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]

class Pipe(pygame.sprite.Sprite):
    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.transform.scale(pygame.image.load('assets/sprites/pipe-green.png').convert_alpha(), (PIPE_WIDTH, PIPE_HEIGHT))
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = -(SCREEN_HEIGHT-ysize)
        else:
            self.rect[1] = SCREEN_HEIGHT - ysize
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect[0] -= GAME_SPEED

class Ground(pygame.sprite.Sprite):
    def __init__(self, xpos):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.transform.scale(pygame.image.load('assets/sprites/base.png').convert_alpha(), (GROUND_WIDTH, GROUND_HEIGHT))
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT

    def update(self):
        self.rect[0] -= GAME_SPEED

def is_off_screen(sprite):
    return sprite.rect[0] < -(sprite.rect[2])

def get_random_pipes(xpos):
    size = random.randint(int(100 * SCALING_FACTOR), int((TARGET_SCREEN_HEIGHT-100) * SCALING_FACTOR))
    pipe = Pipe(False, xpos, size)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
    return pipe, pipe_inverted

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
    GAME_SPEED = 20
    await initialization_complete.wait()  # Wait for initialization to complete

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Flappy Bird')

    BACKGROUND = pygame.transform.scale(pygame.image.load('assets/sprites/background-day.png'), (SCREEN_WIDTH, SCREEN_HEIGHT))
    BEGIN_IMAGE = pygame.transform.scale(pygame.image.load('assets/sprites/message.png').convert_alpha(), (int(184 * SCALING_FACTOR), int(267 * SCALING_FACTOR)))

    bird_group = pygame.sprite.Group()
    bird = Bird()
    bird_group.add(bird)

    ground_group = pygame.sprite.Group()
    for i in range(2):
        ground = Ground(GROUND_WIDTH * i)
        ground_group.add(ground)

    pipe_group = pygame.sprite.Group()
    for i in range(2):
        pipes = get_random_pipes(SCREEN_WIDTH * i + 800)
        pipe_group.add(pipes[0])
        pipe_group.add(pipes[1])

    clock = pygame.time.Clock()
    begin = True
    weight_min =0
    weight_max = 40
    
    while begin:


        clock.tick(TARGET_SCREEN_WIDTH/50)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return
            if event.type == KEYDOWN:
                if event.key == K_SPACE or event.key == K_UP:
                    pygame.mixer.music.load(wing)
                    pygame.mixer.music.play()
                    begin = False

        while not weight_queue.empty():
            weight = await weight_queue.get()
            mapped_weight = SCREEN_HEIGHT - ((weight - weight_min) / (weight_max - weight_min) * SCREEN_HEIGHT)
            bird.set_position(mapped_weight)
            print(f"Weight: {weight}, Bird Y: {bird.rect[1]}, Min: {weight_min}, Max: {weight_max}")

        screen.blit(BACKGROUND, (0, 0))
        screen.blit(BEGIN_IMAGE, (SCREEN_WIDTH // 2 - BEGIN_IMAGE.get_width() // 2, SCREEN_HEIGHT // 2 - BEGIN_IMAGE.get_height() // 2))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])
            new_ground = Ground(GROUND_WIDTH - 20)
            ground_group.add(new_ground)

        bird.begin()
        ground_group.update()
        bird_group.draw(screen)
        ground_group.draw(screen)
        pygame.display.update()
        await asyncio.sleep(0.03)



    weight_min =0
    weight_max = 35

    
    speed_up = .01
    while True:
        speed_up = speed_up+.01
        GAME_SPEED = GAME_SPEED+speed_up
        clock.tick(TARGET_SCREEN_WIDTH/50)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return

        while not weight_queue.empty():
            weight = await weight_queue.get()
            mapped_weight = SCREEN_HEIGHT - ((weight - weight_min) / (weight_max - weight_min) * SCREEN_HEIGHT)
            bird.set_position(mapped_weight)
            print(f"Weight: {weight}, Bird Y: {bird.rect[1]}, Min: {weight_min}, Max: {weight_max}")

        screen.blit(BACKGROUND, (0, 0))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])
            new_ground = Ground(GROUND_WIDTH - 20)
            ground_group.add(new_ground)

        if is_off_screen(pipe_group.sprites()[0]):
            pipe_group.remove(pipe_group.sprites()[0])
            pipe_group.remove(pipe_group.sprites()[0])
            pipes = get_random_pipes(SCREEN_WIDTH * 2)
            pipe_group.add(pipes[0])
            pipe_group.add(pipes[1])

        bird_group.update()
        ground_group.update()
        pipe_group.update()
        bird_group.draw(screen)
        pipe_group.draw(screen)
        ground_group.draw(screen)
        pygame.display.update()

        # if (pygame.sprite.groupcollide(bird_group, ground_group, False, False, pygame.sprite.collide_mask) or
        #         pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask)):
        if pygame.sprite.spritecollide(bird, pipe_group,False,pygame.sprite.collide_mask):
            pygame.mixer.music.load(hit)
            pygame.mixer.music.play()
            time.sleep(5)

            break
        await asyncio.sleep(0.03)

async def main():
    weight_queue = asyncio.Queue()
    initialization_complete = asyncio.Event()
    tindeq_future = asyncio.ensure_future(tindeq_task(weight_queue, initialization_complete))
    game_future = asyncio.ensure_future(main_game(weight_queue, initialization_complete))
    await asyncio.gather(tindeq_future, game_future)

if __name__ == "__main__":
    asyncio.run(main())
