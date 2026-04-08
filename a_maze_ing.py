
"""
a_maze_ing.py - Main entry point for the A-Maze-ing project.
 
Usage:
    python3 a_maze_ing.py config.txt
"""
 
import sys
import os
from typing import Optional
import time
 
from mazegen import MazeGenerator, NORTH, EAST, SOUTH, WEST
 
# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET = "\033[0m"
WALL_COLOURS = [
    "\033[37m",   # white  (default)
    "\033[33m",   # yellow
    "\033[32m",   # green
    "\033[36m",   # cyan
    "\033[35m",   # magenta
    "\033[31m",   # red
]
PATH_COLOUR = "\033[96m"    # bright cyan
ENTRY_COLOUR = "\033[95m"   # magenta
EXIT_COLOUR = "\033[91m"    # bright red
COLOUR_42 = "\033[94m"      # blue for '42' cells
 
WALL_CH = "██"
OPEN_CH = "  "
 
 
# ── Config parsing ─────────────────────────────────────────────────────────────
 
def parse_config(path: str) -> dict[str, str]:
    """Parse KEY=VALUE config file, ignoring comment lines starting with #.
 
    Args:
        path: Path to the configuration file.
 
    Returns:
        Dictionary of key->value string pairs.
 
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: On bad syntax or missing required keys.
    """
    required = {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}
    cfg: dict[str, str] = {}

    try:
        with open(path, "r") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ValueError(
                        f"Config line {lineno}: expected KEY=VALUE, got: {line!r}"
                    )
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path!r}")

    missing = required - cfg.keys()
    if missing:
        raise ValueError(
            f"Missing required config keys: {', '.join(sorted(missing))}"
        )
    return cfg


def parse_coord(raw: str, label: str) -> tuple[int, int]:
    """Parse an 'x,y' string into a tuple of ints.
 
    Args:
        raw:   The raw string from the config (e.g. '0,0').
        label: Human-readable name used in error messages.

    Returns:
        Tuple (x, y).
 
    Raises:
        ValueError: If the format is wrong or values are not integers.
    """
    parts = raw.split(",")
    if len(parts) != 2:
        raise ValueError(f"{label}: expected 'x,y', got {raw!r}")
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise ValueError(
            f"{label}: coordinates must be integers, got {raw!r}"
        )


# ── Output file ───────────────────────────────────────────────────────────────
 
def write_output(gen: MazeGenerator, output_path: str) -> None:
    """Write the maze to a file in hex format with entry, exit and path.
 
    Args:
        gen:         Fully generated MazeGenerator.
        output_path: Destination file path.
    """
    rows = gen.to_hex_grid()
    ex, ey = gen.entry
    xx, xy = gen.exit
    direction_str = gen.solution_as_directions()
 
    with open(output_path, "w") as fh:
        for row in rows:
            fh.write(row + "\n")
        fh.write("\n")
        fh.write(f"{ex},{ey}\n")
        fh.write(f"{xx},{xy}\n")
        fh.write(direction_str + "\n")
 
 
# ── Terminal renderer ─────────────────────────────────────────────────────────
 
def render_terminal(
    gen: MazeGenerator,
    show_path: bool = False,
    colour_idx: int = 0
) -> None:
    """Render the maze to the terminal using block characters.
 
    The maze is drawn on a (2*H+1) x (2*W+1) character grid:
    - Even row + even col  → corner pillar (always wall)
    - Even row + odd  col  → horizontal wall segment (top/bottom of cell)
    - Odd  row + even col  → vertical   wall segment (left/right of cell)
    - Odd  row + odd  col  → cell interior
 
    Args:
        gen:        Generated maze.
        show_path:  Whether to highlight the solution path.
        colour_idx: Index into WALL_COLOURS.
        :    Whether to colour '42' pattern cells distinctly.
    """
    w, h = gen.width, gen.height
    path_set = set(gen.solution) if show_path else set()
    wall_col = WALL_COLOURS[colour_idx % len(WALL_COLOURS)]

    line = [[(wall_col + WALL_CH + RESET) for b in range(2 * w + 1)] for a in range(2 * h + 1)]

    for row in range(2 * h + 1):

        for col in range(2 * w + 1):
            on_h_edge = (row % 2 == 0)   # horizontal grid line
            on_v_edge = (col % 2 == 0)   # vertical grid line

            # Cell coordinates (only valid when row/col are odd)
            cx = col // 2
            cy = row // 2
    
            if on_h_edge and on_v_edge:
                # ── Corner pillar ──────────────────────────────────────────
               line[row][col] = wall_col + WALL_CH + RESET

            elif on_h_edge:
                # ── Horizontal wall between cell (cx, cy-1) and (cx, cy) ──
                # This segment is drawn at grid row `row` (even).
                # The cell above is (cx, cy-1); we check its SOUTH wall.
                cell_above_y = (row // 2) - 1
                if cell_above_y < 0:
                    # Top outer border → always wall
                    line[row][col] = wall_col + WALL_CH + RESET
                elif cell_above_y == h:
                    # Bottom outer border → always wall
                    line[row][col] = wall_col + WALL_CH + RESET
                else:
                    wall_closed = bool(gen.maze[(cx, cell_above_y)] & SOUTH)
                    if wall_closed:
                        line[row][col] = wall_col + WALL_CH + RESET
                    else:
                        line[row][col] = OPEN_CH

            elif on_v_edge:
                # ── Vertical wall between cell (cx-1, cy) and (cx, cy) ────
                cell_left_x = (col // 2) - 1
                if cell_left_x < 0:
                    # Left outer border → always wall
                    line[row][col] = wall_col + WALL_CH + RESET
                elif cell_left_x == w:
                    # Right outer border → always wall
                    line[row][col] = wall_col + WALL_CH + RESET
                else:
                    wall_closed = bool(gen.maze[(cell_left_x, cy)] & EAST)
                    if wall_closed:
                        line[row][col] = wall_col + WALL_CH + RESET
                    else:
                        line[row][col] = OPEN_CH

            else:
                # ── Cell interior ──────────────────────────────────────────
                cell = (cx, cy)
                if cell in gen.num_42:
                    line[row][col] = wall_col + WALL_CH + RESET
                elif cell == gen.entry:
                    line[row][col] = ENTRY_COLOUR + "🟢" + RESET
                elif cell == gen.exit:
                    line[row][col] = EXIT_COLOUR + "🔴" + RESET

                else:
                    line[row][col] = OPEN_CH
        # time.sleep(0.1)
            if not show_path:
                os.system("clear")
                for l in line:
                    print("".join(l))
                time.sleep(0.0005)

        if show_path:
            for i in range(len(gen.path)):
                x, y = gen.path[i]
                line[y * 2 + 1][x * 2 + 1] = PATH_COLOUR + "██" + RESET
                if (x, y) != gen.path[0]:
                    os.system("clear")
                    for l in line:
                        print("".join(l))
                    time.sleep(0.05)
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def build_generator(cfg: dict[str, str], seed: Optional[int]) -> MazeGenerator:
    """Instantiate and generate a maze from a config dict.
 
    Args:
        cfg:  Parsed configuration dictionary.
        seed: RNG seed (None for a random maze).
 
    Returns:
        A fully generated MazeGenerator.
    """
    width = int(cfg["WIDTH"])
    height = int(cfg["HEIGHT"])
    entry = parse_coord(cfg["ENTRY"], "ENTRY")
    exit_ = parse_coord(cfg["EXIT"], "EXIT")
    perfect = cfg["PERFECT"].strip().lower() in ("true", "1", "yes")
 
    gen = MazeGenerator(
        width=width, height=height, seed=seed,
        entry=entry, exit_=exit_
    )
    gen.generate(perfect=perfect)
    return gen
 
 
# ── Interactive menu ──────────────────────────────────────────────────────────
 
def interactive_loop(gen: MazeGenerator, cfg: dict[str, str]) -> None:
    """Run the interactive terminal menu.
 
    Args:
        gen: Initial generated maze to display.
        cfg: Parsed configuration dict for re-generation.
    """
    show_path = False
    colour_idx = 0

 
    render_terminal(gen, show_path, colour_idx)
 
    while True:
        print("\n==== A-Maze-ing ====")
        print("1. Re-generate a new maze")
        print("2. Show/Hide solution path")
        print("3. Rotate wall colour")
        print("4. Quit")
        choice = input("Choice (1-4): ").strip()
 
        if choice == "1":
            try:
                gen = build_generator(cfg, seed=None)
                show_path = False
                render_terminal(gen, show_path, colour_idx, )
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
 
        elif choice == "2":
            show_path = not show_path
            render_terminal(gen, show_path, colour_idx, )
 
        elif choice == "3":
            colour_idx = (colour_idx + 1) % len(WALL_COLOURS)
            render_terminal(gen, show_path, colour_idx, )
 
        elif choice == "4":
            print("Goodbye!")
            break
 
        else:
            print("Invalid choice, please enter 1-4.")
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
def main() -> None:
    """Entry point: parse config, generate maze, write output, show visual."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        sys.exit(1)
 
    config_path = sys.argv[1]
 
    try:
        cfg = parse_config(config_path)
        seed: Optional[int] = (
            int(cfg["SEED"]) if "SEED" in cfg else None
        )
        if int(cfg["WIDTH"]) < 3 or int(cfg["HEIGHT"]) < 3:
            raise ValueError("WIDTH and HEIGHT must both be >= 3")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
 
    try:
        gen = build_generator(cfg, seed)
    except ValueError as exc:
        print(f"Maze generation error: {exc}", file=sys.stderr)
        sys.exit(1)
 
    output_file = cfg["OUTPUT_FILE"]
    try:
        write_output(gen, output_file)
        print(f"Maze written to {output_file!r}")
    except OSError as exc:
        print(f"Error writing output file: {exc}", file=sys.stderr)
        sys.exit(1)
 
    interactive_loop(gen, cfg)
 
 
if __name__ == "__main__":
    main()
