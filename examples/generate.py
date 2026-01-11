#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        SYMBOL INSERT TASK GENERATION                          ║
║                                                                               ║
║  Generate symbol insertion tasks for visual reasoning.                        ║
║  Task: Insert a symbol at a specific position in a sequence.                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python examples/generate.py --num-samples 100
    python examples/generate.py --num-samples 1000 --symbol-set letters
    python examples/generate.py --num-samples 500 --output data/symbols --seed 42
"""

import argparse
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import OutputWriter
from src import TaskGenerator, TaskConfig


def main():
    parser = argparse.ArgumentParser(
        description="Generate symbol insertion task dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate 100 samples with geometric shapes (default)
    python examples/generate.py --num-samples 100

    # Generate 1000 samples with letters
    python examples/generate.py --num-samples 1000 --symbol-set letters

    # Generate 500 samples without videos (faster)
    python examples/generate.py --num-samples 500 --no-videos

    # Generate with specific seed for reproducibility
    python examples/generate.py --num-samples 200 --seed 42
        """
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        required=True,
        help="Number of symbol insertion task samples to generate"
    )
    parser.add_argument(
        "--symbol-set",
        type=str,
        default="shapes",
        choices=["shapes", "letters", "numbers", "mixed"],
        help="Symbol set to use (default: shapes)"
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=4,
        help="Minimum sequence length (default: 4)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=8,
        help="Maximum sequence length (default: 8)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/questions",
        help="Output directory (default: data/questions)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-videos",
        action="store_true",
        help="Disable video generation (faster)"
    )

    args = parser.parse_args()

    symbol_set_names = {
        "shapes": "geometric shapes",
        "letters": "letters A-Z",
        "numbers": "numbers 0-9",
        "mixed": "mixed symbols"
    }
    symbol_desc = symbol_set_names[args.symbol_set]

    print(f"🎯 Generating {args.num_samples} symbol insertion tasks...")
    print(f"   Symbol set: {symbol_desc}")
    print(f"   Sequence length: {args.min_length}-{args.max_length}")
    print(f"   Videos: {'disabled' if args.no_videos else 'enabled'}")
    print()

    # Configure symbol insertion task generation
    config = TaskConfig(
        num_samples=args.num_samples,
        random_seed=args.seed,
        output_dir=Path(args.output),
        generate_videos=not args.no_videos,
        symbol_set=args.symbol_set,
        min_sequence_length=args.min_length,
        max_sequence_length=args.max_length,
    )

    # Generate tasks
    generator = TaskGenerator(config)
    tasks = generator.generate_dataset()

    # Write to disk
    writer = OutputWriter(Path(args.output))
    writer.write_dataset(tasks)

    print(f"\n✅ Done! Generated {len(tasks)} tasks in {args.output}/{config.domain}_task/")


if __name__ == "__main__":
    main()
