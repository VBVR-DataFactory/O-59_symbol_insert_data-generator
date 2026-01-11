"""Symbol Insert Task generator - Insert symbol at position in sequence."""

import random
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt


# Symbol sets
SYMBOL_SETS = {
    "shapes": ["●", "▲", "■", "★", "◆", "♥", "◯", "△", "□", "☆", "◇", "♦", "▼", "▶", "◀"],
    "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    "numbers": list("0123456789"),
    "mixed": ["●", "▲", "■", "★", "A", "B", "C", "1", "2", "3", "X", "Y", "Z"]
}

# Colors for symbols (diverse palette)
SYMBOL_COLORS = [
    (220, 60, 60),    # Red
    (60, 60, 220),    # Blue
    (60, 180, 60),    # Green
    (220, 160, 60),   # Orange
    (160, 60, 220),   # Purple
    (60, 180, 180),   # Cyan
    (220, 60, 160),   # Pink
    (100, 150, 60),   # Olive
    (220, 120, 60),   # Coral
    (80, 80, 200),    # Indigo
]


class SymbolInsertGenerator(BaseGenerator):
    """Generates symbol insertion tasks."""

    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")

        # Select symbol set
        self.symbols = SYMBOL_SETS.get(config.symbol_set, SYMBOL_SETS["shapes"])

        # Colors
        self.bg_color = (255, 255, 255)  # Pure white background
        self.border_color = (60, 60, 60)
        self.text_color = (40, 40, 40)

    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one symbol insertion task."""
        # Generate initial sequence
        seq_length = random.randint(self.config.min_sequence_length, self.config.max_sequence_length)

        # Pick symbols without replacement for the sequence
        sequence = random.sample(self.symbols, seq_length)

        # Pick a new symbol to insert (not in current sequence)
        available_symbols = [s for s in self.symbols if s not in sequence]
        if not available_symbols:
            # Fallback: allow duplicates if we run out of unique symbols
            available_symbols = self.symbols
        insert_symbol = random.choice(available_symbols)

        # Pick insertion position (1-indexed for user, but we'll use 0-indexed internally)
        # Position 0 = insert at beginning, position len = insert at end
        insert_position = random.randint(0, len(sequence))

        # Create final sequence
        final_sequence = sequence[:insert_position] + [insert_symbol] + sequence[insert_position:]

        # Assign colors to symbols
        color_map = self._create_color_map(final_sequence)

        # Render images
        first_image = self._render_sequence(sequence, color_map)
        final_image = self._render_sequence(final_sequence, color_map)

        # Generate video if enabled
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(
                sequence, final_sequence, insert_symbol, insert_position, color_map, task_id
            )

        # Get prompt (1-indexed position for human readability)
        prompt = get_prompt(insert_symbol, insert_position + 1, len(sequence))

        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )

    def _create_color_map(self, all_symbols: List[str]) -> dict:
        """Assign consistent colors to symbols."""
        color_map = {}
        for i, symbol in enumerate(set(all_symbols)):
            color_map[symbol] = SYMBOL_COLORS[i % len(SYMBOL_COLORS)]
        return color_map

    def _render_sequence(self, sequence: List[str], color_map: dict) -> Image.Image:
        """Render a sequence of symbols."""
        width, height = self.config.image_size
        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)

        if not sequence:
            return img

        # Calculate symbol spacing
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        total_width = len(sequence) * spacing - 20
        start_x = (width - total_width) // 2
        center_y = height // 2

        # Load font - try fonts with good Unicode symbol support
        font_size = symbol_size
        font = self._get_unicode_font(font_size)

        # Draw each symbol
        for i, symbol in enumerate(sequence):
            x = start_x + i * spacing
            self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_map[symbol], font)

        return img

    def _draw_symbol(self, draw: ImageDraw.Draw, symbol: str, x: int, y: int,
                    size: int, color: tuple, font: ImageFont.FreeTypeFont):
        """Draw a single symbol at position (x, y)."""
        # Get text bounding box
        bbox = draw.textbbox((0, 0), symbol, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        text_x = x - text_width // 2
        text_y = y - text_height // 2

        # Draw the symbol
        draw.text((text_x, text_y), symbol, fill=color, font=font)

    def _get_unicode_font(self, font_size: int) -> ImageFont.FreeTypeFont:
        """Get a font that supports Unicode symbols well."""
        # Try fonts in order of preference (best Unicode symbol support first)
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS - excellent Unicode support
            "/Library/Fonts/Arial Unicode.ttf",  # macOS alternative location
            "/System/Library/Fonts/Apple Symbols.ttf",  # macOS - good for symbols
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
            "Arial Unicode MS",  # Cross-platform name
            "DejaVu Sans",  # Cross-platform name
            "Segoe UI Symbol",  # Windows
        ]

        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, font_size)
            except (OSError, IOError):
                continue

        # Final fallback
        return ImageFont.load_default()

    def _generate_video(self, initial_seq: List[str], final_seq: List[str],
                       insert_symbol: str, insert_pos: int, color_map: dict,
                       task_id: str) -> Optional[str]:
        """Generate video showing the insertion animation."""
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"

        frames = self._create_animation_frames(
            initial_seq, final_seq, insert_symbol, insert_pos, color_map
        )
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None

    def _create_animation_frames(self, initial_seq: List[str], final_seq: List[str],
                                 insert_symbol: str, insert_pos: int, color_map: dict,
                                 hold_frames: int = 5,
                                 fade_frames: int = 8,
                                 slide_frames: int = 10,
                                 shift_frames: int = 8) -> List[Image.Image]:
        """Create animation frames for symbol insertion."""
        frames = []
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20

        # Show initial sequence
        frames.extend([self._render_sequence(initial_seq, color_map)] * hold_frames)

        # Phase 1: New symbol fades in above the insertion position
        for i in range(fade_frames):
            progress = (i + 1) / fade_frames
            frame = self._render_fade_in_frame(initial_seq, insert_symbol, insert_pos,
                                               color_map, progress)
            frames.append(frame)

        # Phase 2: Symbol slides down into position while others shift right
        for i in range(slide_frames):
            progress = (i + 1) / slide_frames
            frame = self._render_slide_and_shift_frame(initial_seq, insert_symbol, insert_pos,
                                                       color_map, progress)
            frames.append(frame)

        # Show final sequence
        frames.extend([self._render_sequence(final_seq, color_map)] * hold_frames)

        return frames

    def _render_fade_in_frame(self, sequence: List[str], new_symbol: str,
                              insert_pos: int, color_map: dict,
                              alpha_progress: float) -> Image.Image:
        """Render frame with new symbol fading in above insertion position."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20

        # Start with base sequence
        img = self._render_sequence(sequence, color_map).convert('RGBA')

        # Calculate position for new symbol (above the insertion point)
        total_width = len(sequence) * spacing - 20
        start_x = (width - total_width) // 2
        center_y = height // 2

        new_symbol_x = start_x + insert_pos * spacing
        new_symbol_y = center_y - symbol_size  # Above the line

        # Create overlay for fading symbol
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Load font - try fonts with good Unicode symbol support
        font_size = symbol_size
        font = self._get_unicode_font(font_size)

        # Draw new symbol with alpha
        color = color_map[new_symbol]
        alpha = int(255 * alpha_progress)
        rgba_color = (*color, alpha)

        bbox = overlay_draw.textbbox((0, 0), new_symbol, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = new_symbol_x - text_width // 2
        text_y = new_symbol_y - text_height // 2

        overlay_draw.text((text_x, text_y), new_symbol, fill=rgba_color, font=font)

        # Composite
        result = Image.alpha_composite(img, overlay)
        return result.convert('RGB')

    def _render_slide_and_shift_frame(self, sequence: List[str], new_symbol: str,
                                      insert_pos: int, color_map: dict,
                                      progress: float) -> Image.Image:
        """Render frame with symbol sliding down and others shifting right."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2

        # Calculate layout
        initial_total_width = len(sequence) * spacing - 20
        initial_start_x = (width - initial_total_width) // 2

        final_total_width = (len(sequence) + 1) * spacing - 20
        final_start_x = (width - final_total_width) // 2

        # Create image
        img = Image.new('RGB', (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # Load font - try fonts with good Unicode symbol support
        font_size = symbol_size
        font = self._get_unicode_font(font_size)

        # Draw symbols with interpolated positions
        for i, symbol in enumerate(sequence):
            if i < insert_pos:
                # Symbols before insertion: shift from initial to final layout
                initial_x = initial_start_x + i * spacing
                final_x = final_start_x + i * spacing
                current_x = initial_x + (final_x - initial_x) * progress
            else:
                # Symbols after insertion: shift right to make room
                initial_x = initial_start_x + i * spacing
                final_x = final_start_x + (i + 1) * spacing
                current_x = initial_x + (final_x - initial_x) * progress

            self._draw_symbol(draw, symbol, int(current_x), center_y,
                            symbol_size, color_map[symbol], font)

        # Draw new symbol sliding down
        new_x = final_start_x + insert_pos * spacing
        start_y = center_y - symbol_size
        current_y = start_y + (center_y - start_y) * progress

        self._draw_symbol(draw, new_symbol, new_x, int(current_y),
                         symbol_size, color_map[new_symbol], font)

        return img
