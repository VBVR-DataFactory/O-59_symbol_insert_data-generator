"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SYMBOL INSERT TASK PROMPTS                               ║
║                                                                               ║
║  Unified prompt template for Symbol Worlds_SymbolEditing_1:                  ║
║  Insert a symbol at a specific position in a sequence.                        ║
║                                                                               ║
║  Each prompt clearly specifies:                                               ║
║  - Which symbol to insert                                                     ║
║  - At which position (1-indexed)                                              ║
║  - The animation sequence (fade in → slide down → shift)                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# ══════════════════════════════════════════════════════════════════════════════
#  DEFINE YOUR PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

# Unified prompt template (single structure for consistency)
PROMPT_TEMPLATE = (
    "Insert {symbol} at position {position}. "
    "The animation shows the new symbol fading in above the target position, "
    "then sliding down while other symbols shift to make room."
)


def get_prompt(insert_symbol: str, position: int, sequence_length: int = 0) -> str:
    """
    Generate a prompt for symbol insertion task.

    Args:
        insert_symbol: The symbol to be inserted
        position: The 1-indexed position where symbol will be inserted
        sequence_length: Length of the original sequence (not used in current template)

    Returns:
        Formatted prompt string
    """
    # Note: sequence_length parameter kept for API compatibility but not used in current template
    return PROMPT_TEMPLATE.format(symbol=insert_symbol, position=position)


def get_all_prompts() -> list[str]:
    """Get all prompt templates."""
    return PROMPT_TEMPLATES
