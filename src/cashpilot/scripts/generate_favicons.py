# File: scripts/generate_favicons.py
"""Generate PNG favicons from SVG using Pillow."""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ Pillow not installed. Run: pip install -e .[dev]")
    exit(1)


def create_favicon(size, output_path):
    """Create a CP logo favicon at the specified size."""
    # Create image with gradient-like blue background
    img = Image.new('RGB', (size, size), color='#3b82f6')
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle (simulate rounded corners)
    corner_radius = int(size * 0.22)  # 22% radius like SVG

    # Simple approach: draw a blue square (corners will be covered by antialiasing in browser)

    # Draw "CP" text
    try:
        # Try to use a system font
        font_size = int(size * 0.52)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()

    # Calculate text position (center)
    text = "CP"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2
    y = (size - text_height) // 2 - int(size * 0.08)  # Adjust vertical alignment

    # Draw white text
    draw.text((x, y), text, fill='white', font=font)

    # Save
    img.save(output_path, 'PNG')
    print(f"   ✅ {output_path}")


# Generate favicons
create_favicon(16, 'static/favicon-16x16.png')
create_favicon(32, 'static/favicon-32x32.png')
create_favicon(180, 'static/apple-touch-icon.png')

print("\n✅ All favicons generated!")