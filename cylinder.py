import numpy as np
import trimesh
from PIL import Image, ImageDraw
import io

def generate_test_pattern(width=720, height=360):
    """Generates a synthetic 'cuneiform-like' test pattern."""
    img = Image.new('L', (width, height), color=255) # White background
    draw = ImageDraw.Draw(img)
    
    # Draw some random "wedge" shapes (simple triangles)
    # to simulate a high-contrast seal impression
    for _ in range(50):
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        w = np.random.randint(20, 50)
        h = np.random.randint(10, 30)
        # Draw a black triangle (deep cut)
        draw.polygon([(x, y), (x + w, y + h//2), (x, y + h)], fill=0)
        
    # Add a "rim" line at top and bottom
    draw.line([(0, 10), (width, 10)], fill=0, width=5)
    draw.line([(0, height-10), (width, height-10)], fill=0, width=5)
    
    return img

def create_seal_sleeve(
    image_input, 
    base_radius=20.0, 
    wall_thickness=3.0, # How thick the plastic is
    max_displacement=2.0, 
    height=40.0,
    invert=True
):
    # 1. Load Image
    if isinstance(image_input, str):
        img = Image.open(image_input).convert('L')
    else:
        img = image_input # Assume it's a PIL object already

    # Resize for resolution control
    target_width = 720 
    aspect_ratio = img.height / img.width
    target_height = int(target_width * aspect_ratio)
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    data = np.array(img) / 255.0
    if invert:
        data = 1.0 - data

    rows, cols = data.shape
    num_verts_per_layer = rows * cols

    # 2. Setup Grids
    theta = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    z = np.linspace(0, height, rows)
    theta_grid, z_grid = np.meshgrid(theta, z)

    # 3. Define Outer Surface (Displaced)
    r_outer = base_radius + (data * max_displacement)
    x_outer = r_outer * np.cos(theta_grid)
    y_outer = r_outer * np.sin(theta_grid)
    z_outer = z_grid

    # 4. Define Inner Surface (Smooth Cylinder)
    # The inner radius is constant
    r_inner = np.full_like(r_outer, base_radius - wall_thickness)
    x_inner = r_inner * np.cos(theta_grid)
    y_inner = r_inner * np.sin(theta_grid)
    z_inner = z_grid

    # 5. Combine Vertices
    # Stack outer coordinates, then inner coordinates
    verts_outer = np.column_stack((x_outer.flatten(), y_outer.flatten(), z_outer.flatten()))
    verts_inner = np.column_stack((x_inner.flatten(), y_inner.flatten(), z_inner.flatten()))
    vertices = np.vstack((verts_outer, verts_inner))

    # 6. Generate Topology (Faces)
    faces = []
    
    # Grid indices helper
    indices = np.arange(rows * cols).reshape((rows, cols))
    offset = num_verts_per_layer # Offset to get to the inner layer vertices

    for r in range(rows - 1):
        for c in range(cols):
            # Wrap columns (modulo)
            c_next = (c + 1) % cols
            
            # --- Outer Surface (Standard Grid) ---
            p1 = indices[r, c]
            p2 = indices[r + 1, c]
            p3 = indices[r, c_next]
            p4 = indices[r + 1, c_next]
            
            # CCW Winding for outer
            faces.append([p1, p2, p3])
            faces.append([p3, p2, p4])

            # --- Inner Surface (Standard Grid, Reversed Winding) ---
            # We add 'offset' to access the inner vertices
            i1 = p1 + offset
            i2 = p2 + offset
            i3 = p3 + offset
            i4 = p4 + offset
            
            # CW Winding for inner (so normals point inward towards the hole center)
            faces.append([i1, i3, i2])
            faces.append([i3, i4, i2])

    # 7. Stitch the Rims (Top and Bottom) to make it watertight
    # We must connect the top row of Outer to the top row of Inner
    # And the bottom row of Outer to the bottom row of Inner
    
    for c in range(cols):
        c_next = (c + 1) % cols
        
        # --- Top Rim (Row 0) ---
        o1 = indices[0, c]           # Outer current
        o2 = indices[0, c_next]      # Outer next
        i1 = o1 + offset             # Inner current
        i2 = o2 + offset             # Inner next
        
        # Connect outer to inner (filling the gap)
        faces.append([o1, o2, i1])
        faces.append([o2, i2, i1])
        
        # --- Bottom Rim (Row rows-1) ---
        o3 = indices[rows-1, c]      # Outer current
        o4 = indices[rows-1, c_next] # Outer next
        i3 = o3 + offset             # Inner current
        i4 = o4 + offset             # Inner next
        
        # Connect outer to inner
        # Note winding might need flip depending on perspective, 
        # but trimesh.fix_normals() usually cleans this up.
        faces.append([o3, i3, o4])
        faces.append([o4, i3, i4])

    # Create Mesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    # Final cleanup to ensure normals are pointing correctly for printing
    mesh.fix_normals()
    
    return mesh

# --- MAIN EXECUTION ---

# 1. Generate a "fake" Sumerian image for testing
print("Generating test pattern...")
test_image = generate_test_pattern()

# 2. Convert to Sleeve
print("Converting to mesh...")
mesh = create_seal_sleeve(
    test_image, 
    base_radius=20,     # Outer radius
    wall_thickness=4,   # 4mm thick walls
    height=60
)

# 3. Export
filename = "sumerian_roller_test.stl"
mesh.export(filename)
print(f"Done! Saved to {filename}")

# Optional: Visualize if you have a window manager
# mesh.show()
