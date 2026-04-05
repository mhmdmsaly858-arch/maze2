*This project has been created as part of the 42 curriculum by your_login.*

# A-Maze-ing

## Description

A-Maze-ing is a Python maze generator that creates random mazes from a simple
configuration file and renders them in the terminal with full colour support.
It produces a hexadecimal output file encoding each cell's walls, along with the
BFS-shortest path from entry to exit. The maze always embeds a visible **"42"**
pattern when the dimensions allow it.

## Instructions

### Requirements

- Python 3.10+
- `flake8`, `mypy` (for linting)

### Installation

```bash
make install
```

### Run

```bash
make run
# or directly:
python3 a_maze_ing.py config.txt
```

### Debug

```bash
make debug
```

### Lint

```bash
make lint          # standard checks
make lint-strict   # mypy --strict
```

### Build the pip package

```bash
make build
# Produces dist/mazegen-1.0.0-py3-none-any.whl
pip install dist/mazegen-1.0.0-py3-none-any.whl
```

---

## Config file format

```
# Comments start with #
WIDTH=20           # number of columns (cells)
HEIGHT=15          # number of rows    (cells)
ENTRY=0,0          # entry cell (x,y)
EXIT=19,14         # exit  cell (x,y)
OUTPUT_FILE=maze.txt
PERFECT=True       # True → one unique path; False → adds loops
# SEED=42          # optional integer seed for reproducibility
```

---

## Algorithm choice

**Iterative DFS (recursive backtracker)**

- Simple to implement and fully understood.
- Produces *perfect* mazes with long, winding corridors — pleasant to navigate.
- Easy to extend with loop-injection for imperfect mazes.
- O(n) time and space where n = number of cells.

---

## Reusable module (`mazegen`)

The `mazegen` package exposes a single class `MazeGenerator` that can be imported
in any Python 3.10+ project:

```python
from mazegen import MazeGenerator

# Basic usage
gen = MazeGenerator(width=20, height=15, seed=42)
gen.generate(perfect=True)

# Access the maze (dict of bitmasks)
print(gen.maze[(0, 0)])        # int: walls bitmask for cell (0,0)
print(gen.solution)            # list of (x,y) tuples
print(gen.solution_as_directions())  # e.g. "EESSWN..."
print(gen.to_hex_grid())       # list of hex strings, one per row

# Custom entry/exit
gen2 = MazeGenerator(width=30, height=30, entry=(0,0), exit_=(29,29))
gen2.generate()
```

Wall bitmask encoding (matches output file):

| Bit | Direction |
|-----|-----------|
| 0   | North     |
| 1   | East      |
| 2   | South     |
| 3   | West      |

A bit set to **1** means the wall is **closed** (present).

---

## Team & project management

| Member | Role |
|--------|------|
| your_login | Everything (solo) |

**Planning:** Designed core data model first (bitmask per cell), then DFS carver,
then "42" pattern stamp, then BFS solver, then terminal renderer and menu.

**What worked well:** Keeping generation and rendering fully separate made
iteration fast.  The iterative DFS avoids Python recursion-limit issues for
large mazes.

**Could be improved:** A graphical MLX display would be cleaner for very large
mazes. The "42" stamp currently uses a simple 3×5 pixel font — a larger font
would be more visible.

---

## Resources

- [Maze generation algorithms – Wikipedia](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [Jamis Buck's blog: Maze algorithms](http://www.jamisbuck.org/mazes/)
- [Python `random` module docs](https://docs.python.org/3/library/random.html)
- [PEP 257 – Docstring conventions](https://peps.python.org/pep-0257/)

**AI usage:** Claude was used to help structure the project layout, review
bitmask logic, and generate docstrings. All code was reviewed, tested, and
understood before inclusion.
