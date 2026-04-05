"""
mazegen - A reusable maze generation module.

Usage example::

    from mazegen import MazeGenerator

    gen = MazeGenerator(width=20, height=15, seed=42)
    gen.generate(perfect=True)

    maze = gen.maze          # dict[(x,y)] -> int (bitmask: N=1,E=2,S=4,W=8)
    path = gen.solution      # list of (x,y) tuples from entry to exit
    entry = gen.entry        # (x, y)
    exit_ = gen.exit         # (x, y)
    pattern = gen.pattern42  # set of (x,y) cells that form the '42'
"""

import random
from collections import deque
from typing import Optional


# Wall bitmasks
NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8

OPPOSITE = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}
DELTA = {
    NORTH: (0, -1),
    SOUTH: (0, 1),
    EAST: (1, 0),
    WEST: (-1, 0),
}

# 3×5 pixel fonts for digits '4' and '2'
_DIGIT_4 = [
    [1, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1],
]
_DIGIT_2 = [
    [1, 1, 1],
    [0, 0, 1],
    [1, 1, 1],
    [1, 0, 0],
    [1, 1, 1],
]


class MazeGenerator:
    """Generates a 2-D maze using iterative DFS (recursive backtracker).

    Each cell is stored as a bitmask where a bit set to 1 means the wall
    in that direction is *closed* (present):

    - Bit 0 (value 1): North
    - Bit 1 (value 2): East
    - Bit 2 (value 4): South
    - Bit 3 (value 8): West

    Args:
        width:  Number of cells horizontally. Must be >= 3.
        height: Number of cells vertically.   Must be >= 3.
        seed:   Optional RNG seed for reproducibility.
        entry:  (x, y) of the entrance cell. Defaults to (0, 0).
        exit_:  (x, y) of the exit cell. Defaults to (width-1, height-1).
    """

    def __init__(
        self,
        width: int = 20,
        height: int = 15,
        seed: Optional[int] = None,
        entry: tuple[int, int] = (0, 0),
        exit_: Optional[tuple[int, int]] = None,
    ) -> None:
        """Initialise the generator without running generation yet."""
        if width < 3 or height < 3:
            raise ValueError("width and height must be >= 3")
        self.width = width
        self.height = height
        self.seed = seed
        self.entry: tuple[int, int] = entry
        self.exit: tuple[int, int] = (
            exit_ if exit_ is not None else (width - 1, height - 1)
        )
        if not self._in_bounds(*self.entry):
            raise ValueError(f"entry {self.entry} is out of bounds")
        if not self._in_bounds(*self.exit):
            raise ValueError(f"exit {self.exit} is out of bounds")
        if self.entry == self.exit:
            raise ValueError("entry and exit must be different cells")

        self.maze: dict[tuple[int, int], int] = {}
        self.solution: list[tuple[int, int]] = []
        self.pattern42: set[tuple[int, int]] = set()
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, perfect: bool = True) -> None:
        """Generate the maze.

        The '42' pattern is stored in ``self.pattern42`` as a set of cell
        coordinates. These cells are visually distinct but remain part of
        the navigable maze so connectivity is preserved.

        Args:
            perfect: If True produce a perfect maze (unique path between any
                     two cells). If False add ~5 % extra passages for loops.
        """
        self._init_grid()
        self._carve_passages_dfs()
        if not perfect:
            self._add_loops()
        self._enforce_outer_walls()
        self.solution = self._bfs_solution()
        self.pattern42 = self._compute_42_cells()

    def solution_as_directions(self) -> str:
        """Return the solution as a string of N/E/S/W characters."""
        if len(self.solution) < 2:
            return ""
        dirs: list[str] = []
        for (x1, y1), (x2, y2) in zip(self.solution, self.solution[1:]):
            dx, dy = x2 - x1, y2 - y1
            if dx == 1:
                dirs.append("E")
            elif dx == -1:
                dirs.append("W")
            elif dy == -1:
                dirs.append("N")
            else:
                dirs.append("S")
        return "".join(dirs)

    def to_hex_grid(self) -> list[str]:
        """Return the maze as a list of hex strings, one per row.

        Each character is one hex digit: N=bit0, E=bit1, S=bit2, W=bit3.
        A set bit means the wall is closed (present).
        """
        rows: list[str] = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                row += format(self.maze[(x, y)], "X")
            rows.append(row)
        return rows

    def has_42_pattern(self) -> bool:
        """Return True if the maze is large enough to show the '42' pattern."""
        return self.width >= 11 and self.height >= 9

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _init_grid(self) -> None:
        """Fill every cell with all 4 walls closed."""
        self.maze = {
            (x, y): NORTH | EAST | SOUTH | WEST
            for y in range(self.height)
            for x in range(self.width)
        }

    def _remove_wall(self, x: int, y: int, direction: int) -> None:
        """Remove the wall between (x,y) and its neighbour in direction."""
        nx, ny = x + DELTA[direction][0], y + DELTA[direction][1]
        self.maze[(x, y)] &= ~direction
        self.maze[(nx, ny)] &= ~OPPOSITE[direction]

    def _carve_passages_dfs(self) -> None:
        """Iterative DFS to carve a spanning tree (perfect maze)."""
        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = [self.entry]
        visited.add(self.entry)

        while stack:
            x, y = stack[-1]
            neighbors = [
                (d, x + dx, y + dy)
                for d, (dx, dy) in DELTA.items()
                if self._in_bounds(x + dx, y + dy)
                and (x + dx, y + dy) not in visited
            ]
            if neighbors:
                direction, nx, ny = self._rng.choice(neighbors)
                self._remove_wall(x, y, direction)
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()

    def _add_loops(self) -> None:
        """Remove ~5 % of interior walls to create light loops."""
        extra = max(1, (self.width * self.height) // 20)
        candidates = [
            (x, y, d)
            for y in range(self.height)
            for x in range(self.width)
            for d, (dx, dy) in DELTA.items()
            if self._in_bounds(x + dx, y + dy) and (self.maze[(x, y)] & d)
        ]
        self._rng.shuffle(candidates)
        for x, y, direction in candidates[:extra]:
            self._remove_wall(x, y, direction)

    def _enforce_outer_walls(self) -> None:
        """Close every border wall, then open entry and exit outer walls."""
        for x in range(self.width):
            self.maze[(x, 0)] |= NORTH
            self.maze[(x, self.height - 1)] |= SOUTH
        for y in range(self.height):
            self.maze[(0, y)] |= WEST
            self.maze[(self.width - 1, y)] |= EAST

        # Open the outer wall of entry and exit
        self._open_outer_wall(*self.entry)
        self._open_outer_wall(*self.exit)

    def _open_outer_wall(self, x: int, y: int) -> None:
        """Open whichever border wall faces outside for cell (x,y)."""
        if y == 0:
            self.maze[(x, y)] &= ~NORTH
        if y == self.height - 1:
            self.maze[(x, y)] &= ~SOUTH
        if x == 0:
            self.maze[(x, y)] &= ~WEST
        if x == self.width - 1:
            self.maze[(x, y)] &= ~EAST

    def _bfs_solution(self) -> list[tuple[int, int]]:
        """Return the shortest path from entry to exit using BFS."""
        start, end = self.entry, self.exit
        queue: deque[tuple[int, int]] = deque([start])
        prev: dict[tuple[int, int], Optional[tuple[int, int]]] = {start: None}

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == end:
                break
            for direction, (dx, dy) in DELTA.items():
                nx, ny = cx + dx, cy + dy
                if (
                    self._in_bounds(nx, ny)
                    and (nx, ny) not in prev
                    and not (self.maze[(cx, cy)] & direction)
                ):
                    prev[(nx, ny)] = (cx, cy)
                    queue.append((nx, ny))

        # Reconstruct path
        path: list[tuple[int, int]] = []
        node: Optional[tuple[int, int]] = end
        while node is not None:
            path.append(node)
            node = prev.get(node)
        path.reverse()
        return path if path and path[0] == start else []

    # ------------------------------------------------------------------
    # '42' pattern (visual only — does NOT modify maze walls)
    # ------------------------------------------------------------------

    def _compute_42_cells(self) -> set[tuple[int, int]]:
        """Return the set of cells that visually form the '42' pattern.

        The pattern is centred in the maze. It is purely decorative: the
        actual wall data is unchanged so connectivity is always preserved.
        The cells are rendered with a distinct colour by the display layer.
        """
        if not self.has_42_pattern():
            return set()

        pattern_w = 7   # 3 cols + 1 gap + 3 cols
        pattern_h = 5
        ox = (self.width - pattern_w) // 2
        oy = (self.height - pattern_h) // 2

        cells: set[tuple[int, int]] = set()
        for row_i, row in enumerate(_DIGIT_4):
            for col_i, filled in enumerate(row):
                if filled:
                    cx, cy = ox + col_i, oy + row_i
                    if self._in_bounds(cx, cy):
                        cells.add((cx, cy))

        for row_i, row in enumerate(_DIGIT_2):
            for col_i, filled in enumerate(row):
                if filled:
                    cx, cy = ox + 4 + col_i, oy + row_i
                    if self._in_bounds(cx, cy):
                        cells.add((cx, cy))
        return cells
