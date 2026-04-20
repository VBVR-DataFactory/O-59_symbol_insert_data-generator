"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SYMBOL INSERT TASK PROMPTS                               ║
║                                                                               ║
║  Unified prompt template for Symbol Worlds_SymbolEditing_1:                  ║
║  Insert a symbol at a specific position in a sequence.                        ║
║                                                                               ║
║  Each prompt clearly specifies:                                               ║
║  - Which symbol to insert (with color)                                        ║
║  - At which position (1-indexed)                                              ║
║  - The animation sequence (fade in → slide down → shift)                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# ══════════════════════════════════════════════════════════════════════════════
#  DEFINE YOUR PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

# Unified prompt template (single structure for consistency)
PROMPT_TEMPLATE = (
    "Insert a {color} {symbol} at position {position}. "
    "A reference panel in the top-right shows the target symbol. "
    "The animation shows the new symbol fading in above the target position, "
    "then sliding down while other symbols shift to make room."
)


def get_prompt(insert_symbol: str, insert_color: str, position: int) -> str:
    """
    Generate a prompt for symbol insertion task.

    Args:
        insert_symbol: The symbol emoji to be inserted (e.g., '●', '▲')
        insert_color: The color name of the symbol (e.g., 'red', 'blue')
        position: The 1-indexed position where symbol will be inserted

    Returns:
        Formatted prompt string
    """
    return PROMPT_TEMPLATE.format(color=insert_color, symbol=insert_symbol, position=position)
