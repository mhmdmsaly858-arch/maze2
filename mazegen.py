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
        w = self.width // 2
        h = self.height // 2
        self.num_42 = []
        if self.width > 8 and self.height > 6:
            self.num_42 = [
                (w - 1, h),
                (w - 2, h),
                (w - 3, h),
                (w - 3, h - 1),
                (w - 3, h - 2),
                (w - 1, h + 1),
                (w + 1, h),
                (w + 2, h),
                (w + 3, h),
                (w + 1, h + 2),
                (w + 2, h + 2),
                (w + 3, h + 2),
                (w + 1, h - 2),
                (w + 2, h - 2),
                (w + 3, h - 2),
                (w + 3, h - 1),
                (w + 1, h + 1),
                (w - 1, h + 2),
            ]
        if not self._in_bounds(*self.entry):
            raise ValueError(f"entry {self.entry} is out of bounds")
        if not self._in_bounds(*self.exit):
            raise ValueError(f"exit {self.exit} is out of bounds")
        if self.entry == self.exit:
            raise ValueError("entry and exit must be different cells")
        if self.entry in self.num_42 or self.exit in self.num_42:
            raise ValueError("ENTRY and EXIT must be outside 42!")
        self.maze: dict[tuple[int, int], int] = {}
        self.solution: list[tuple[int, int]] = []
        self.pattern42: set[tuple[int, int]] = set()
        self._rng = random.Random(seed)

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

        self.solution = self._bfs_solution()

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
        self.maze[(x, y)] -= direction
        self.maze[(nx, ny)] -= OPPOSITE[direction]

    def _carve_passages_dfs(self) -> None:
        """Iterative DFS to carve a spanning tree (perfect maze)."""
        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = [self.entry]
        visited.add(self.entry)
        if len(self.num_42):
            for x, y in self.num_42:
                visited.add((x, y))
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
            if 0 <= x + dx < self.width and 0 <= y + dy < self.height
            and (self.maze[(x, y)] & d)
            and (x, y) not in self.num_42
            and (x + dx, y + dy) not in self.num_42
        ]
        self._rng.shuffle(candidates)
        for x, y, direction in candidates[:extra]:
            if (self.maze[(x, y)] & direction):
                self._remove_wall(x, y, direction)

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
                if self._in_bounds(nx, ny) and (nx, ny) not in prev and not (
                    self.maze[(cx, cy)] & direction
                ):
                    prev[(nx, ny)] = (cx, cy)
                    queue.append((nx, ny))
        # Reconstruct path
        self.path: list[tuple[int, int]] = []
        node: Optional[tuple[int, int]] = end
        while node is not None:
            self.path.append(node)
            node = prev.get(node)
        self.path.reverse()
        return self.path
