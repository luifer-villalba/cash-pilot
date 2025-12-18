# File: scripts/generate_favicons.py
"""Generate PNG favicons from SVG using Pillow."""

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ Pillow not installed. Run: pip install -e .[dev]")
    exit(1)


def get_system_font(size):
    """Try to get a system font, fallback to default if unavailable."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
    ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except (FileNotFoundError, OSError):
            continue

    # Fallback to default font
    return ImageFont.load_default()


def create_favicon(size, output_path):
    """Create a CP logo favicon at the specified size."""
    # Create image with gradient-like blue background
    img = Image.new("RGB", (size, size), color="#3b82f6")
    draw = ImageDraw.Draw(img)

    # Draw a simple square background; any corner rounding will be handled by browser rendering

    # Draw "CP" text
    font_size = int(size * 0.52)
    font = get_system_font(font_size)

    # Calculate text position (center)
    text = "CP"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2
    y = (size - text_height) // 2 - int(size * 0.08)  # Adjust vertical alignment

    # Draw white text
    draw.text((x, y), text, fill="white", font=font)

    # Save
    img.save(output_path, "PNG")
    print(f"   ✅ {output_path}")


def main():
    """Generate all favicon sizes."""
    # Get absolute path to static directory
    script_dir = Path(__file__).parent.parent.parent.parent
    static_dir = script_dir / "static"

    # Ensure static directory exists
    static_dir.mkdir(parents=True, exist_ok=True)

    # Generate favicons with absolute paths
    create_favicon(16, str(static_dir / "favicon-16x16.png"))
    create_favicon(32, str(static_dir / "favicon-32x32.png"))
    create_favicon(180, str(static_dir / "apple-touch-icon.png"))

    print("\n✅ All favicons generated!")


if __name__ == "__main__":
    main()
