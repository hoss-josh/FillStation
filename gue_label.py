from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def create_gue_label(percentage, initials):
    # Timestamp for record keeping
    timestamp = datetime.now()
    # Paths for external files
    template_path = "data/AnalysisTape4__96185.webp"
    output_path = f"labels/filled_label_{initials}_{timestamp}.png"

    # Load the background label template
    label = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(label)

    # Try to load custom fonts, fallback to default if not found
    try:
        font_large = ImageFont.truetype("Arial.ttf", 120)
        font_small = ImageFont.truetype("Arial.ttf", 40)
    except IOError:
        print("⚠️ Custom font not found, using default font.")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Today's date in YYYY-MM-DD format
    today = datetime.today().strftime('%Y-%m-%d')

    # Coordinates - adjust these for your template
    percent_position = (label.width - 260, label.height // 2 + 20)
    initials_position = (400, label.height - 110)
    date_position = (label.width - 380, label.height - 110)

    # Draw percentage in large font
    draw.text(percent_position, f"{percentage}", fill="black", font=font_large, anchor="mm")

    # Draw initials and today's date in small font
    draw.text(initials_position, initials, fill="black", font=font_small, anchor="lm")
    draw.text(date_position, today, fill="black", font=font_small, anchor="lm")

    # Show the label (used for testing)
    # label.show()

    # Save the label
    label.save(output_path)
    label.close()
    print(f"✅ Label created at {output_path}")

    return output_path

# ------------------------------
# User input section with guardrails
# ------------------------------
def get_valid_initials():
    while True:
        initials = input("Enter your initials (1-3 letters, e.g. JD): ").strip().upper()
        if 1 <= len(initials) <= 3 and initials.isalpha():
            return initials
        print("❌ Invalid initials. Please enter 1 to 3 alphabetic characters only.")
