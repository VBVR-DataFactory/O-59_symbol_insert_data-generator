"""Symbol Insert Task generator - Insert symbol at position in sequence."""

import random
from pathlib import Path
import tempfile
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig, RAINBOW_COLOR_NAMES, ALL_COLOR_NAMES
from .prompts import get_prompt


# Symbol sets
SYMBOL_SETS = {
    "shapes": ["●", "▲", "■", "★", "◆", "♥", "◯", "△", "□", "☆", "◇", "♦", "▼", "▶", "◀"],
    "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    "numbers": list("0123456789"),
    "mixed": ["●", "▲", "■", "★", "A", "B", "C", "1", "2", "3", "X", "Y", "Z"]
}


class SymbolInsertGenerator(BaseGenerator):
    """Generates symbol insertion tasks with color scaling."""

    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")

        # Select symbol set
        self.symbols = SYMBOL_SETS.get(config.symbol_set, SYMBOL_SETS["shapes"])

        # Load color names from config
        self.rainbow_color_names = list(RAINBOW_COLOR_NAMES.keys())
        self.all_color_names = list(ALL_COLOR_NAMES.keys())

        # Colors
        self.bg_color = (255, 255, 255)  # Pure white background
        self.border_color = (60, 60, 60)
        self.text_color = (40, 40, 40)

    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one symbol insertion task with color information."""
        # Generate initial sequence length
        seq_length = random.randint(self.config.min_sequence_length, self.config.max_sequence_length)

        # Pick insertion position first
        insert_position = random.randint(0, seq_length)  # 0 to seq_length inclusive

        # Build initial sequence with colors (allow symbol repetition, different colors)
        sequence: List[Tuple[str, str]] = []
        for _ in range(seq_length):
            symbol = random.choice(self.symbols)
            color_name = random.choice(self.all_color_names)
            sequence.append((symbol, color_name))

        # Pick a new symbol to insert (from rainbow colors)
        insert_symbol = random.choice(self.symbols)
        insert_color_name = random.choice(self.rainbow_color_names)

        # Create final sequence
        final_sequence = (
            sequence[:insert_position] + 
            [(insert_symbol, insert_color_name)] + 
            sequence[insert_position:]
        )

        # Generate animation frames first to ensure alignment
        frames = self._create_animation_frames(sequence, final_sequence, insert_symbol, insert_color_name, insert_position)
        
        # Extract first and final images from frames
        first_image = frames[0]
        final_image = frames[-1]

        # Generate video if enabled
        video_path = None
        if self.config.generate_videos and self.video_generator:
            temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
            temp_dir.mkdir(parents=True, exist_ok=True)
            video_path = temp_dir / f"{task_id}_ground_truth.mp4"
            result = self.video_generator.create_video_from_frames(frames, video_path)
            video_path = str(result) if result else None

        # Get prompt (1-indexed position for human readability)
        prompt = get_prompt(insert_symbol, insert_color_name, insert_position + 1)

        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )

    def _render_sequence(self, sequence: List[Tuple[str, str]]) -> Image.Image:
        """Render a sequence of symbols with colors."""
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

        # Draw each symbol with its color
        for i, (symbol, color_name) in enumerate(sequence):
            x = start_x + i * spacing
            color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
            self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)

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

    def _generate_video(
        self, 
        initial_seq: List[Tuple[str, str]], 
        final_seq: List[Tuple[str, str]],
        insert_symbol: str, 
        insert_color_name: str,
        insert_pos: int, 
        task_id: str
    ) -> Optional[str]:
        """Generate video showing the insertion animation."""
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"

        frames = self._create_animation_frames(
            initial_seq, final_seq, insert_symbol, insert_color_name, insert_pos
        )
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None

    def _create_animation_frames(
        self, 
        initial_seq: List[Tuple[str, str]], 
        final_seq: List[Tuple[str, str]],
        insert_symbol: str,
        insert_color_name: str,
        insert_pos: int,
        hold_frames: int = 5,
        shift_frames: int = 8,
        fade_frames: int = 6,
        slide_frames: int = 8
    ) -> List[Image.Image]:
        """Create animation frames using O-61 style:
        1. Existing symbols shift left/right to make space (zoom open)
        2. New symbol fades in above the gap
        3. New symbol slides down into the gap
        
        Uses a fixed center point to prevent visual "jumping" during animation.
        """
        frames = []
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        
        # Calculate fixed center position (prevents jumping)
        fixed_center_x = width // 2  # Fixed center point (never changes)
        
        # Calculate start positions for initial and final sequences
        initial_total_width = len(initial_seq) * spacing - 20
        initial_start_x = fixed_center_x - (initial_total_width // 2)
        
        final_total_width = len(final_seq) * spacing - 20
        final_start_x = fixed_center_x - (final_total_width // 2)

        # Show initial sequence (centered at fixed position)
        frames.extend([self._render_sequence_fixed(initial_seq, initial_start_x)] * hold_frames)

        # Get color RGB for new symbol
        insert_color_rgb = ALL_COLOR_NAMES.get(insert_color_name, (0, 0, 0))
        
        # Check if insertion is at boundary (leftmost or rightmost)
        is_leftmost = (insert_pos == 0)
        is_rightmost = (insert_pos == len(initial_seq))
        is_boundary = is_leftmost or is_rightmost

        # Phase 1: Existing symbols shift left/right to make space (only for middle insertions)
        if not is_boundary:
            for i in range(shift_frames):
                progress = (i + 1) / shift_frames
                frame = self._render_shift_frame(
                    initial_seq, insert_pos, progress, initial_start_x, final_start_x
                )
                frames.append(frame)

        # Phase 2: New symbol fades in above the gap
        for i in range(fade_frames):
            progress = (i + 1) / fade_frames
            frame = self._render_fade_in_frame(
                initial_seq, insert_symbol, insert_color_rgb, insert_pos, progress,
                is_boundary, initial_start_x, final_start_x
            )
            frames.append(frame)

        # Phase 3: New symbol slides down into the gap
        for i in range(slide_frames):
            progress = (i + 1) / slide_frames
            frame = self._render_slide_down_frame(
                initial_seq, insert_symbol, insert_color_rgb, insert_pos, progress,
                is_boundary, initial_start_x, final_start_x
            )
            frames.append(frame)

        # Show final sequence (centered at fixed position)
        frames.extend([self._render_sequence_fixed(final_seq, final_start_x)] * hold_frames)

        return frames

    def _render_sequence_fixed(self, sequence: List[Tuple[str, str]], start_x: int) -> Image.Image:
        """Render a sequence of symbols with colors at a fixed start position."""
        width, height = self.config.image_size
        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)

        if not sequence:
            return img

        # Calculate symbol spacing
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2

        # Load font
        font_size = symbol_size
        font = self._get_unicode_font(font_size)

        # Draw each symbol with its color at fixed positions
        for i, (symbol, color_name) in enumerate(sequence):
            x = start_x + i * spacing
            color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
            self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)

        return img

    def _render_shift_frame(
        self,
        sequence: List[Tuple[str, str]],
        insert_pos: int,
        progress: float,
        current_start_x: int,
        next_start_x: int
    ) -> Image.Image:
        """Render frame with symbols shifting left/right to make space."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2

        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = self._get_unicode_font(symbol_size)

        # Draw symbols with interpolated positions
        for i, (symbol, color_name) in enumerate(sequence):
            if i < insert_pos:
                # Symbols before insertion: shift from current to next layout
                initial_x = current_start_x + i * spacing
                final_x = next_start_x + i * spacing
                current_x = initial_x + (final_x - initial_x) * progress
            else:
                # Symbols at/after insertion: shift right to make room
                initial_x = current_start_x + i * spacing
                final_x = next_start_x + (i + 1) * spacing
                current_x = initial_x + (final_x - initial_x) * progress

            color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
            self._draw_symbol(draw, symbol, int(current_x), center_y, symbol_size, color_rgb, font)

        return img

    def _render_fade_in_frame(
        self, 
        sequence: List[Tuple[str, str]], 
        new_symbol: str,
        new_color: tuple,
        insert_pos: int, 
        fade_progress: float,
        is_boundary: bool,
        current_start_x: int,
        next_start_x: int
    ) -> Image.Image:
        """Render frame with new symbol fading in above the gap."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2

        # Create base image
        img = Image.new('RGB', (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = self._get_unicode_font(symbol_size)

        if is_boundary:
            # Boundary insertion: sequence stays in place
            for i, (symbol, color_name) in enumerate(sequence):
                x = current_start_x + i * spacing
                color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
                self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)
            
            # Calculate where new symbol will appear
            if insert_pos == 0:
                # Leftmost: symbol appears to the left of first symbol
                x = current_start_x - spacing
            else:
                # Rightmost: symbol appears to the right of last symbol
                x = current_start_x + len(sequence) * spacing
        else:
            # Middle insertion: sequence already shifted, use next layout
            for i, (symbol, color_name) in enumerate(sequence):
                if i < insert_pos:
                    x = next_start_x + i * spacing
                else:
                    x = next_start_x + (i + 1) * spacing
                color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
                self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)
            
            # New symbol appears in the gap
            x = next_start_x + insert_pos * spacing

        # Calculate new symbol position above the line
        new_symbol_y = center_y - symbol_size

        # Create overlay for fading symbol
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Draw new symbol with alpha
        alpha = int(255 * fade_progress)
        rgba_color = (*new_color, alpha)

        bbox = overlay_draw.textbbox((0, 0), new_symbol, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = x - text_width // 2
        text_y = new_symbol_y - text_height // 2

        overlay_draw.text((text_x, text_y), new_symbol, fill=rgba_color, font=font)

        # Composite
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        return img.convert('RGB')

    def _render_slide_down_frame(
        self, 
        sequence: List[Tuple[str, str]], 
        new_symbol: str,
        new_color: tuple,
        insert_pos: int, 
        slide_progress: float,
        is_boundary: bool,
        current_start_x: int,
        next_start_x: int
    ) -> Image.Image:
        """Render frame with symbol sliding down into position."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2

        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = self._get_unicode_font(symbol_size)

        if is_boundary:
            # Boundary insertion: sequence stays in place
            for i, (symbol, color_name) in enumerate(sequence):
                x = current_start_x + i * spacing
                color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
                self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)
            
            # Calculate where new symbol slides down
            if insert_pos == 0:
                x = current_start_x - spacing
            else:
                x = current_start_x + len(sequence) * spacing
        else:
            # Middle insertion: sequence in final position
            for i, (symbol, color_name) in enumerate(sequence):
                if i < insert_pos:
                    x = next_start_x + i * spacing
                else:
                    x = next_start_x + (i + 1) * spacing
                color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
                self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)
            
            x = next_start_x + insert_pos * spacing

        # Draw new symbol sliding down
        initial_y = center_y - symbol_size
        target_y = center_y
        new_symbol_y = int(initial_y + (target_y - initial_y) * slide_progress)

        self._draw_symbol(draw, new_symbol, x, new_symbol_y, symbol_size, new_color, font)

        return img
