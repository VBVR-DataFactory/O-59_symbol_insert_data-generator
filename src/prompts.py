"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SYMBOL INSERT TASK PROMPTS                               ║
║                                                                               ║
║  Prompt templates for Symbol Worlds_SymbolEditing_1:                          ║
║  Insert a symbol at a specific position in a sequence.                        ║
║                                                                               ║
║  Each prompt clearly specifies:                                               ║
║  - Which symbol to insert                                                     ║
║  - At which position (1-indexed)                                              ║
║  - The animation sequence (fade in → slide down → shift)                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random


# ══════════════════════════════════════════════════════════════════════════════
#  DEFINE YOUR PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_TEMPLATES = [
    "Insert symbol {symbol} at position {position} in the sequence. The video shows the new symbol fading in above the target position, then sliding down while other symbols shift to make room.",

    "Add symbol {symbol} at position {position} of the sequence. Animate the symbol appearing above the insertion point and moving into place as the existing symbols adjust their positions.",

    "Place symbol {symbol} at position {position} in the symbol sequence. The insertion is shown by the new symbol materializing above the target location and descending into position while subsequent symbols shift right.",

    "Insert the symbol {symbol} at position {position}. Show the symbol fading in above the sequence, sliding down to its position, and the remaining symbols shifting to accommodate the new addition.",
]


def get_prompt(insert_symbol: str, position: int, sequence_length: int = 0) -> str:
    """
    Generate a prompt for symbol insertion task.

    Args:
        insert_symbol: The symbol to be inserted
        position: The 1-indexed position where symbol will be inserted
        sequence_length: Length of the original sequence (not used in current templates)

    Returns:
        Formatted prompt string
    """
    # Note: sequence_length parameter kept for API compatibility but not used in current templates
    template = random.choice(PROMPT_TEMPLATES)
    return template.format(symbol=insert_symbol, position=position)


def get_all_prompts() -> list[str]:
    """Get all prompt templates."""
    return PROMPT_TEMPLATES
