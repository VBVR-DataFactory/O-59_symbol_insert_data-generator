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

    def _centered_start_x(self, center_x: int, slot_count: int, spacing: int) -> int:
        """Return x of the first slot center so the row is centered."""
        if slot_count <= 1:
            return center_x
        return int(round(center_x - ((slot_count - 1) * spacing) / 2.0))

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

        # Build object-centric metadata
        optimized_task_data = self._build_objects_metadata(
            initial_sequence=sequence,
            final_sequence=final_sequence,
            insert_position=insert_position,
            insert_symbol=insert_symbol,
            insert_color_name=insert_color_name
        )
        
        # Build metadata
        metadata = self._build_metadata(task_id, optimized_task_data)
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path,
            metadata=metadata
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
        start_x = self._centered_start_x(width // 2, len(sequence), spacing)
        center_y = height // 2

        # Load font - try fonts with good Unicode symbol support
        font_size = symbol_size
        font = self._get_unicode_font(font_size)

        # Draw each symbol with its color
        for i, (symbol, color_name) in enumerate(sequence):
            x = start_x + i * spacing
            color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
            self._draw_symbol(draw, symbol, x, center_y, symbol_size, color_rgb, font)
        self._draw_add_candidate_panel(draw, symbol_size)

        return img

    def _draw_symbol(self, draw: ImageDraw.Draw, symbol: str, x: int, y: int,
                    size: int, color: tuple, font: ImageFont.FreeTypeFont):
        """Draw a single symbol at position (x, y)."""
        max_side = max(12, size - 12)
        fit_font, bbox = self._fit_symbol_font(draw, symbol, font, max_side, max_side)
        # Center using real glyph bbox (handles Unicode baseline offsets)
        text_x = int(round(x - (bbox[0] + bbox[2]) / 2))
        text_y = int(round(y - (bbox[1] + bbox[3]) / 2))
        dx, dy = self._get_optical_center_offset(symbol, fit_font)
        text_x += dx
        text_y += dy

        # Draw the symbol
        draw.text((text_x, text_y), symbol, fill=color, font=fit_font)

    def _get_optical_center_offset(self, symbol: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Measure rendered ink center and return correction offset."""
        if not hasattr(self, "_optical_center_cache"):
            self._optical_center_cache = {}
        key = (symbol, getattr(font, "size", 0))
        if key in self._optical_center_cache:
            return self._optical_center_cache[key]

        canvas = max(64, int(getattr(font, "size", 32) * 4))
        tmp = Image.new("L", (canvas, canvas), 0)
        tmp_draw = ImageDraw.Draw(tmp)
        bbox = tmp_draw.textbbox((0, 0), symbol, font=font)
        tx = int(round(canvas / 2 - (bbox[0] + bbox[2]) / 2))
        ty = int(round(canvas / 2 - (bbox[1] + bbox[3]) / 2))
        tmp_draw.text((tx, ty), symbol, fill=255, font=font)
        ink_bbox = tmp.getbbox()
        if ink_bbox is None:
            self._optical_center_cache[key] = (0, 0)
            return (0, 0)

        ink_cx = (ink_bbox[0] + ink_bbox[2]) / 2
        ink_cy = (ink_bbox[1] + ink_bbox[3]) / 2
        dx = int(round(canvas / 2 - ink_cx))
        dy = int(round(canvas / 2 - ink_cy))
        self._optical_center_cache[key] = (dx, dy)
        return (dx, dy)

    def _fit_symbol_font(
        self,
        draw: ImageDraw.Draw,
        symbol: str,
        base_font: ImageFont.FreeTypeFont,
        max_width: int,
        max_height: int,
    ) -> tuple[ImageFont.FreeTypeFont, tuple]:
        """Pick the largest font that keeps glyph fully inside slot bounds."""
        start_size = getattr(base_font, "size", self.config.symbol_size)
        for sz in range(start_size, 7, -1):
            f = self._get_unicode_font(sz)
            bbox = draw.textbbox((0, 0), symbol, font=f)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw <= max_width and th <= max_height:
                return f, bbox
        fallback = self._get_unicode_font(8)
        return fallback, draw.textbbox((0, 0), symbol, font=fallback)

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
        
        # Fixed slot grid for the entire sample.
        slot_count = max(len(initial_seq), len(final_seq))
        fixed_start_x = self._centered_start_x(fixed_center_x, slot_count, spacing)

        # Get color RGB for new symbol
        insert_color_rgb = ALL_COLOR_NAMES.get(insert_color_name, (0, 0, 0))
        self._candidate_add_symbol = insert_symbol
        self._candidate_add_color = insert_color_rgb

        # Show initial sequence (centered at fixed position)
        hi = min(insert_pos, max(0, slot_count - 1))
        frames.extend(
            [self._render_sequence_fixed(initial_seq, fixed_start_x, slot_count, hi)] * hold_frames
        )
        
        # Check if insertion is at boundary (leftmost or rightmost)
        is_leftmost = (insert_pos == 0)
        is_rightmost = (insert_pos == len(initial_seq))
        is_boundary = is_leftmost or is_rightmost

        # Phase 1: Existing symbols shift left/right to make space (only for middle insertions)
        if not is_boundary:
            for i in range(shift_frames):
                progress = i / max(1, shift_frames - 1)
                frame = self._render_shift_frame(
                    initial_seq, insert_pos, progress, fixed_start_x, fixed_start_x, slot_count
                )
                frames.append(frame)

        # Phase 2: New symbol fades in above the gap
        for i in range(fade_frames):
            progress = i / max(1, fade_frames - 1)
            frame = self._render_fade_in_frame(
                initial_seq, insert_symbol, insert_color_rgb, insert_pos, progress,
                is_boundary, fixed_start_x, fixed_start_x, slot_count
            )
            frames.append(frame)

        # Phase 3: New symbol slides down into the gap
        for i in range(slide_frames):
            progress = i / max(1, slide_frames - 1)
            frame = self._render_slide_down_frame(
                initial_seq, insert_symbol, insert_color_rgb, insert_pos, progress,
                is_boundary, fixed_start_x, fixed_start_x, slot_count
            )
            frames.append(frame)

        # Show final sequence (centered at fixed position)
        frames.extend(
            [self._render_sequence_fixed(final_seq, fixed_start_x, slot_count, None)] * hold_frames
        )

        return frames

    def _draw_position_slots_unicode(
        self,
        draw: ImageDraw.Draw,
        total_slots: int,
        start_x: int,
        spacing: int,
        center_y: int,
        symbol_size: int,
        highlight_index: Optional[int],
    ) -> None:
        slot_gap = 8
        half = max(symbol_size // 2 + 4, (spacing - slot_gap) // 2)
        try:
            label_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
            )
        except OSError:
            try:
                label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 28)
            except OSError:
                label_font = ImageFont.load_default()
        for i in range(total_slots):
            cx = start_x + i * spacing
            box = [cx - half, center_y - half, cx + half, center_y + half]
            if highlight_index is not None and i == highlight_index:
                draw.rectangle(box, outline=(220, 70, 55), width=4)
            else:
                draw.rectangle(box, outline=(170, 170, 170), width=1)
            lab = str(i + 1)
            bbox = draw.textbbox((0, 0), lab, font=label_font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((cx - tw // 2, center_y + half + 20), lab, fill=(70, 70, 70), font=label_font)

    def _draw_add_candidate_panel(self, draw: ImageDraw.Draw, symbol_size: int) -> None:
        symbol = getattr(self, "_candidate_add_symbol", None)
        color = getattr(self, "_candidate_add_color", None)
        if symbol is None or color is None:
            return

        width, _ = self.config.image_size
        panel_w = max(90, symbol_size + 34)
        panel_h = max(90, symbol_size + 34)
        margin = 18
        left = width - panel_w - margin
        top = margin
        right = left + panel_w
        bottom = top + panel_h

        draw.rectangle([left, top, right, bottom], outline=(165, 165, 165), width=1, fill=(255, 255, 255))
        cx = left + panel_w // 2
        cy = top + panel_h // 2
        font = self._get_unicode_font(symbol_size)
        self._draw_symbol(draw, symbol, cx, cy, symbol_size, color, font)

    def _render_sequence_fixed(
        self,
        sequence: List[Tuple[str, str]],
        start_x: int,
        slot_count: int,
        highlight_slot: Optional[int] = None,
    ) -> Image.Image:
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
        symbol_center_y = center_y

        # Load font
        font_size = symbol_size
        font = self._get_unicode_font(font_size)

        self._draw_position_slots_unicode(
            draw, slot_count, start_x, spacing, center_y, symbol_size, highlight_slot
        )
        self._draw_add_candidate_panel(draw, symbol_size)

        # Draw each symbol with its color at fixed positions
        for i, (symbol, color_name) in enumerate(sequence):
            x = start_x + i * spacing
            color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
            self._draw_symbol(draw, symbol, x, symbol_center_y, symbol_size, color_rgb, font)

        return img

    def _render_shift_frame(
        self,
        sequence: List[Tuple[str, str]],
        insert_pos: int,
        progress: float,
        current_start_x: int,
        next_start_x: int,
        slot_count: int,
    ) -> Image.Image:
        """Render frame with symbols shifting left/right to make space."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2
        symbol_center_y = center_y

        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = self._get_unicode_font(symbol_size)

        hi = min(insert_pos, max(0, len(sequence) - 1))
        self._draw_position_slots_unicode(
            draw, slot_count, current_start_x, spacing, center_y, symbol_size, hi
        )
        self._draw_add_candidate_panel(draw, symbol_size)

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
            self._draw_symbol(draw, symbol, int(current_x), symbol_center_y, symbol_size, color_rgb, font)

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
        next_start_x: int,
        slot_count: int,
    ) -> Image.Image:
        """Render frame with new symbol fading in above the gap."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2
        symbol_center_y = center_y

        # Create base image
        img = Image.new('RGB', (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = self._get_unicode_font(symbol_size)

        hi = min(insert_pos, max(0, slot_count - 1))
        self._draw_position_slots_unicode(
            draw, slot_count, current_start_x, spacing, center_y, symbol_size, hi
        )
        self._draw_add_candidate_panel(draw, symbol_size)

        if is_boundary:
            # Boundary insertion: sequence stays in place
            for i, (symbol, color_name) in enumerate(sequence):
                shift = 1 if insert_pos == 0 else 0
                x = current_start_x + (i + shift) * spacing
                color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
                self._draw_symbol(draw, symbol, x, symbol_center_y, symbol_size, color_rgb, font)
            
            # Calculate where new symbol will appear
            if insert_pos == 0:
                x = current_start_x
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
                self._draw_symbol(draw, symbol, x, symbol_center_y, symbol_size, color_rgb, font)
            
            # New symbol appears in the gap
            x = next_start_x + insert_pos * spacing

        # Calculate new symbol position above the line
        new_symbol_y = symbol_center_y - symbol_size

        # Create overlay for fading symbol
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Draw new symbol with alpha
        alpha = int(255 * fade_progress)
        rgba_color = (*new_color, alpha)

        fit_font, bbox = self._fit_symbol_font(
            overlay_draw, new_symbol, font, max(12, symbol_size - 12), max(12, symbol_size - 12)
        )
        text_x = int(round(x - (bbox[0] + bbox[2]) / 2))
        text_y = int(round(new_symbol_y - (bbox[1] + bbox[3]) / 2))
        dx, dy = self._get_optical_center_offset(new_symbol, fit_font)
        text_x += dx
        text_y += dy

        overlay_draw.text((text_x, text_y), new_symbol, fill=rgba_color, font=fit_font)

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
        next_start_x: int,
        slot_count: int,
    ) -> Image.Image:
        """Render frame with symbol sliding down into position."""
        width, height = self.config.image_size
        symbol_size = self.config.symbol_size
        spacing = symbol_size + 20
        center_y = height // 2
        symbol_center_y = center_y

        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        font = self._get_unicode_font(symbol_size)

        hi = min(insert_pos, max(0, slot_count - 1))
        self._draw_position_slots_unicode(
            draw, slot_count, current_start_x, spacing, center_y, symbol_size, hi
        )
        self._draw_add_candidate_panel(draw, symbol_size)

        if is_boundary:
            # Boundary insertion: sequence stays in place
            for i, (symbol, color_name) in enumerate(sequence):
                shift = 1 if insert_pos == 0 else 0
                x = current_start_x + (i + shift) * spacing
                color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
                self._draw_symbol(draw, symbol, x, symbol_center_y, symbol_size, color_rgb, font)
            
            # Calculate where new symbol slides down
            if insert_pos == 0:
                x = current_start_x
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
                self._draw_symbol(draw, symbol, x, symbol_center_y, symbol_size, color_rgb, font)
            
            x = next_start_x + insert_pos * spacing

        # Draw new symbol sliding down
        initial_y = center_y - symbol_size
        target_y = symbol_center_y
        new_symbol_y = int(initial_y + (target_y - initial_y) * slide_progress)

        self._draw_symbol(draw, new_symbol, x, new_symbol_y, symbol_size, new_color, font)

        return img

    # ══════════════════════════════════════════════════════════════════════════
    #  METADATA BUILDING
    # ══════════════════════════════════════════════════════════════════════════
    
    def _build_objects_metadata(
        self,
        initial_sequence: List[Tuple[str, str]],
        final_sequence: List[Tuple[str, str]],
        insert_position: int,
        insert_symbol: str,
        insert_color_name: str
    ) -> dict:
        """
        Build object-centric metadata for symbol insert task.
        
        Args:
            initial_sequence: Initial sequence of (symbol, color_name) tuples
            final_sequence: Final sequence after insertion
            insert_position: 0-indexed position where symbol is inserted
            insert_symbol: Symbol that was inserted
            insert_color_name: Color name of inserted symbol
            
        Returns:
            Dictionary with object-centric metadata
        """
        from typing import Dict, Any
        from .config import ALL_COLOR_NAMES
        
        # Create objects for each symbol in the final sequence
        objects = []
        for i, (symbol, color_name) in enumerate(final_sequence):
            color_rgb = ALL_COLOR_NAMES.get(color_name, (0, 0, 0))
            is_inserted = (i == insert_position)
            
            obj = {
                "symbol": f"symbol_{i}",
                "index": i,
                "slot_index": i,
                "symbol_char": symbol,
                "color_name": color_name,
                "color_rgb": list(color_rgb),
                "is_inserted": is_inserted,
                "is_operation_target": is_inserted,
            }
            
            # Add initial position information
            if is_inserted:
                # This is the newly inserted symbol
                obj["initial_index"] = None
            else:
                # Find position in initial sequence
                if i < insert_position:
                    initial_index = i
                else:
                    initial_index = i - 1
                obj["initial_index"] = initial_index
            
            objects.append(obj)
        
        # Build task-specific metadata
        optimized_task_data = {
            "initial_sequence_length": len(initial_sequence),
            "final_sequence_length": len(final_sequence),
            "insert_position": insert_position,
            "insert_symbol": insert_symbol,
            "insert_color_name": insert_color_name,
            "insert_color_rgb": list(ALL_COLOR_NAMES.get(insert_color_name, (0, 0, 0))),
            "objects": objects
        }
        
        return optimized_task_data
