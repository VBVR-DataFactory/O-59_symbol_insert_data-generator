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
    image_size: tuple[int, int] = Field(default=(800, 200))

    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO SETTINGS
    # ══════════════════════════════════════════════════════════════════════════

    generate_videos: bool = Field(
        default=True,
        description="Whether to generate ground truth videos"
    )

    video_fps: int = Field(
        default=10,
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
        default=60,
        ge=40,
        le=100,
        description="Size of each symbol in pixels"
    )
