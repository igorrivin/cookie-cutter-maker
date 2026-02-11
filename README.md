# Cookie Cutter Maker

Turn any image into a 3D-printable cookie cutter!

A simple web app that converts 2D images (silhouettes, logos, characters) into STL files ready for 3D printing.

## Features

- **Easy to use**: Just upload an image and adjust a few sliders
- **3D Preview**: See your cookie cutter in 3D before downloading
- **Customizable**: Adjust size, wall height, and thickness
- **Instant STL download**: Get a print-ready file in seconds

## Installation

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

1. **Upload an image** - PNG with transparent background works best
2. **Adjust settings**:
   - Cookie Size: The maximum width/height in mm
   - Wall Height: How tall the cutting edge is (10-20mm typical)
   - Wall Thickness: Thickness of walls (1.2mm works well)
3. **Generate** - Click the button to create your cutter
4. **Download STL** - Save the file for 3D printing

## Tips for Best Results

### Image Selection
- Use images with **clear, simple shapes**
- **Silhouettes** work better than detailed photos
- PNG files with **transparent backgrounds** are ideal
- Avoid very thin lines or intricate details

### 3D Printing
- Use **food-safe filament** (PLA, PETG) if using with actual food
- Print with **0.2mm layer height** for good detail
- **100% infill** makes the cutter more durable
- Consider printing a separate handle piece

## How It Works

1. The image is converted to a binary mask (silhouette)
2. Contours are extracted and simplified
3. The contour is extruded into 3D walls
4. Inner and outer walls create the cutting edge
5. A manifold mesh is generated and exported as STL/GLB

## Command Line Usage

You can also use the generator directly from Python:

```python
from cookie_cutter import generate_cookie_cutter
import cv2

image = cv2.imread("my_shape.png", cv2.IMREAD_UNCHANGED)
model_path, preview, stats = generate_cookie_cutter(
    image=image,
    wall_height=15.0,
    wall_thickness=1.2,
    cutter_size=80,
    output_format="stl"
)
print(f"Generated: {model_path}")
print(stats)
```

## Requirements

- Python 3.8+
- OpenCV
- NumPy
- Gradio
- Pillow

## License

MIT License - feel free to use, modify, and share!

## Acknowledgments

Inspired by the creativity of cookie makers everywhere who turn their favorite characters and shapes into delicious treats.
