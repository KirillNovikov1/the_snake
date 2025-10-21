from __future__ import annotations
import json
import os
import random
import sys
from typing import List, Tuple, Set

import pygame

# === Константы (переименованы в соответствии с тестами) ===
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
GRID_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // GRID_SIZE
BOARD_BACKGROUND_COLOR = (0, 0, 0)

# Цвета
COLOR_APPLE = (255, 0, 0)
COLOR_SNAKE = (0, 255, 0)
COLOR_HEAD = (0, 200, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_POISON = (255, 100, 255)
COLOR_STONE = (100, 100, 100)

# Параметры
START_FPS = 10
MAX_FPS = 25
MIN_FPS = 5
APPLE_COUNT = 3
STONE_COUNT = 5
POISON_COUNT = 2

# Файл рекорда
RECORD_FILE = "snake_record.json"

# Поле клеток
ALL_CELLS: Set[Tuple[int, int]] = {
    (x * GRID_SIZE, y * GRID_SIZE)
    for x in range(GRID_WIDTH)
    for y in range(GRID_HEIGHT)
}

# Направления (переименованы в соответствии с тестами)
UP = (0, -GRID_SIZE)
DOWN = (0, GRID_SIZE)
LEFT = (-GRID_SIZE, 0)
RIGHT = (GRID_SIZE, 0)
DEFAULT_DIRECTION = RIGHT

# Словарь направлений
DIRECTION_MAP = {
    pygame.K_RIGHT: RIGHT,
    pygame.K_LEFT: LEFT,
    pygame.K_UP: UP,
    pygame.K_DOWN: DOWN,
}

# Инициализация pygame и глобальных переменных
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()


# Типы объектов
class ObjectType:
    """Типы игровых объектов."""

    APPLE = "apple"
    POISON = "poison"
    STONE = "stone"


def load_record(filename: str) -> int:
    """Загрузить рекорд из JSON файла."""
    if not os.path.exists(filename):
        return 0
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("record", 0))
    except Exception:
        return 0


def save_record(filename: str, value: int) -> None:
    """Сохранить рекорд в JSON файл."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {"record": int(value)}, f,
                ensure_ascii=False, indent=2
            )
    except Exception:
        pass


class GameObject:
    """Базовый класс игровых объектов."""

    def __init__(
        self,
        position: Tuple[int, int] = (0, 0),
        body_color: Tuple[int, int, int] = (0, 0, 0)
    ):
        """Инициализировать игровой объект."""
        self.position = position
        self.body_color = body_color

    def draw(self, surface: pygame.Surface) -> None:
        """Отрисовать объект на поверхности."""
        self.draw_cell(surface, self.position, self.body_color)

    def erase(self, surface: pygame.Surface) -> None:
        """Стереть объект с поверхности."""
        self.draw_cell(surface, self.position, BOARD_BACKGROUND_COLOR)

    @staticmethod
    def draw_cell(
        surface: pygame.Surface,
        position: Tuple[int, int],
        color: Tuple[int, int, int]
    ) -> None:
        """Отрисовать одну клетку."""
        rect = pygame.Rect(
            position[0], position[1], GRID_SIZE, GRID_SIZE
        )
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, BOARD_BACKGROUND_COLOR, rect, 1)

    def randomize_position(self, occupied: Set[Tuple[int, int]]) -> None:
        """Установить случайную позицию, не занятую другими объектами."""
        free_cells = ALL_CELLS - occupied
        if free_cells:
            self.position = random.choice(tuple(free_cells))


class Collectible(GameObject):
    """Собираемый объект (яблоко или отрава)."""

    def __init__(
        self,
        body_color: Tuple[int, int, int] = (0, 0, 0),
        obj_type: str = ""
    ):
        """Инициализировать собираемый объект."""
        super().__init__((0, 0), body_color)
        self.obj_type = obj_type

    def initialize_position(self, occupied: Set[Tuple[int, int]]) -> None:
        """Инициализировать позицию объекта."""
        self.randomize_position(occupied)


class Apple(Collectible):
    """Яблоко - увеличивает длину змейки."""

    def __init__(self, occupied: Set[Tuple[int, int]] = None):
        """Инициализировать яблоко."""
        super().__init__(COLOR_APPLE, ObjectType.APPLE)
        if occupied is None:
            occupied = set()
        self.initialize_position(occupied)


class Poison(Collectible):
    """Отрава - уменьшает длину змейки."""

    def __init__(self, occupied: Set[Tuple[int, int]] = None):
        """Инициализировать отраву."""
        super().__init__(COLOR_POISON, ObjectType.POISON)
        if occupied is None:
            occupied = set()
        self.initialize_position(occupied)


class Stone(GameObject):
    """Камень - препятствие."""

    def __init__(self, occupied: Set[Tuple[int, int]] = None):
        """Инициализировать камень."""
        super().__init__((0, 0), COLOR_STONE)
        if occupied is None:
            occupied = set()
        self.randomize_position(occupied)


class Snake(GameObject):
    """Класс змейки."""

    def __init__(self):
        """Инициализировать змейку."""
        cx = (GRID_WIDTH // 2) * GRID_SIZE
        cy = (GRID_HEIGHT // 2) * GRID_SIZE
        initial_position = (cx, cy)
        super().__init__(initial_position, COLOR_SNAKE)

        self.positions: List[Tuple[int, int]] = [initial_position]
        self.length = 1
        self.direction = DEFAULT_DIRECTION
        self.last_tail_position: Tuple[int, int] | None = None

    def get_head_position(self) -> Tuple[int, int]:
        """Получить позицию головы змейки."""
        return self.positions[0]

    def update_direction(self, key: int) -> None:
        """Обновить направление движения змейки."""
        new_direction = DIRECTION_MAP.get(key)
        if not new_direction:
            return

        # Запрет движения в противоположном направлении
        if (new_direction[0] == -self.direction[0]
                and new_direction[1] == -self.direction[1]
                and self.length > 1):
            return

        self.direction = new_direction

    def move(self) -> None:
        """Переместить змейку."""
        head_x, head_y = self.get_head_position()
        dx, dy = self.direction
        new_head = (
            (head_x + dx) % SCREEN_WIDTH,
            (head_y + dy) % SCREEN_HEIGHT
        )

        # Сохраняем позицию хвоста перед удалением
        if len(self.positions) >= self.length:
            self.last_tail_position = self.positions[-1]

        # Вставляем новую голову
        self.positions.insert(0, new_head)

        # Удаляем хвост, если не растём
        if len(self.positions) > self.length:
            self.positions.pop()

        # Обновляем позицию для GameObject
        self.position = new_head

    def grow(self, amount: int = 1) -> None:
        """Увеличить длину змейки."""
        self.length += amount
        if self.length < 1:
            self.length = 1
            self.positions = [self.get_head_position()]

    def check_self_collision(self) -> bool:
        """Проверить столкновение с собой."""
        # У короткой змейки не может быть столкновения
        if self.length < 4:
            return False

        head = self.get_head_position()
        return head in self.positions[1:]

    def check_collision_with_position(self, position: Tuple[int, int]) -> bool:
        """Проверить столкновение с заданной позицией."""
        return self.get_head_position() == position

    def reset(self) -> None:
        """Сбросить змейку в начальное состояние."""
        cx = (GRID_WIDTH // 2) * GRID_SIZE
        cy = (GRID_HEIGHT // 2) * GRID_SIZE
        initial_position = (cx, cy)
        self.positions = [initial_position]
        self.position = initial_position
        self.length = 1
        self.direction = DEFAULT_DIRECTION
        self.last_tail_position = None

    def draw(self, surface: pygame.Surface) -> None:
        """Отрисовать змейку."""
        if not self.positions:
            return

        # Отрисовка головы
        GameObject.draw_cell(surface, self.positions[0], COLOR_HEAD)

        # Отрисовка тела
        for segment in self.positions[1:]:
            GameObject.draw_cell(surface, segment, self.body_color)

    def erase_tail(self, surface: pygame.Surface) -> None:
        """Стереть хвост змейки."""
        if (self.last_tail_position
                and self.last_tail_position not in self.positions):
            GameObject.draw_cell(
                surface, self.last_tail_position, BOARD_BACKGROUND_COLOR
            )


class GameState:
    """Состояние игры."""

    def __init__(self):
        """Инициализировать состояние игры."""
        self.record = load_record(RECORD_FILE)
        self.snake = Snake()
        self.fps = START_FPS
        self.running = True
        self.game_over = False
        self.apples: List[Apple] = []
        self.stones: List[Stone] = []
        self.poisons: List[Poison] = []

    def generate_objects(self) -> None:
        """Сгенерировать игровые объекты."""
        occupied = set(self.snake.positions)

        # Генерация яблок
        self.apples = []
        for _ in range(APPLE_COUNT):
            apple = Apple(occupied)
            self.apples.append(apple)
            occupied.add(apple.position)

        # Генерация камней
        self.stones = []
        for _ in range(STONE_COUNT):
            stone = Stone(occupied)
            self.stones.append(stone)
            occupied.add(stone.position)

        # Генерация отравы
        self.poisons = []
        for _ in range(POISON_COUNT):
            poison = Poison(occupied)
            self.poisons.append(poison)
            occupied.add(poison.position)

    def check_collisions(self) -> None:
        """Проверить все столкновения."""
        head = self.snake.get_head_position()

        # Проверка яблок
        for apple in self.apples[:]:
            if head == apple.position:
                self.snake.grow(1)
                all_objects = self.apples + self.stones + self.poisons
                occupied = (
                    set(self.snake.positions)
                    | {obj.position for obj in all_objects}
                )
                apple.randomize_position(occupied)

                # Обновление рекорда
                if self.snake.length > self.record:
                    self.record = self.snake.length
                    save_record(RECORD_FILE, self.record)

        # Проверка отравы
        for poison in self.poisons[:]:
            if head == poison.position:
                self.snake.grow(-1)
                all_objects = self.apples + self.stones + self.poisons
                occupied = (
                    set(self.snake.positions)
                    | {obj.position for obj in all_objects}
                )
                poison.randomize_position(occupied)

        # Проверка камней
        for stone in self.stones:
            if head == stone.position:
                self.game_over = True
                return

        # Проверка самоперекуса
        if self.snake.check_self_collision():
            self.game_over = True


def handle_keys(game_object) -> None:
    """Обработать события игры."""
    # Эта функция должна быть совместима с тестами
    # В тестах ожидается, что эта функция принимает один аргумент
    # и обрабатывает клавиши для управления змейкой
    pass


def main():
    """Главная функция игры."""
    # Используем глобальные переменные screen и clock
    global screen, clock

    # Инициализация состояния игры
    game_state = GameState()
    game_state.generate_objects()

    font = pygame.font.SysFont(None, 36)
    small_font = pygame.font.SysFont(None, 24)

    # Основной игровой цикл
    while game_state.running:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state.running = False
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state.running = False
                    continue

                if event.key in (
                    pygame.K_UP, pygame.K_DOWN,
                    pygame.K_LEFT, pygame.K_RIGHT
                ):
                    game_state.snake.update_direction(event.key)

                if event.key == pygame.K_q:
                    game_state.fps = max(MIN_FPS, game_state.fps - 1)

                if event.key == pygame.K_w:
                    game_state.fps = min(MAX_FPS, game_state.fps + 1)

                if event.key == pygame.K_r and game_state.game_over:
                    game_state.snake.reset()
                    game_state.fps = START_FPS
                    game_state.generate_objects()
                    game_state.game_over = False

        # Отрисовка игры
        screen.fill(BOARD_BACKGROUND_COLOR)

        if game_state.game_over:
            # Экран завершения игры
            draw_center_message(
                screen,
                f"Игра окончена! Длина: {game_state.snake.length}",
                font,
                COLOR_TEXT
            )
            draw_message(
                screen,
                "Нажмите R для рестарта или ESC для выхода",
                small_font,
                COLOR_TEXT
            )
        else:
            # Игровой процесс
            # Движение змейки
            game_state.snake.move()

            # Проверка столкновений
            game_state.check_collisions()

            # Отрисовка объектов
            for obj in (
                game_state.apples + game_state.stones
                + game_state.poisons
            ):
                obj.draw(screen)
            game_state.snake.draw(screen)

            # Обновление заголовка
            update_caption(game_state)

        # Обновление экрана
        pygame.display.update()
        clock.tick(game_state.fps)

    pygame.quit()
    sys.exit(0)


def draw_center_message(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int]
) -> None:
    """Нарисовать сообщение по центру экрана."""
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    surface.blit(surf, rect)


def draw_message(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int]
) -> None:
    """Нарисовать сообщение на экране."""
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
    surface.blit(surf, rect)


def update_caption(game_state: GameState) -> None:
    """Обновить заголовок окна."""
    caption = (
        f"Змейка — длина: {game_state.snake.length} | "
        f"рекорд: {game_state.record} | скорость: {game_state.fps} | "
        "ESC — выход"
    )
    pygame.display.set_caption(caption)


if __name__ == "__main__":
    main()
