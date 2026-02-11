"""
Cookie Cutter Generator Module
Converts 2D images into 3D-printable cookie cutter meshes.
Also generates cylinder seals with embossed designs.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import tempfile
from scipy.ndimage import gaussian_filter

# Try to import rembg for smart background removal
try:
    from rembg import remove as rembg_remove
    from PIL import Image
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# Rodin API integration
import requests
import time
import os

RODIN_API_URL = "https://api.hyper3d.com/api/v2/rodin"
RODIN_STATUS_URL = "https://api.hyper3d.com/api/v2/status"
RODIN_DOWNLOAD_URL = "https://api.hyper3d.com/api/v2/download"


def generate_relief_cookie_cutter(
    image: np.ndarray,
    diameter_mm: float = 80.0,
    base_thickness: float = 3.0,
    relief_depth: float = 2.0,
    rim_height: float = 12.0,
    rim_thickness: float = 1.5,
    resolution: int = 200,
    invert_relief: bool = False,
    output_format: str = "glb"
) -> Tuple[str, np.ndarray, dict]:
    """
    Generate a cookie cutter with embossed relief from image heightmap.

    Args:
        image: Input image (will be converted to grayscale for heightmap)
        diameter_mm: Cookie cutter diameter in mm
        base_thickness: Thickness of the flat base in mm
        relief_depth: Maximum depth of the embossed relief in mm
        rim_height: Height of the cutting rim in mm
        rim_thickness: Thickness of the cutting rim in mm
        resolution: Grid resolution for the mesh
        invert_relief: If True, dark areas are raised (good for dark images on light bg)
        output_format: "glb" or "stl"

    Returns:
        Tuple of (output_path, preview_image, stats_dict)
    """
    # Convert to grayscale
    if len(image.shape) == 3:
        if image.shape[2] == 4:
            # RGBA - use alpha to mask, then grayscale
            gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_RGB2GRAY)
            alpha = image[:, :, 3] / 255.0
            gray = (gray * alpha).astype(np.uint8)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()

    # Resize to resolution
    gray = cv2.resize(gray, (resolution, resolution), interpolation=cv2.INTER_AREA)

    # Normalize to 0-1
    heightmap = gray.astype(float) / 255.0

    if invert_relief:
        heightmap = 1.0 - heightmap

    # Create circular mask
    y, x = np.ogrid[:resolution, :resolution]
    center = resolution / 2
    radius = resolution / 2 - 2
    dist_from_center = np.sqrt((x - center)**2 + (y - center)**2)
    circular_mask = dist_from_center <= radius

    # Apply circular mask to heightmap
    heightmap = heightmap * circular_mask

    # Calculate scale
    scale = diameter_mm / resolution

    # Generate mesh vertices
    vertices = []

    # Top surface with relief (inside the rim)
    for j in range(resolution):
        for i in range(resolution):
            x_mm = (i - center) * scale
            y_mm = (j - center) * scale

            if circular_mask[j, i]:
                # Relief surface
                z_mm = base_thickness + heightmap[j, i] * relief_depth
            else:
                z_mm = 0  # Outside disc

            vertices.append([x_mm, y_mm, z_mm])

    # Bottom surface (flat)
    for j in range(resolution):
        for i in range(resolution):
            x_mm = (i - center) * scale
            y_mm = (j - center) * scale
            vertices.append([x_mm, y_mm, 0])

    vertices = np.array(vertices, dtype=np.float32)

    # Generate faces for top and bottom surfaces
    faces = []

    # Top surface faces
    for j in range(resolution - 1):
        for i in range(resolution - 1):
            idx = j * resolution + i

            # Check if all 4 corners are inside the disc
            if (circular_mask[j, i] and circular_mask[j, i+1] and
                circular_mask[j+1, i] and circular_mask[j+1, i+1]):
                # Two triangles for this quad
                faces.append([idx, idx + 1, idx + resolution])
                faces.append([idx + 1, idx + resolution + 1, idx + resolution])

    # Bottom surface faces (offset by resolution^2)
    offset = resolution * resolution
    for j in range(resolution - 1):
        for i in range(resolution - 1):
            idx = j * resolution + i

            if (circular_mask[j, i] and circular_mask[j, i+1] and
                circular_mask[j+1, i] and circular_mask[j+1, i+1]):
                # Reverse winding for bottom
                faces.append([offset + idx, offset + idx + resolution, offset + idx + 1])
                faces.append([offset + idx + 1, offset + idx + resolution, offset + idx + resolution + 1])

    # Add rim vertices and faces
    rim_segments = 64
    rim_inner_radius = diameter_mm / 2 - rim_thickness
    rim_outer_radius = diameter_mm / 2

    rim_start_idx = len(vertices)
    rim_vertices = []

    for i in range(rim_segments):
        angle = 2 * np.pi * i / rim_segments
        cos_a, sin_a = np.cos(angle), np.sin(angle)

        # Inner bottom
        rim_vertices.append([rim_inner_radius * cos_a, rim_inner_radius * sin_a, base_thickness])
        # Inner top
        rim_vertices.append([rim_inner_radius * cos_a, rim_inner_radius * sin_a, rim_height])
        # Outer top
        rim_vertices.append([rim_outer_radius * cos_a, rim_outer_radius * sin_a, rim_height])
        # Outer bottom (cutting edge)
        rim_vertices.append([rim_outer_radius * cos_a, rim_outer_radius * sin_a, 0])

    vertices = np.vstack([vertices, np.array(rim_vertices, dtype=np.float32)])

    # Rim faces
    for i in range(rim_segments):
        base = rim_start_idx + i * 4
        next_base = rim_start_idx + ((i + 1) % rim_segments) * 4

        # Inner wall
        faces.append([base, base + 1, next_base])
        faces.append([next_base, base + 1, next_base + 1])

        # Top
        faces.append([base + 1, base + 2, next_base + 1])
        faces.append([next_base + 1, base + 2, next_base + 2])

        # Outer wall
        faces.append([base + 2, base + 3, next_base + 2])
        faces.append([next_base + 2, base + 3, next_base + 3])

        # Bottom (connects to disc edge)
        faces.append([base + 3, base, next_base + 3])
        faces.append([next_base + 3, base, next_base])

    faces = np.array(faces, dtype=np.uint32)

    # Create preview image
    preview = cv2.applyColorMap((heightmap * 255).astype(np.uint8), cv2.COLORMAP_VIRIDIS)
    preview[~circular_mask] = [40, 40, 40]  # Dark background outside disc

    # Draw rim indicator
    cv2.circle(preview, (resolution//2, resolution//2), int(radius), (255, 255, 255), 2)

    # Write output file
    with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as f:
        output_path = f.name

    if output_format == "stl":
        write_stl(output_path, vertices, faces)
    else:
        write_glb(output_path, vertices, faces)

    stats = {
        "diameter_mm": diameter_mm,
        "base_thickness_mm": base_thickness,
        "relief_depth_mm": relief_depth,
        "rim_height_mm": rim_height,
        "vertices": len(vertices),
        "faces": len(faces),
        "resolution": resolution
    }

    return output_path, preview, stats


def generate_cylinder_seal(
    image: np.ndarray,
    outer_radius: float = 20.0,
    wall_thickness: float = 4.0,
    height: float = 60.0,
    max_displacement: float = 2.0,
    resolution: int = 360,
    smoothing: float = 1.0,
    invert: bool = True,
    constant_wall: bool = True,
    output_format: str = "glb"
) -> Tuple[str, np.ndarray, dict]:
    """
    Generate a cylinder seal with embossed/carved design from image.

    The seal is a hollow cylinder where the outer surface is displaced
    based on image brightness, creating a rollable stamp that imprints
    the design (like ancient Sumerian cylinder seals).

    Args:
        image: Input image (will be converted to grayscale for heightmap)
        outer_radius: Outer radius of the cylinder in mm
        wall_thickness: Wall thickness in mm
        height: Height of the cylinder in mm
        max_displacement: Maximum displacement depth in mm
        resolution: Circumference resolution (number of points around)
        smoothing: Gaussian blur sigma for smoothing (0 = no smoothing)
        invert: If True, dark areas are carved in (typical for seals)
        constant_wall: If True, inner surface follows outer displacement
                      to maintain constant wall thickness
        output_format: "glb" or "stl"

    Returns:
        Tuple of (output_path, preview_image, stats_dict)
    """
    # Convert to grayscale
    if len(image.shape) == 3:
        if image.shape[2] == 4:
            gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_RGB2GRAY)
            alpha = image[:, :, 3] / 255.0
            gray = (gray * alpha).astype(np.uint8)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()

    # Calculate target dimensions based on cylinder geometry
    # Circumference = 2 * pi * radius, so aspect ratio should match
    circumference = 2 * np.pi * outer_radius
    target_cols = resolution  # Points around circumference
    target_rows = int(resolution * (height / circumference))
    target_rows = max(target_rows, 50)  # Minimum height resolution

    # Resize image to match cylinder proportions
    gray = cv2.resize(gray, (target_cols, target_rows), interpolation=cv2.INTER_AREA)

    # Normalize to 0-1
    heightmap = gray.astype(float) / 255.0

    if invert:
        heightmap = 1.0 - heightmap

    # Apply smoothing
    if smoothing > 0:
        heightmap = gaussian_filter(heightmap, sigma=smoothing)

    rows, cols = heightmap.shape

    # Create coordinate grids
    theta = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    z = np.linspace(0, height, rows)
    theta_grid, z_grid = np.meshgrid(theta, z)

    # Outer surface with displacement
    r_outer = outer_radius + (heightmap * max_displacement)
    x_outer = r_outer * np.cos(theta_grid)
    y_outer = r_outer * np.sin(theta_grid)
    z_outer = z_grid

    # Inner surface
    if constant_wall:
        # Inner follows outer to maintain wall thickness
        r_inner = r_outer - wall_thickness
    else:
        # Inner is smooth cylinder (variable wall thickness)
        r_inner = np.full_like(r_outer, outer_radius - wall_thickness)

    x_inner = r_inner * np.cos(theta_grid)
    y_inner = r_inner * np.sin(theta_grid)
    z_inner = z_grid

    # Combine vertices: outer first, then inner
    verts_outer = np.column_stack((x_outer.flatten(), y_outer.flatten(), z_outer.flatten()))
    verts_inner = np.column_stack((x_inner.flatten(), y_inner.flatten(), z_inner.flatten()))
    vertices = np.vstack((verts_outer, verts_inner)).astype(np.float32)

    num_verts_per_layer = rows * cols
    offset = num_verts_per_layer

    # Generate faces
    faces = []
    indices = np.arange(rows * cols).reshape((rows, cols))

    for r in range(rows - 1):
        for c in range(cols):
            c_next = (c + 1) % cols

            # Outer surface (CCW winding for outward normals)
            p1 = indices[r, c]
            p2 = indices[r + 1, c]
            p3 = indices[r, c_next]
            p4 = indices[r + 1, c_next]

            faces.append([p1, p2, p3])
            faces.append([p3, p2, p4])

            # Inner surface (CW winding for inward normals)
            i1 = p1 + offset
            i2 = p2 + offset
            i3 = p3 + offset
            i4 = p4 + offset

            faces.append([i1, i3, i2])
            faces.append([i3, i4, i2])

    # Stitch top and bottom rims to make watertight
    for c in range(cols):
        c_next = (c + 1) % cols

        # Top rim (row 0) - connects outer to inner
        o1 = indices[0, c]
        o2 = indices[0, c_next]
        i1 = o1 + offset
        i2 = o2 + offset

        faces.append([o1, o2, i1])
        faces.append([o2, i2, i1])

        # Bottom rim (row rows-1)
        o3 = indices[rows-1, c]
        o4 = indices[rows-1, c_next]
        i3 = o3 + offset
        i4 = o4 + offset

        faces.append([o3, i3, o4])
        faces.append([o4, i3, i4])

    faces = np.array(faces, dtype=np.uint32)

    # Create preview image (unwrapped cylinder texture with displacement visualization)
    preview = cv2.applyColorMap((heightmap * 255).astype(np.uint8), cv2.COLORMAP_VIRIDIS)
    # Scale preview to reasonable size
    preview_height = 200
    preview_width = int(preview_height * cols / rows)
    preview = cv2.resize(preview, (preview_width, preview_height))

    # Add border to indicate it wraps around
    cv2.rectangle(preview, (0, 0), (preview_width-1, preview_height-1), (255, 255, 255), 2)

    # Write output file
    with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as f:
        output_path = f.name

    if output_format == "stl":
        write_stl(output_path, vertices, faces)
    else:
        write_glb(output_path, vertices, faces)

    stats = {
        "outer_radius_mm": outer_radius,
        "inner_radius_mm": round(outer_radius - wall_thickness, 1),
        "wall_thickness_mm": wall_thickness,
        "height_mm": height,
        "max_displacement_mm": max_displacement,
        "circumference_mm": round(2 * np.pi * outer_radius, 1),
        "resolution": f"{cols}x{rows}",
        "vertices": len(vertices),
        "faces": len(faces),
        "constant_wall": constant_wall
    }

    return output_path, preview, stats


def generate_with_rodin(
    image: np.ndarray,
    prompt: str = "Cookie cutter stamp with this design embossed in relief on a circular disc",
    tier: str = "Detail",
    api_key: str = None,
    output_dir: str = None
) -> Tuple[Optional[str], Optional[str], dict]:
    """
    Generate a 3D cookie cutter using Rodin API with image + prompt.

    Args:
        image: Input image as numpy array
        prompt: Text prompt describing the desired output
        tier: Quality tier (Sketch, Regular, Detail, Gen-2)
        api_key: Rodin API key (defaults to env var or 'vibecoding')
        output_dir: Directory to save output files

    Returns:
        Tuple of (glb_path, preview_path, stats_dict)
    """
    api_key = api_key or os.environ.get("HYPER3D_API_KEY", "vibecoding")

    headers = {"Authorization": f"Bearer {api_key}"}

    # Convert numpy array to PNG bytes
    from PIL import Image as PILImage
    import io

    if len(image.shape) == 2:
        pil_img = PILImage.fromarray(image, mode='L').convert('RGB')
    elif image.shape[2] == 4:
        pil_img = PILImage.fromarray(image, mode='RGBA')
    else:
        pil_img = PILImage.fromarray(image, mode='RGB')

    img_buffer = io.BytesIO()
    pil_img.save(img_buffer, format='PNG')
    img_bytes = img_buffer.getvalue()

    # Submit task
    files = [('images', ('input.png', img_bytes, 'image/png'))]
    data = {
        "tier": tier,
        "geometry_file_format": "glb",
        "material": "PBR",
        "quality": "high" if tier in ["Detail", "Gen-2"] else "medium",
        "mesh_mode": "Quad",
        "prompt": prompt
    }

    response = requests.post(RODIN_API_URL, headers=headers, files=files, data=data, timeout=300)
    response.raise_for_status()
    result = response.json()

    subscription_key = result.get('jobs', {}).get('subscription_key')
    task_uuid = result.get('uuid')

    if not subscription_key:
        raise ValueError("Failed to get subscription key from Rodin API")

    # Poll for completion
    max_attempts = 360  # 30 minutes max (360 * 5 seconds)
    for i in range(max_attempts):
        status_response = requests.post(
            RODIN_STATUS_URL,
            headers=headers,
            json={"subscription_key": subscription_key},
            timeout=30
        )
        status_data = status_response.json()

        jobs = status_data.get('jobs', [])
        done = sum(1 for j in jobs if j.get('status') in ['Done', 'Completed'])
        total = len(jobs) if jobs else 6

        # Print progress for debugging
        print(f"Rodin progress: {done}/{total} jobs complete (attempt {i+1})")

        if done == total and total > 0:
            break

        time.sleep(5)
    else:
        raise TimeoutError(f"Rodin generation timed out after {max_attempts * 5 / 60:.0f} minutes")

    # Get download links
    download_response = requests.post(
        RODIN_DOWNLOAD_URL,
        headers=headers,
        json={"task_uuid": task_uuid},
        timeout=30
    )
    download_data = download_response.json()

    # Download files
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    os.makedirs(output_dir, exist_ok=True)

    glb_path = None
    preview_path = None

    for item in download_data.get('list', []):
        url = item.get('url')
        name = item.get('name')
        if url and name:
            file_response = requests.get(url, timeout=60)
            file_path = os.path.join(output_dir, name)
            with open(file_path, 'wb') as f:
                f.write(file_response.content)

            if name.endswith('.glb'):
                glb_path = file_path
            elif name.endswith('.webp') or name.endswith('.png'):
                preview_path = file_path

    stats = {
        "task_uuid": task_uuid,
        "tier": tier,
        "prompt": prompt,
        "files_generated": len(download_data.get('list', []))
    }

    return glb_path, preview_path, stats


def remove_background(image: np.ndarray) -> np.ndarray:
    """
    Remove background using rembg (neural network-based).
    Returns RGBA image with transparent background.
    """
    if not REMBG_AVAILABLE:
        raise RuntimeError("rembg is not installed. Run: pip install rembg")

    # Convert numpy array to PIL Image
    if len(image.shape) == 2:
        pil_img = Image.fromarray(image, mode='L').convert('RGB')
    elif image.shape[2] == 4:
        pil_img = Image.fromarray(image, mode='RGBA').convert('RGB')
    else:
        pil_img = Image.fromarray(image, mode='RGB')

    # Remove background
    result = rembg_remove(pil_img)

    # Convert back to numpy array
    return np.array(result)


def load_and_preprocess(image: np.ndarray, target_size: int = 200,
                        invert: bool = False, use_edges: bool = False,
                        threshold: int = 0, smart_remove_bg: bool = False) -> np.ndarray:
    """
    Load image and create binary mask from silhouette.

    Args:
        image: Input image (RGB, RGBA, or grayscale)
        target_size: Target size for processing
        invert: If True, invert the mask (for dark shapes on light backgrounds)
        use_edges: If True, use edge detection instead of thresholding
        threshold: Manual threshold value (0 = auto/Otsu)
        smart_remove_bg: If True, use rembg neural network for background removal
    """
    if image is None:
        raise ValueError("Invalid image")

    # Smart background removal using rembg
    if smart_remove_bg and REMBG_AVAILABLE:
        image = remove_background(image)

    # Handle different input formats
    if len(image.shape) == 2:
        # Grayscale
        gray = image
        has_alpha = False
    elif image.shape[2] == 4:
        # RGBA - use alpha channel if it has meaningful data
        alpha = image[:, :, 3]
        # Check if alpha channel is actually used (not all 255 or all 0)
        if alpha.min() < 250 and alpha.max() > 5:
            mask = alpha
            has_alpha = True
        else:
            gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_RGB2GRAY)
            has_alpha = False
    else:
        # RGB
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        has_alpha = False

    if not has_alpha:
        if use_edges:
            # Use Canny edge detection for complex images
            edges = cv2.Canny(gray, 50, 150)
            # Dilate edges to make them thicker
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=2)
            # Fill the shape
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            mask = np.zeros_like(gray)
            if contours:
                # Fill the largest contour
                largest = max(contours, key=cv2.contourArea)
                cv2.fillPoly(mask, [largest], 255)
        else:
            # Standard thresholding
            if threshold > 0:
                _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            else:
                _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Auto-detect if inversion is needed by checking corners
        if not invert:
            corners = [
                mask[0, 0], mask[0, -1],
                mask[-1, 0], mask[-1, -1]
            ]
            # If corners are mostly white, the background is white, so invert
            if np.mean(corners) > 200:
                invert = True

        if invert:
            mask = 255 - mask
    else:
        mask = mask  # Use alpha channel directly

    # Resize maintaining aspect ratio
    h, w = mask.shape
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Clean up the mask
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Ensure binary
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    return mask


def extract_contour(mask: np.ndarray, simplify_epsilon: float = 1.0) -> np.ndarray:
    """Extract and simplify the main contour from binary mask."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError("No contours found in image")

    # Get the largest contour
    main_contour = max(contours, key=cv2.contourArea)

    # Simplify the contour
    epsilon = simplify_epsilon * cv2.arcLength(main_contour, True) / 100
    simplified = cv2.approxPolyDP(main_contour, epsilon, True)

    # Convert to 2D points array
    points = simplified.reshape(-1, 2).astype(float)

    return points


def offset_contour(contour: np.ndarray, offset: float) -> np.ndarray:
    """Offset a contour outward by computing normals."""
    n = len(contour)
    normals = []

    for i in range(n):
        p_prev = contour[(i - 1) % n]
        p_curr = contour[i]
        p_next = contour[(i + 1) % n]

        e1 = p_curr - p_prev
        e2 = p_next - p_curr

        n1 = np.array([-e1[1], e1[0]])
        n2 = np.array([-e2[1], e2[0]])

        n1 = n1 / (np.linalg.norm(n1) + 1e-10)
        n2 = n2 / (np.linalg.norm(n2) + 1e-10)

        avg_normal = n1 + n2
        avg_normal = avg_normal / (np.linalg.norm(avg_normal) + 1e-10)

        normals.append(avg_normal)

    normals = np.array(normals)

    # Check winding order
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += contour[i][0] * contour[j][1]
        area -= contour[j][0] * contour[i][1]

    if area > 0:
        normals = -normals

    return contour + normals * offset


def create_cookie_cutter_mesh(contour: np.ndarray,
                               wall_height: float = 15.0,
                               wall_thickness: float = 1.2,
                               base_height: float = 2.0,
                               scale_mm: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    """Create 3D mesh for cookie cutter from 2D contour."""
    contour = contour * scale_mm
    centroid = contour.mean(axis=0)
    contour = contour - centroid

    n_points = len(contour)
    outer_contour = offset_contour(contour, wall_thickness)

    vertices = []
    faces = []

    # Inner wall vertices
    for x, y in contour:
        vertices.append([x, y, 0])
        vertices.append([x, y, wall_height])

    # Outer wall vertices
    for x, y in outer_contour:
        vertices.append([x, y, base_height])
        vertices.append([x, y, wall_height])

    vertices = np.array(vertices)

    # Inner wall faces
    for i in range(n_points):
        i_next = (i + 1) % n_points
        v0, v1 = i * 2, i * 2 + 1
        v2, v3 = i_next * 2, i_next * 2 + 1
        faces.append([v0, v2, v1])
        faces.append([v1, v2, v3])

    # Outer wall faces
    outer_start = n_points * 2
    for i in range(n_points):
        i_next = (i + 1) % n_points
        v0 = outer_start + i * 2
        v1 = outer_start + i * 2 + 1
        v2 = outer_start + i_next * 2
        v3 = outer_start + i_next * 2 + 1
        faces.append([v0, v1, v2])
        faces.append([v1, v3, v2])

    # Top cap
    for i in range(n_points):
        i_next = (i + 1) % n_points
        inner_top = i * 2 + 1
        inner_top_next = i_next * 2 + 1
        outer_top = outer_start + i * 2 + 1
        outer_top_next = outer_start + i_next * 2 + 1
        faces.append([inner_top, inner_top_next, outer_top])
        faces.append([outer_top, inner_top_next, outer_top_next])

    # Bottom cap
    for i in range(n_points):
        i_next = (i + 1) % n_points
        inner_bottom = i * 2
        inner_bottom_next = i_next * 2
        outer_bottom = outer_start + i * 2
        outer_bottom_next = outer_start + i_next * 2
        faces.append([inner_bottom, outer_bottom, inner_bottom_next])
        faces.append([outer_bottom, outer_bottom_next, inner_bottom_next])

    return vertices, np.array(faces)


def write_stl(filename: str, vertices: np.ndarray, faces: np.ndarray) -> None:
    """Write binary STL file."""
    with open(filename, 'wb') as f:
        f.write(b'\0' * 80)
        f.write(np.uint32(len(faces)).tobytes())

        for face in faces:
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
            edge1, edge2 = v1 - v0, v2 - v0
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm

            f.write(np.float32(normal).tobytes())
            f.write(np.float32(v0).tobytes())
            f.write(np.float32(v1).tobytes())
            f.write(np.float32(v2).tobytes())
            f.write(np.uint16(0).tobytes())


def write_glb(filename: str, vertices: np.ndarray, faces: np.ndarray) -> None:
    """Write GLB file (binary glTF) for 3D viewing."""
    import struct
    import json

    # Prepare vertex data (positions only)
    positions = vertices.astype(np.float32)
    indices = faces.astype(np.uint32).flatten()

    # Calculate bounds
    pos_min = positions.min(axis=0).tolist()
    pos_max = positions.max(axis=0).tolist()

    # Create buffer data
    pos_bytes = positions.tobytes()
    idx_bytes = indices.tobytes()

    # Padding for alignment
    pos_padding = (4 - len(pos_bytes) % 4) % 4
    idx_padding = (4 - len(idx_bytes) % 4) % 4

    buffer_data = idx_bytes + b'\x00' * idx_padding + pos_bytes + b'\x00' * pos_padding

    # glTF JSON
    gltf = {
        "asset": {"version": "2.0", "generator": "Cookie Cutter Maker"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{
            "primitives": [{
                "attributes": {"POSITION": 1},
                "indices": 0,
                "mode": 4
            }]
        }],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5125,  # UNSIGNED_INT
                "count": len(indices),
                "type": "SCALAR"
            },
            {
                "bufferView": 1,
                "componentType": 5126,  # FLOAT
                "count": len(positions),
                "type": "VEC3",
                "min": pos_min,
                "max": pos_max
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(idx_bytes),
                "target": 34963  # ELEMENT_ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": len(idx_bytes) + idx_padding,
                "byteLength": len(pos_bytes),
                "target": 34962  # ARRAY_BUFFER
            }
        ],
        "buffers": [{"byteLength": len(buffer_data)}]
    }

    # Encode JSON
    json_str = json.dumps(gltf, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    json_padding = (4 - len(json_bytes) % 4) % 4
    json_bytes += b' ' * json_padding

    # GLB structure
    glb_length = 12 + 8 + len(json_bytes) + 8 + len(buffer_data)

    with open(filename, 'wb') as f:
        # Header
        f.write(b'glTF')  # magic
        f.write(struct.pack('<I', 2))  # version
        f.write(struct.pack('<I', glb_length))  # length

        # JSON chunk
        f.write(struct.pack('<I', len(json_bytes)))
        f.write(b'JSON')
        f.write(json_bytes)

        # BIN chunk
        f.write(struct.pack('<I', len(buffer_data)))
        f.write(b'BIN\x00')
        f.write(buffer_data)


def create_contour_preview(contour: np.ndarray, outer_contour: np.ndarray,
                           size: int = 400) -> np.ndarray:
    """Create preview image of contours."""
    all_points = np.vstack([contour, outer_contour])
    min_pt = all_points.min(axis=0)
    max_pt = all_points.max(axis=0)

    scale = (size - 40) / max(max_pt - min_pt)
    offset = np.array([20, 20]) - min_pt * scale

    img = np.ones((size, size, 3), dtype=np.uint8) * 255

    inner_pts = (contour * scale + offset).astype(np.int32)
    outer_pts = (outer_contour * scale + offset).astype(np.int32)

    cv2.polylines(img, [inner_pts], True, (255, 100, 100), 2)  # Blue inner
    cv2.polylines(img, [outer_pts], True, (100, 100, 255), 2)  # Red outer

    # Fill between contours for visualization
    cv2.fillPoly(img, [outer_pts], (220, 220, 255))
    cv2.fillPoly(img, [inner_pts], (255, 255, 255))
    cv2.polylines(img, [inner_pts], True, (255, 100, 100), 2)
    cv2.polylines(img, [outer_pts], True, (100, 100, 255), 2)

    return img


def generate_cookie_cutter(
    image: np.ndarray,
    wall_height: float = 15.0,
    wall_thickness: float = 1.2,
    target_size: int = 200,
    simplify: float = 1.0,
    scale_mm: float = 0.5,
    output_format: str = "glb",
    invert: bool = False,
    use_edges: bool = False,
    threshold: int = 0,
    smart_remove_bg: bool = False
) -> Tuple[str, np.ndarray, dict]:
    """
    Main function to generate cookie cutter from image.

    Args:
        image: Input image
        wall_height: Height of cutter walls in mm
        wall_thickness: Thickness of walls in mm
        target_size: Processing resolution
        simplify: Contour simplification factor
        scale_mm: Scale factor for final size
        output_format: "glb" or "stl"
        invert: Invert the mask (for dark shapes on light backgrounds)
        use_edges: Use edge detection (for complex images with backgrounds)
        threshold: Manual threshold (0 = auto)
        smart_remove_bg: Use rembg for smart background removal

    Returns:
        Tuple of (output_path, preview_image, stats_dict)
    """
    # Process image
    mask = load_and_preprocess(image, target_size, invert=invert,
                                use_edges=use_edges, threshold=threshold,
                                smart_remove_bg=smart_remove_bg)
    contour = extract_contour(mask, simplify)

    # Create mesh
    vertices, faces = create_cookie_cutter_mesh(
        contour,
        wall_height=wall_height,
        wall_thickness=wall_thickness,
        scale_mm=scale_mm
    )

    # Create preview
    scaled_contour = (contour - contour.mean(axis=0)) * scale_mm
    outer = offset_contour(scaled_contour, wall_thickness)
    preview = create_contour_preview(scaled_contour, outer)

    # Write output file
    with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as f:
        output_path = f.name

    if output_format == "stl":
        write_stl(output_path, vertices, faces)
    else:
        write_glb(output_path, vertices, faces)

    # Calculate stats
    contour_scaled = scaled_contour
    width = contour_scaled[:, 0].max() - contour_scaled[:, 0].min()
    height = contour_scaled[:, 1].max() - contour_scaled[:, 1].min()

    stats = {
        "contour_points": len(contour),
        "vertices": len(vertices),
        "faces": len(faces),
        "width_mm": round(width, 1),
        "height_mm": round(height, 1),
        "wall_height_mm": wall_height,
        "wall_thickness_mm": wall_thickness
    }

    return output_path, preview, stats
