"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   SYMBOL INSERT TASK CONFIGURATION                            ║
║                                                                               ║
║  Configuration for Symbol Worlds_SymbolEditing_1:                             ║
║  Insert a symbol at a specific position in a sequence.                        ║
║                                                                               ║
║  Task: Insert symbol S at position P in sequence [A, B, C, ...]               ║
║  Result: [A, B, ..., S, ..., C, ...]                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from pydantic import Field
from core import GenerationConfig


# ══════════════════════════════════════════════════════════════════════════════
#  COLOR DEFINITIONS (Scaling Feature)
# ══════════════════════════════════════════════════════════════════════════════

# Rainbow 7 colors - used for newly inserted symbols (easy to reference in prompts)
RAINBOW_COLOR_NAMES = {
    'red': (255, 0, 0),
    'orange': (255, 165, 0),
    'yellow': (255, 255, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'indigo': (75, 0, 130),
    'violet': (238, 130, 238),
}

# Extended 20 colors - used for all symbols in initial sequence
ALL_COLOR_NAMES = {
    # Rainbow 7 (must be first)
    'red': (255, 0, 0),
    'orange': (255, 165, 0),
    'yellow': (255, 255, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'indigo': (75, 0, 130),
    'violet': (238, 130, 238),
    # Extended 13 colors
    'pink': (255, 192, 203),
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    'brown': (165, 42, 42),
    'gray': (128, 128, 128),
    'olive': (128, 128, 0),
    'teal': (0, 128, 128),
    'navy': (0, 0, 128),
    'maroon': (128, 0, 0),
    'lime': (50, 205, 50),
    'aqua': (127, 255, 212),
    'silver': (192, 192, 192),
    'coral': (255, 127, 80),
}

# Symbol English names for prompts
SYMBOL_NAMES = {
    '●': 'circle',
    '▲': 'triangle',
    '■': 'square',
    '★': 'star',
    '◆': 'diamond',
    '♥': 'heart',
    '◯': 'hollow circle',
    '△': 'hollow triangle',
    '□': 'hollow square',
    '☆': 'hollow star',
    '◇': 'hollow diamond',
    '♦': 'filled diamond',
    '▼': 'down triangle',
    '▶': 'right triangle',
    '◀': 'left triangle',
}


class TaskConfig(GenerationConfig):
    """
    Symbol Insert Task configuration.

    Task: Insert a symbol at a specific position in a sequence.

    Inherited from GenerationConfig:
        - num_samples: int          # Number of samples to generate
        - domain: str               # Task domain name
        - difficulty: Optional[str] # Difficulty level
        - random_seed: Optional[int] # For reproducibility
        - output_dir: Path          # Where to save outputs
        - image_size: tuple[int, int] # Image dimensions
    """

    # ══════════════════════════════════════════════════════════════════════════
    #  OVERRIDE DEFAULTS
    # ══════════════════════════════════════════════════════════════════════════

    domain: str = Field(default="symbol_insert")
    image_size: tuple[int, int] = Field(default=(1024, 1024))

    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    generate_videos: bool = Field(
        default=True,
        description="Whether to generate ground truth videos"
    )

    video_fps: int = Field(
        default=16,
        description="Video frame rate"
    )

    # ══════════════════════════════════════════════════════════════════════════
    #  SYMBOL INSERT TASK SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    min_sequence_length: int = Field(
        default=4,
        ge=3,
        le=8,
        description="Minimum number of symbols in initial sequence"
    )

    max_sequence_length: int = Field(
        default=8,
        ge=4,
        le=12,
        description="Maximum number of symbols in initial sequence"
    )

    symbol_set: str = Field(
        default="shapes",
        description="Symbol set to use: 'shapes', 'letters', 'numbers', 'mixed'"
    )

    symbol_size: int = Field(
        default=85,
        ge=40,
        le=120,
        description="Size of each symbol in pixels"
    )
