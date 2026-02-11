---
title: Cookie Cutter Maker
emoji: 🍪
colorFrom: orange
colorTo: yellow
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# Cookie Cutter Maker

Turn any image into a 3D-printable cookie cutter or cylinder seal!

A web app that converts 2D images into STL files ready for 3D printing.

## Features

### Relief Embossing
- Creates cookie stamps with embossed designs from image brightness
- Light areas = raised, dark areas = recessed (or invert)
- Best for photos, characters, logos

### Outline Only
- Generates cookie cutters from silhouettes
- Creates just the cutting edge shape
- Best for simple shapes (stars, hearts, gingerbread men)

### Cylinder Seals
- Creates rollable stamps like ancient Sumerian seals
- Image wraps around a hollow cylinder
- Roll to imprint repeating patterns

## Installation (Local)

```bash
# Clone the repo
git clone https://github.com/yourusername/cookie-cutter-maker.git
cd cookie-cutter-maker

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open http://localhost:7860 in your browser.

## Usage

1. **Choose a mode**: Relief Embossing, Outline Only, or Cylinder Seal
2. **Upload an image**: PNG, JPG, or images with transparent backgrounds
3. **Adjust settings**: Size, depth, resolution, etc.
4. **Generate**: Click the button to create your model
5. **Download STL**: Save the file for 3D printing

## Tips for Best Results

### Image Selection
- **Relief Embossing**: Works with any image - photos, logos, characters
- **Outline Only**: Use simple silhouettes with clear edges
- **Cylinder Seals**: Patterns that tile horizontally work best

### 3D Printing
- Use **food-safe filament** (PLA, PETG) if using with actual food
- Print with **0.2mm layer height** for good detail
- **100% infill** makes the cutter more durable
- Cylinder seals: print standing up for best surface finish

## How It Works

### Relief Embossing
1. Image converted to grayscale heightmap
2. Brightness mapped to surface height
3. Circular disc with rim created
4. Exported as watertight mesh

### Outline Only
1. Image converted to binary mask
2. Contours extracted and simplified
3. Extruded into 3D walls with cutting edge
4. Exported as manifold mesh

### Cylinder Seals
1. Image wrapped around cylinder coordinates
2. Brightness displaces outer surface
3. Inner surface maintains wall thickness
4. Top/bottom rims stitched for watertight mesh

## Command Line Usage

```python
from cookie_cutter import generate_relief_cookie_cutter, generate_cylinder_seal
import cv2

# Relief cookie cutter
image = cv2.imread("my_image.png")
model_path, preview, stats = generate_relief_cookie_cutter(
    image=image,
    diameter_mm=80,
    relief_depth=2.0,
    output_format="stl"
)

# Cylinder seal
model_path, preview, stats = generate_cylinder_seal(
    image=image,
    outer_radius=20,
    height=60,
    max_displacement=2.0,
    output_format="stl"
)
```

## Requirements

- Python 3.8+
- OpenCV
- NumPy
- SciPy
- Gradio
- Pillow

## License

MIT License - feel free to use, modify, and share!

## Acknowledgments

Inspired by cookie makers everywhere and ancient Sumerian scribes who rolled their stories into clay.
