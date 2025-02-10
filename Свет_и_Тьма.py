import pygame
import sys
import sqlite3
import os

# Конфигурация окна
WINDOW_SIZE = WINDOW_WIDTH, WINDOW_HEIGHT = 1400, 700
BUTTON_PLACE = 50
FPS = 40
MAP_DIR = 'levels'
TILE_SIZE = None
WALL_PER = 0.2
DANGER_ZONE_INFLATE = 5
DEBUG_DRAW_RECTS = False

# Обозначения объектов
SIGNS = {
    'free': ' ', 'dynamic_stone': 'b', 'static_stone': 'B',
    'fire': 'F', 'water': 'W', 'water_door': '$',
    'fire_door': '#', 'wall': '-', 'fire_lake': 'f',
    'water_lake': 'w', 'kristal': 'k'  # Добавлен кристал
}

COLORS = {
    'dynamic_stone': (101, 66, 10), 'static_stone': (101, 66, 10),
    'fire': (225, 225, 210), 'water': (255, 255, 210),
    'water_door': (60, 100, 200), 'fire_door': (255, 50, 100),
    'wall': (101, 66, 33), 'fire_lake': (0, 0, 0),
    'water_lake': (255, 255, 210), 'kristal': (255, 215, 0)  # Золотой цвет
}

SIZES = {
    'dynamic_stone': None, 'static_stone': None,
    'fire': None, 'water': None, 'water_door': None,
    'fire_door': None, 'g_wall': None, 'v_wall': None,
    'fire_lake': None, 'water_lake': None,
    'kristal': None  # Добавлен размер
}

kristals = pygame.sprite.Group()

# Типы границ
TYPE_BORD = {'left': 1, 'right': 2, 'up': 3, 'bottom': 4}

# Группы спрайтов
all_sprites = pygame.sprite.Group()
walls = pygame.sprite.Group()
v_borders = pygame.sprite.Group()
g_borders = pygame.sprite.Group()
static_stones = pygame.sprite.Group()
dynamic_stones = pygame.sprite.Group()
fire_doors = pygame.sprite.Group()
water_doors = pygame.sprite.Group()
players_group = pygame.sprite.Group()
platforms = pygame.sprite.Group()
fire_lakes = pygame.sprite.Group()
water_lakes = pygame.sprite.Group()

# Глобальные ссылки на игроков
fire = None
water = None
fire_kartinka = "image/dark/sprite.png"
fire_kartinka_levo = "image/dark/levo.png"
fire_kartinka_pravo = "image/dark/pravo.png"
water_kartinka = "image/light/sprite.png"
water_kartinka_levo = "image/light/levo.png"
water_kartinka_pravo = "image/light/pravo.png"
stone_kartinka = "image/cube_sprite.png"
STONE_SCALE_FACTOR = 1.5
SPRITE_WIDTH_SCALE = 1.1
ROTATION_ANGLE = 25

class Border(pygame.sprite.Sprite):
    def __init__(self, x1, y1, x2, y2, t):
        super().__init__(all_sprites)
        self.t = t
        if x1 == x2:
            self.add(v_borders)
            self.image = pygame.Surface([1, y2 - y1])
            self.rect = pygame.Rect(x1, y1, 5, y2 - y1)
        else:
            self.add(g_borders)
            self.image = pygame.Surface([x2 - x1, 1])
            self.rect = pygame.Rect(x1, y1, x2 - x1, 5)


class Wall(pygame.sprite.Sprite):
    def __init__(self, pos, size, add_b=[]):
        super().__init__(all_sprites, platforms)
        self.add(walls)
        x, y = pos
        a, b = size

        if a > b:
            Border(x, y, x + a, y, TYPE_BORD['up'])
            Border(x, y + b, x + a, y + b, TYPE_BORD['bottom'])
            for side in add_b:
                if side == TYPE_BORD['left']:
                    Border(x, y, x, y + b, TYPE_BORD['left'])
                elif side == TYPE_BORD['right']:
                    Border(x + a, y, x + a, y + b, TYPE_BORD['right'])
        else:
            Border(x, y, x, y + b, TYPE_BORD['left'])
            Border(x + a, y, x + a, y + b, TYPE_BORD['right'])

        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(self.image, COLORS['wall'], (0, 0, *size))
        pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 1)
        self.rect = pygame.Rect(*pos, *size)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 2)


class Kristal(pygame.sprite.Sprite):
    def __init__(self, pos, size, level):
        super().__init__(all_sprites, kristals)
        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        self.level = level  # Добавляем уровень, на котором находится кристалл

        # Рисуем ромб (кристалл)
        pygame.draw.polygon(self.image, COLORS['kristal'], [
            (size[0]/2, 0),
            (size[0], size[1]/2),
            (size[0]/2, size[1]),
            (0, size[1]/2)
        ])
        self.rect = self.image.get_rect(topleft=pos)

    def update(self):
        # Проверяем столкновение с персонажами
        if pygame.sprite.collide_rect(self, fire):
            self.kill()  # Удаляем кристалл при соприкосновении
            save_kristal_collection(self.level, 'fire')  # Сохраняем сбор кристалла
        elif pygame.sprite.collide_rect(self, water):
            self.kill()  # Удаляем кристалл при соприкосновении
            save_kristal_collection(self.level, 'water')  # Сохраняем сбор кристалла

# Инициализация базы данных
def init_db():
    # Проверяем, существует ли файл базы данных
    if not os.path.exists('game.db'):
        # Создаем базу данных и таблицы
        conn = sqlite3.connect('game.db')
        cursor = conn.cursor()

        # Создаем таблицу для хранения собранных кристаллов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collected_kristals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                player TEXT NOT NULL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем таблицу для хранения прогресса игроков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player TEXT NOT NULL,
                level TEXT NOT NULL,
                kristals_collected INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE
            )
        ''')

        conn.commit()
        conn.close()

def save_kristal_collection(level, player):
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()

    # Добавляем запись о собранном кристалле
    cursor.execute('''
        INSERT INTO collected_kristals (level, player)
        VALUES (?, ?)
    ''', (level, player))

    # Обновляем прогресс игрока
    cursor.execute('''
        INSERT OR IGNORE INTO player_progress (player, level, kristals_collected)
        VALUES (?, ?, 0)
    ''', (player, level))

    cursor.execute('''
        UPDATE player_progress
        SET kristals_collected = kristals_collected + 1
        WHERE player = ? AND level = ?
    ''', (player, level))

    conn.commit()
    conn.close()

def save_kristal_collection(level, player):
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()

    # Добавляем запись о собранном кристалле
    cursor.execute('''
        INSERT INTO collected_kristals (level, player)
        VALUES (?, ?)
    ''', (level, player))

    # Обновляем прогресс игрока
    cursor.execute('''
        INSERT OR IGNORE INTO player_progress (player, level, kristals_collected)
        VALUES (?, ?, 0)
    ''', (player, level))

    cursor.execute('''
        UPDATE player_progress
        SET kristals_collected = kristals_collected + 1
        WHERE player = ? AND level = ?
    ''', (player, level))

    conn.commit()
    conn.close()

# Функция для получения прогресса игрока
def get_player_progress(player, level):
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT kristals_collected, completed
        FROM player_progress
        WHERE player = ? AND level = ?
    ''', (player, level))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'kristals_collected': result[0],
            'completed': bool(result[1])
        }
    return None



class FireDoor(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        super().__init__(all_sprites)
        self.add(fire_doors)
        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(self.image, COLORS['fire_door'], (0, 0, *size))
        pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 1)
        self.rect = pygame.Rect(*pos, *size)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 2)


class WaterDoor(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        super().__init__(all_sprites)
        self.add(water_doors)
        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(self.image, COLORS['water_door'], (0, 0, *size))
        pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 1)
        self.rect = pygame.Rect(*pos, *size)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 2)


class DynamicStone(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        super().__init__(all_sprites, platforms)
        self.add(dynamic_stones)
        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(self.image, COLORS['dynamic_stone'], (0, 0, *size))
        pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 1)
        self.rect = pygame.Rect(*pos, *size)
        self.speed = TILE_SIZE // 25
        self.is_pushed = False
        self.current_platform = None
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(self.image, (0, 0, 0), (0, 0, *size), 2)

    def move(self, direction, pusher_rect):
        if direction == 'right' and pusher_rect.right <= self.rect.left + 5:
            self.rect.x += self.speed
            self.is_pushed = True
            return True
        elif direction == 'left' and pusher_rect.left >= self.rect.right - 5:
            self.rect.x -= self.speed
            self.is_pushed = True
            return True
        self.is_pushed = False
        return False


class Fire(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        global fire
        super().__init__(all_sprites, players_group)

        # Загрузка изображений
        self.original_image = pygame.image.load(fire_kartinka).convert_alpha()
        self.image_levo = pygame.image.load(fire_kartinka_levo).convert_alpha()
        self.image_pravo = pygame.image.load(fire_kartinka_pravo).convert_alpha()

        self.size = size  # Размеры спрайта (ширина, высота)
        self.image, self.inner_image_size = self.create_sprite(self.original_image) # Изменено
        self.rect = self.image.get_rect(topleft=pos)

        self.speed = TILE_SIZE // 25
        self.jump_speed = -TILE_SIZE // 6
        self.gravity = TILE_SIZE // 50
        self.max_jump_height = self.rect.height * 2

        self.vertical_velocity = 0
        self.on_ground = False
        self.is_jumping = False
        self.alive = True
        self.at_door = False
        fire = self

        self.facing_direction = 0
        self.mask = pygame.mask.from_surface(self.image)

    def create_sprite(self, source_image):
        """Создает спрайт с персонажем внутри, уменьшенным по x на 5% с каждой стороны."""
        sprite_width, sprite_height = self.size
        image_width, image_height = source_image.get_size()

        # Уменьшаем ширину на 5% с каждой стороны
        padding_x = sprite_width * 0.05
        inner_width = sprite_width - 2 * padding_x

        # Определяем размеры для размещения изображения в центре
        scale = min(inner_width / image_width, sprite_height / image_height)
        new_image_width = int(image_width * scale)
        new_image_height = int(image_height * scale)

        # Масштабируем изображение
        scaled_image = pygame.transform.scale(source_image, (new_image_width, new_image_height))

        # Создаем поверхность спрайта
        sprite = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
        sprite.blit(scaled_image, (int(padding_x + (inner_width - new_image_width) // 2), (sprite_height - new_image_height) // 2))

        return sprite, (new_image_width, new_image_height) # Возвращаем размеры изображения

    def update(self):
        if not self.alive:
            return

        self.at_door = pygame.sprite.spritecollideany(self, fire_doors)

        keys = pygame.key.get_pressed()
        moved = False

        # Движение вправо
        if keys[pygame.K_RIGHT]:
            self.facing_direction = 0
            self.image, self.inner_image_size = self.create_sprite(self.image_pravo)  # меняем спрайт и получаем размеры
            for stone in pygame.sprite.spritecollide(self, dynamic_stones, False):
                stone.move('right', self.rect)
            if not pygame.sprite.spritecollideany(self, v_borders):
                self.rect.x += self.speed
                moved = True

        # Движение влево
        if keys[pygame.K_LEFT] and not moved:
            self.facing_direction = 1
            self.image, self.inner_image_size = self.create_sprite(self.image_levo)  # меняем спрайт и получаем размеры
            for stone in pygame.sprite.spritecollide(self, dynamic_stones, False):
                stone.move('left', self.rect)
            if not pygame.sprite.spritecollideany(self, v_borders):
                self.rect.x -= self.speed
                moved = True

        if not (keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]):
            self.image, self.inner_image_size = self.create_sprite(self.original_image)  # Возвращаем стандартный спрайт и получаем размеры

        # Прыжок
        if keys[pygame.K_UP] and self.on_ground and not self.is_jumping:
            self.vertical_velocity = self.jump_speed
            self.on_ground = False
            self.is_jumping = True

        # Гравитация
        self.vertical_velocity += self.gravity

        # Ограничение скорости падения
        if self.vertical_velocity > TILE_SIZE // 10:
            self.vertical_velocity = TILE_SIZE // 10

        # Обновление вертикальной позиции
        self.rect.y += self.vertical_velocity

        # Проверка столкновений с платформами
        self.on_ground = False

        collided_platforms = pygame.sprite.spritecollide(self, platforms, False)

        for platform in collided_platforms:
            if self.rect.bottom >= platform.rect.top and self.rect.bottom <= platform.rect.bottom and self.vertical_velocity >= 0:
                self.rect.bottom = platform.rect.top
                self.vertical_velocity = 0
                self.on_ground = True
                self.is_jumping = False
                break
            elif self.vertical_velocity < 0 and self.rect.top <= platform.rect.bottom and self.rect.top >= platform.rect.top:
                self.vertical_velocity = 0
                self.rect.top = platform.rect.bottom
                break

        # Ограничение высоты прыжка
        if self.is_jumping and self.rect.y < self.rect.bottom - self.max_jump_height - self.rect.height:
            self.is_jumping = False
            self.vertical_velocity = 0
            self.rect.y = self.rect.bottom - self.max_jump_height - self.rect.height

    def draw(self, surface):
        """Рисует спрайт на поверхности."""
        surface.blit(self.image, self.rect)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)


class Water(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        global water
        super().__init__(all_sprites, players_group)

        # Загрузка изображений
        self.original_image = pygame.image.load(water_kartinka).convert_alpha()
        self.image_levo = pygame.image.load(water_kartinka_levo).convert_alpha()
        self.image_pravo = pygame.image.load(water_kartinka_pravo).convert_alpha()

        self.size = size  # Размеры спрайта (ширина, высота)
        self.image, self.inner_image_size = self.create_sprite(self.original_image) # Изменено
        self.rect = self.image.get_rect(topleft=pos)

        self.speed = TILE_SIZE // 25
        self.jump_speed = -TILE_SIZE // 6
        self.gravity = TILE_SIZE // 50
        self.max_jump_height = self.rect.height * 2

        self.vertical_velocity = 0
        self.on_ground = False
        self.is_jumping = False
        self.alive = True
        self.at_door = False
        water = self

        self.facing_direction = 0
        self.mask = pygame.mask.from_surface(self.image)

    def create_sprite(self, source_image):
        """Создает спрайт с персонажем внутри, уменьшенным по x на 5% с каждой стороны."""
        sprite_width, sprite_height = self.size
        image_width, image_height = source_image.get_size()

        # Уменьшаем ширину на 5% с каждой стороны
        padding_x = sprite_width * 0.05
        inner_width = sprite_width - 2 * padding_x

        # Определяем размеры для размещения изображения в центре
        scale = min(inner_width / image_width, sprite_height / image_height)
        new_image_width = int(image_width * scale)
        new_image_height = int(image_height * scale)

        # Масштабируем изображение
        scaled_image = pygame.transform.scale(source_image, (new_image_width, new_image_height))

        # Создаем поверхность спрайта
        sprite = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
        sprite.blit(scaled_image, (int(padding_x + (inner_width - new_image_width) // 2), (sprite_height - new_image_height) // 2))

        return sprite, (new_image_width, new_image_height) # Возвращаем размеры изображения

    def update(self):
        if not self.alive:
            return

        self.at_door = pygame.sprite.spritecollideany(self, water_doors)

        keys = pygame.key.get_pressed()
        moved = False

        # Движение вправо
        if keys[pygame.K_d]:
            self.facing_direction = 0
            self.image, self.inner_image_size = self.create_sprite(self.image_pravo)  # меняем спрайт и получаем размеры
            for stone in pygame.sprite.spritecollide(self, dynamic_stones, False):
                stone.move('right', self.rect)
            if not pygame.sprite.spritecollideany(self, v_borders):
                self.rect.x += self.speed
                moved = True

        # Движение влево
        if keys[pygame.K_a] and not moved:
            self.facing_direction = 1
            self.image, self.inner_image_size = self.create_sprite(self.image_levo)  # меняем спрайт и получаем размеры
            for stone in pygame.sprite.spritecollide(self, dynamic_stones, False):
                stone.move('left', self.rect)
            if not pygame.sprite.spritecollideany(self, v_borders):
                self.rect.x -= self.speed
                moved = True

        if not (keys[pygame.K_a] or keys[pygame.K_d]):
            self.image, self.inner_image_size = self.create_sprite(self.original_image)  # Возвращаем стандартный спрайт и получаем размеры

        # Прыжок
        if keys[pygame.K_w] and self.on_ground and not self.is_jumping:
            self.vertical_velocity = self.jump_speed
            self.on_ground = False
            self.is_jumping = True

        # Гравитация
        self.vertical_velocity += self.gravity

        # Ограничение скорости падения
        if self.vertical_velocity > TILE_SIZE // 10:
            self.vertical_velocity = TILE_SIZE // 10

        # Обновление вертикальной позиции
        self.rect.y += self.vertical_velocity

        # Проверка столкновений с платформами
        self.on_ground = False

        collided_platforms = pygame.sprite.spritecollide(self, platforms, False)

        for platform in collided_platforms:
            if self.rect.bottom >= platform.rect.top and self.rect.bottom <= platform.rect.bottom and self.vertical_velocity >= 0:
                self.rect.bottom = platform.rect.top
                self.vertical_velocity = 0
                self.on_ground = True
                self.is_jumping = False
                break
            elif self.vertical_velocity < 0 and self.rect.top <= platform.rect.bottom and self.rect.top >= platform.rect.top:
                self.vertical_velocity = 0
                self.rect.top = platform.rect.bottom
                break

        # Ограничение высоты прыжка
        if self.is_jumping and self.rect.y < self.rect.bottom - self.max_jump_height - self.rect.height:
            self.is_jumping = False
            self.vertical_velocity = 0
            self.rect.y = self.rect.bottom - self.max_jump_height - self.rect.height

    def draw(self, surface):
        """Рисует спрайт на поверхности."""
        surface.blit(self.image, self.rect)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)


class FireLake(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        super().__init__(all_sprites, platforms, fire_lakes)
        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(self.image, COLORS['fire_lake'], (0, 0, *size))
        self.rect = self.image.get_rect(topleft=pos)

        self.danger_zone_rect = self.rect.copy()
        self.danger_zone_rect.inflate_ip(DANGER_ZONE_INFLATE, DANGER_ZONE_INFLATE)

        Border(pos[0], pos[1], pos[0] + size[0], pos[1], TYPE_BORD['up'])
        Border(pos[0], pos[1] + size[1], pos[0] + size[0], pos[1] + size[1], TYPE_BORD['bottom'])
        Border(pos[0], pos[1], pos[0], pos[1] + size[1], TYPE_BORD['left'])
        Border(pos[0] + size[0], pos[1], pos[0] + size[0], pos[1] + size[1], TYPE_BORD['right'])

    def update(self):
        pass

    def draw(self, surface):
        """Отрисовывает озеро."""
        surface.blit(self.image, self.rect)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
            pygame.draw.rect(surface, (255, 0, 0), self.danger_zone_rect, 1)


class WaterLake(pygame.sprite.Sprite):
    def __init__(self, pos, size):
        super().__init__(all_sprites, platforms, water_lakes)
        self.image = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(self.image, COLORS['water_lake'], (0, 0, *size))
        self.rect = self.image.get_rect(topleft=pos)

        self.danger_zone_rect = self.rect.copy()
        self.danger_zone_rect.inflate_ip(DANGER_ZONE_INFLATE, DANGER_ZONE_INFLATE)

        Border(pos[0], pos[1], pos[0] + size[0], pos[1], TYPE_BORD['up'])
        Border(pos[0], pos[1] + size[1], pos[0] + size[0], pos[1] + size[1], TYPE_BORD['bottom'])
        Border(pos[0], pos[1], pos[0], pos[1] + size[1], TYPE_BORD['left'])
        Border(pos[0] + size[0], pos[1], pos[0] + size[0], pos[1] + size[1], TYPE_BORD['right'])

    def update(self):
        pass

    def draw(self, surface):
        """Отрисовывает озеро."""
        surface.blit(self.image, self.rect)
        if DEBUG_DRAW_RECTS:
            pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
            pygame.draw.rect(surface, (255, 0, 0), self.danger_zone_rect, 1)

def load_level(filename):
    global TILE_SIZE, SIZES, all_sprites, walls, v_borders, g_borders, static_stones, dynamic_stones, fire_doors, water_doors, players_group, platforms, fire_lakes, water_lakes, kristals
    # Очистка всех групп
    kristals.empty()
    all_sprites.empty()
    walls.empty()
    v_borders.empty()
    g_borders.empty()
    static_stones.empty()
    dynamic_stones.empty()
    fire_doors.empty()
    water_doors.empty()
    players_group.empty()
    platforms.empty()
    fire_lakes.empty()
    water_lakes.empty()

    global fire, water  # Используем глобальные переменные
    fire = None
    water = None

    with open(f'{MAP_DIR}/{filename}') as f:
        level = [list(line.strip()) for line in f]

    height = len(level)
    width = max(len(line) for line in level)
    TILE_SIZE = min(WINDOW_HEIGHT // (height + 2), WINDOW_WIDTH // (width + 2))

    SIZES = {k: (TILE_SIZE, TILE_SIZE) for k in SIZES}
    SIZES.update({
        'fire': (TILE_SIZE, TILE_SIZE),
        'water': (TILE_SIZE, TILE_SIZE),
        'fire_door': (TILE_SIZE, TILE_SIZE * 2),
        'water_door': (TILE_SIZE, TILE_SIZE * 2),
        'dynamic_stone': (TILE_SIZE // 2, TILE_SIZE // 2),
        'fire_lake': (TILE_SIZE, TILE_SIZE // 4),
        'water_lake': (TILE_SIZE, TILE_SIZE // 4)
    })

    SIZES.update({
        'kristal': (TILE_SIZE // 3, TILE_SIZE // 3)  # Размер кристалла
    })

    for y, row in enumerate(level):
        for x, char in enumerate(row):
            pos = (x * TILE_SIZE, y * TILE_SIZE)

            # Добавляем обработку кристалла
            if char == SIGNS['kristal']:
                kristal_pos = (
                    pos[0] + (TILE_SIZE - SIZES['kristal'][0]) // 2,
                    pos[1] + (TILE_SIZE - SIZES['kristal'][1]) // 2
                )
                Kristal(kristal_pos, SIZES['kristal'], filename)  # Передаем уровень

    for y, row in enumerate(level):
        for x, char in enumerate(row):
            pos = (x * TILE_SIZE, y * TILE_SIZE)

            if char == SIGNS['fire']:
                fire_sprite = Fire(pos, SIZES['fire'])
                all_sprites.add(fire_sprite)
            elif char == SIGNS['water']:
                water_sprite = Water(pos, SIZES['water'])
                all_sprites.add(water_sprite)
            elif char == SIGNS['fire_door']:
                FireDoor(pos, SIZES['fire_door'])
            elif char == SIGNS['water_door']:
                WaterDoor(pos, SIZES['water_door'])
            elif char == SIGNS['fire_lake']:
                FireLake(pos, SIZES['fire_lake'])
            elif char == SIGNS['water_lake']:
                WaterLake(pos, SIZES['water_lake'])
            elif char == SIGNS['wall']:
                Wall(pos, (TILE_SIZE, TILE_SIZE // 4))
            elif char == SIGNS['dynamic_stone']:
                stone = DynamicStone(
                    (pos[0] + (TILE_SIZE - SIZES['dynamic_stone'][0]) // 2,
                     pos[1] + (TILE_SIZE - SIZES['dynamic_stone'][1]) // 2),
                    SIZES['dynamic_stone']
                )

def draw_menu(screen, font, play_button_rect, levels_button_rect):
    """Рисует экран меню."""
    screen.fill((0, 0, 0))  # Черный фон
    text = font.render("Свет и Тьма", True, (255, 255, 255))
    text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
    screen.blit(text, text_rect)

    # Рисуем кнопку "Играть"
    pygame.draw.rect(screen, (50, 200, 50), play_button_rect)  # Зеленая кнопка
    play_text = font.render("Играть", True, (255, 255, 255))
    play_text_rect = play_text.get_rect(center=play_button_rect.center)
    screen.blit(play_text, play_text_rect)

    # Рисуем кнопку "Уровни"
    pygame.draw.rect(screen, (200, 100, 50), levels_button_rect)  # Оранжевая кнопка
    levels_text = font.render("Уровни", True, (255, 255, 255))
    levels_text_rect = levels_text.get_rect(center=levels_button_rect.center)
    screen.blit(levels_text, levels_text_rect)

def draw_end_screen(screen, font, win):
    """Рисует экран завершения игры."""
    screen.fill((50, 50, 50))  # Серый фон
    if win:
        text = font.render("Победа!", True, (0, 255, 0))
    else:
        text = font.render("Проигрыш!", True, (255, 0, 0))

    text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
    screen.blit(text, text_rect)

    # Кнопка "Меню"
    menu_button_width = 150
    menu_button_height = 40
    menu_button_x = WINDOW_WIDTH // 2 - menu_button_width - 20
    menu_button_y = WINDOW_HEIGHT // 2
    menu_button_rect = pygame.Rect(menu_button_x, menu_button_y, menu_button_width, menu_button_height)
    pygame.draw.rect(screen, (100, 100, 200), menu_button_rect)
    menu_text = font.render("Меню", True, (255, 255, 255))
    menu_text_rect = menu_text.get_rect(center=menu_button_rect.center)
    screen.blit(menu_text, menu_text_rect)

    # Кнопка "R"
    r_button_width = 50
    r_button_height = 40
    r_button_x = WINDOW_WIDTH // 2 + 20
    r_button_y = WINDOW_HEIGHT // 2
    r_button_rect = pygame.Rect(r_button_x, r_button_y, r_button_width, r_button_height)
    pygame.draw.rect(screen, (200, 100, 100), r_button_rect)
    r_text = font.render("R", True, (255, 255, 255))
    r_text_rect = r_text.get_rect(center=r_button_rect.center)
    screen.blit(r_text, r_text_rect)

    return menu_button_rect, r_button_rect

def draw_levels_screen(screen, font, level_buttons, back_button_rect):
    """Рисует экран выбора уровней."""
    screen.fill((0, 0, 0))  # Черный фон
    title_text = font.render("Выбор уровня", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4))
    screen.blit(title_text, title_rect)

    # Рисуем кнопки уровней
    for i, (level, button_rect) in enumerate(level_buttons.items()):
        pygame.draw.rect(screen, (50, 150, 200), button_rect)  # Синие кнопки
        level_text = font.render(f"Уровень {level}", True, (255, 255, 255))
        level_text_rect = level_text.get_rect(center=button_rect.center)
        screen.blit(level_text, level_text_rect)

    # Рисуем кнопку "Назад"
    pygame.draw.rect(screen, (200, 50, 50), back_button_rect)  # Красная кнопка
    back_text = font.render("Назад", True, (255, 255, 255))
    back_text_rect = back_text.get_rect(center=back_button_rect.center)
    screen.blit(back_text, back_text_rect)

# ... (предыдущий код без изменений)

pygame.init()
init_db()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT + BUTTON_PLACE))
pygame.display.set_caption("Свет и Тьма")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 74)
small_font = pygame.font.Font(None, 36)

# Определяем прямоугольники для кнопок "Играть" и "Уровни"
button_width = 200
button_height = 50
button_x = WINDOW_WIDTH // 2 - button_width - 10  # Смещаем кнопку "Играть" влево
button_y = WINDOW_HEIGHT // 2 - button_height // 2
play_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

levels_button_x = WINDOW_WIDTH // 2 + 10  # Смещаем кнопку "Уровни" вправо
levels_button_y = WINDOW_HEIGHT // 2 - button_height // 2
levels_button_rect = pygame.Rect(levels_button_x, levels_button_y, button_width, button_height)

# Состояния игры
MENU = 0
GAME = 1
END_SCREEN = 2
LEVELS_SCREEN = 3  # Новое состояние для экрана выбора уровней
game_state = MENU

game_over = False
level_complete = False
running = True
death_time = None
end_screen_buttons = None

# Определяем прямоугольники для кнопок уровней
level_buttons = {
    1: pygame.Rect(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 - 100, 200, 50),  # Уровень 1
    2: pygame.Rect(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2, 200, 50),        # Уровень 2
    3: pygame.Rect(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 + 100, 200, 50),  # Уровень 3
}

# Кнопка "Назад"
back_button_rect = pygame.Rect(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT - 100, 200, 50)

# Основной цикл
while running:
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == MENU:
                if play_button_rect.collidepoint(event.pos):
                    game_state = GAME
                    load_level('1.txt')
                    game_over = False
                    level_complete = False
                    if fire:
                        fire.alive = True
                    if water:
                        water.alive = True
                elif levels_button_rect.collidepoint(event.pos):
                    game_state = LEVELS_SCREEN
            elif game_state == END_SCREEN:
                if end_screen_buttons:
                    menu_button_rect, r_button_rect = end_screen_buttons
                    if menu_button_rect.collidepoint(event.pos):
                        game_state = MENU
                        game_over = False
                        level_complete = False
                    elif r_button_rect.collidepoint(event.pos):
                        game_state = GAME
                        load_level('1.txt')
                        game_over = False
                        level_complete = False
                        if fire:
                            fire.alive = True
                        if water:
                            water.alive = True
            elif game_state == LEVELS_SCREEN:
                # Обработка кликов на экране выбора уровней
                for level, button_rect in level_buttons.items():
                    if button_rect.collidepoint(event.pos):
                        game_state = GAME
                        load_level(f'{level}.txt')  # Загружаем выбранный уровень
                        game_over = False
                        level_complete = False
                        if fire:
                            fire.alive = True
                        if water:
                            water.alive = True
                if back_button_rect.collidepoint(event.pos):
                    game_state = MENU  # Возврат в главное меню

    screen.fill((0, 0, 0))  # Очистка экрана

    if game_state == MENU:
        draw_menu(screen, font, play_button_rect, levels_button_rect)
    elif game_state == GAME:
        if not game_over and not level_complete:
            all_sprites.update()

            if fire.at_door and water.at_door:
                level_complete = True
                game_state = END_SCREEN

            for lake in fire_lakes:
                if water.alive and lake.danger_zone_rect.colliderect(water.rect):
                    water.alive = False
            for lake in water_lakes:
                if fire.alive and lake.danger_zone_rect.colliderect(fire.rect):
                    fire.alive = False

            if (not fire.alive or not water.alive) and not level_complete:
                if death_time is None:
                    death_time = current_time
                elif current_time - death_time >= 2000:
                    game_over = True
                    game_state = END_SCREEN

        screen.fill((150, 150, 150))
        for sprite in all_sprites:
            if hasattr(sprite, 'draw'):
                sprite.draw(screen)
            else:
                screen.blit(sprite.image, sprite.rect)
            if DEBUG_DRAW_RECTS:
                pygame.draw.rect(screen, (0, 0, 0), sprite.rect, 2)

        controls = small_font.render('Fire: ←↑→  Water: AWD', True, (255, 255, 255))
        screen.blit(controls, (10, WINDOW_HEIGHT + 10))
    elif game_state == END_SCREEN:
        win = level_complete
        end_screen_buttons = draw_end_screen(screen, font, win)
    elif game_state == LEVELS_SCREEN:
        draw_levels_screen(screen, font, level_buttons, back_button_rect)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
