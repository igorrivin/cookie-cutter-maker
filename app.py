#!/usr/bin/env python3
"""
Cookie Cutter Maker - Gradio Web Interface
Turn any image into a 3D-printable cookie cutter!
"""

import gradio as gr
import numpy as np
from pathlib import Path
import tempfile
import os
import cv2

from cookie_cutter import generate_cookie_cutter, generate_relief_cookie_cutter, generate_cylinder_seal


def process_image_relief(
    image,
    diameter: float,
    base_thickness: float,
    relief_depth: float,
    rim_height: float,
    rim_thickness: float,
    resolution: int,
    invert_relief: bool
):
    """Process uploaded image using heightmap relief."""
    if image is None:
        return None, None, "Please upload an image first!"

    try:
        model_path, preview, stats = generate_relief_cookie_cutter(
            image=image,
            diameter_mm=diameter,
            base_thickness=base_thickness,
            relief_depth=relief_depth,
            rim_height=rim_height,
            rim_thickness=rim_thickness,
            resolution=resolution,
            invert_relief=invert_relief,
            output_format="glb"
        )

        stats_text = f"""**Relief Cookie Cutter Generated!**

- Diameter: {stats['diameter_mm']} mm
- Base Thickness: {stats['base_thickness_mm']} mm
- Relief Depth: {stats['relief_depth_mm']} mm
- Rim Height: {stats['rim_height_mm']} mm
- Resolution: {stats['resolution']}x{stats['resolution']}
- Mesh: {stats['vertices']} vertices, {stats['faces']} faces

Ready to download and 3D print!"""

        return model_path, preview, stats_text

    except Exception as e:
        import traceback
        return None, None, f"Error: {str(e)}\n\n{traceback.format_exc()}"


def download_relief_stl(
    image,
    diameter: float,
    base_thickness: float,
    relief_depth: float,
    rim_height: float,
    rim_thickness: float,
    resolution: int,
    invert_relief: bool
):
    """Generate STL file for relief cookie cutter."""
    if image is None:
        return None

    try:
        model_path, _, _ = generate_relief_cookie_cutter(
            image=image,
            diameter_mm=diameter,
            base_thickness=base_thickness,
            relief_depth=relief_depth,
            rim_height=rim_height,
            rim_thickness=rim_thickness,
            resolution=resolution,
            invert_relief=invert_relief,
            output_format="stl"
        )
        return model_path
    except Exception:
        return None


def process_image_contour(
    image,
    cutter_size: float,
    wall_height: float,
    wall_thickness: float,
    simplify: float,
    smart_remove_bg: bool,
    invert: bool,
    use_edges: bool
):
    """Process uploaded image using contour extraction."""
    if image is None:
        return None, None, "Please upload an image first!"

    try:
        target_size = 200
        scale_mm = cutter_size / target_size

        model_path, preview, stats = generate_cookie_cutter(
            image=image,
            wall_height=wall_height,
            wall_thickness=wall_thickness,
            target_size=target_size,
            simplify=simplify,
            scale_mm=scale_mm,
            output_format="glb",
            invert=invert,
            use_edges=use_edges,
            smart_remove_bg=smart_remove_bg
        )

        stats_text = f"""**Cookie Cutter Generated!**

- Size: {stats['width_mm']:.1f} x {stats['height_mm']:.1f} mm
- Wall Height: {stats['wall_height_mm']} mm
- Wall Thickness: {stats['wall_thickness_mm']} mm
- Contour Points: {stats['contour_points']}
- Mesh: {stats['vertices']} vertices, {stats['faces']} faces

Ready to download and 3D print!"""

        return model_path, preview, stats_text

    except Exception as e:
        return None, None, f"Error: {str(e)}"


def download_stl_contour(
    image,
    cutter_size: float,
    wall_height: float,
    wall_thickness: float,
    simplify: float,
    smart_remove_bg: bool,
    invert: bool,
    use_edges: bool
):
    """Generate STL file using contour extraction."""
    if image is None:
        return None

    try:
        target_size = 200
        scale_mm = cutter_size / target_size

        model_path, _, _ = generate_cookie_cutter(
            image=image,
            wall_height=wall_height,
            wall_thickness=wall_thickness,
            target_size=target_size,
            simplify=simplify,
            scale_mm=scale_mm,
            output_format="stl",
            invert=invert,
            use_edges=use_edges,
            smart_remove_bg=smart_remove_bg
        )

        return model_path

    except Exception:
        return None


def process_cylinder_seal(
    image,
    outer_radius: float,
    wall_thickness: float,
    height: float,
    max_displacement: float,
    resolution: int,
    smoothing: float,
    invert: bool,
    constant_wall: bool
):
    """Process uploaded image to generate a cylinder seal."""
    if image is None:
        return None, None, "Please upload an image first!"

    try:
        model_path, preview, stats = generate_cylinder_seal(
            image=image,
            outer_radius=outer_radius,
            wall_thickness=wall_thickness,
            height=height,
            max_displacement=max_displacement,
            resolution=resolution,
            smoothing=smoothing,
            invert=invert,
            constant_wall=constant_wall,
            output_format="glb"
        )

        stats_text = f"""**Cylinder Seal Generated!**

- Outer Radius: {stats['outer_radius_mm']} mm
- Inner Radius: {stats['inner_radius_mm']} mm
- Wall Thickness: {stats['wall_thickness_mm']} mm
- Height: {stats['height_mm']} mm
- Circumference: {stats['circumference_mm']} mm
- Max Displacement: {stats['max_displacement_mm']} mm
- Resolution: {stats['resolution']}
- Constant Wall: {"Yes" if stats['constant_wall'] else "No"}
- Mesh: {stats['vertices']} vertices, {stats['faces']} faces

Ready to download and 3D print!"""

        return model_path, preview, stats_text

    except Exception as e:
        import traceback
        return None, None, f"Error: {str(e)}\n\n{traceback.format_exc()}"


def download_cylinder_stl(
    image,
    outer_radius: float,
    wall_thickness: float,
    height: float,
    max_displacement: float,
    resolution: int,
    smoothing: float,
    invert: bool,
    constant_wall: bool
):
    """Generate STL file for cylinder seal."""
    if image is None:
        return None

    try:
        model_path, _, _ = generate_cylinder_seal(
            image=image,
            outer_radius=outer_radius,
            wall_thickness=wall_thickness,
            height=height,
            max_displacement=max_displacement,
            resolution=resolution,
            smoothing=smoothing,
            invert=invert,
            constant_wall=constant_wall,
            output_format="stl"
        )
        return model_path
    except Exception:
        return None


# Example images
EXAMPLES_DIR = Path(__file__).parent / "examples"


def create_app():
    """Create and configure the Gradio interface."""

    with gr.Blocks(
        title="Cookie Cutter Maker",
        theme=gr.themes.Soft(primary_hue="orange"),
        css="""
        .main-title { text-align: center; margin-bottom: 0; }
        .subtitle { text-align: center; color: #666; margin-top: 0; }
        """
    ) as app:

        gr.Markdown(
            """
            # Cookie Cutter Maker
            ### Turn any image into a 3D-printable cookie cutter!
            """,
            elem_classes=["main-title"]
        )

        with gr.Tabs():
            # Tab 1: Relief Embossing (recommended)
            with gr.TabItem("Relief Embossing", id="relief"):
                gr.Markdown(
                    """
                    **Best for:** Photos, characters, logos - creates embossed relief from image brightness.
                    Light areas = raised, dark areas = recessed (or invert).
                    """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 1. Upload Image")
                        relief_image = gr.Image(
                            label="Upload your image (click or drag & drop)",
                            type="numpy",
                            sources=["upload"],
                            height=250,
                            show_download_button=False
                        )

                        gr.Markdown("### 2. Adjust Settings")

                        relief_diameter = gr.Slider(
                            minimum=40,
                            maximum=150,
                            value=80,
                            step=5,
                            label="Cookie Diameter (mm)"
                        )

                        relief_depth = gr.Slider(
                            minimum=0.5,
                            maximum=5.0,
                            value=2.0,
                            step=0.5,
                            label="Relief Depth (mm)",
                            info="How deep the embossing is"
                        )

                        relief_rim_height = gr.Slider(
                            minimum=8,
                            maximum=20,
                            value=12,
                            step=1,
                            label="Cutting Rim Height (mm)"
                        )

                        with gr.Accordion("Advanced Settings", open=False):
                            relief_base = gr.Slider(
                                minimum=2,
                                maximum=8,
                                value=3,
                                step=0.5,
                                label="Base Thickness (mm)"
                            )

                            relief_rim_thick = gr.Slider(
                                minimum=1.0,
                                maximum=3.0,
                                value=1.5,
                                step=0.25,
                                label="Rim Thickness (mm)"
                            )

                            relief_resolution = gr.Slider(
                                minimum=100,
                                maximum=300,
                                value=200,
                                step=50,
                                label="Resolution",
                                info="Higher = more detail but larger file"
                            )

                            relief_invert = gr.Checkbox(
                                label="Invert relief (dark = raised)",
                                value=False,
                                info="Check for dark images on light backgrounds"
                            )

                        relief_generate_btn = gr.Button(
                            "Generate Cookie Cutter",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### 3. Preview & Download")

                        relief_model_3d = gr.Model3D(
                            label="3D Preview",
                            height=300,
                            clear_color=[0.9, 0.9, 0.9, 1.0]
                        )

                        relief_preview = gr.Image(
                            label="Heightmap Preview (yellow=raised, purple=recessed)",
                            height=150
                        )

                        relief_stats = gr.Markdown(
                            value="Upload an image and click 'Generate' to create your cookie cutter!"
                        )

                        relief_download_btn = gr.Button(
                            "Download STL for 3D Printing",
                            variant="secondary"
                        )

                        relief_stl_file = gr.File(
                            label="STL Download",
                            visible=True
                        )

            # Tab 2: Contour-based (for simple shapes)
            with gr.TabItem("Outline Only", id="contour"):
                gr.Markdown(
                    """
                    **Best for:** Simple silhouettes, shapes with clear outlines. Creates cutting edge only (no embossing).
                    """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 1. Upload Image")
                        contour_image = gr.Image(
                            label="Upload your image (click or drag & drop)",
                            type="numpy",
                            sources=["upload"],
                            height=250,
                            show_download_button=False
                        )

                        gr.Markdown("### 2. Adjust Settings")

                        cutter_size = gr.Slider(
                            minimum=30,
                            maximum=150,
                            value=80,
                            step=5,
                            label="Cookie Size (mm)"
                        )

                        wall_height = gr.Slider(
                            minimum=8,
                            maximum=25,
                            value=15,
                            step=1,
                            label="Wall Height (mm)"
                        )

                        wall_thickness = gr.Slider(
                            minimum=0.8,
                            maximum=3.0,
                            value=1.2,
                            step=0.1,
                            label="Wall Thickness (mm)"
                        )

                        with gr.Accordion("Advanced Settings", open=False):
                            simplify = gr.Slider(
                                minimum=0.1,
                                maximum=3.0,
                                value=1.0,
                                step=0.1,
                                label="Contour Simplification"
                            )

                            smart_remove_bg = gr.Checkbox(
                                label="Smart background removal (AI)",
                                value=False
                            )

                            invert = gr.Checkbox(
                                label="Invert colors",
                                value=False
                            )

                            use_edges = gr.Checkbox(
                                label="Use edge detection",
                                value=False
                            )

                        contour_generate_btn = gr.Button(
                            "Generate Cookie Cutter",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### 3. Preview & Download")

                        contour_model_3d = gr.Model3D(
                            label="3D Preview",
                            height=300,
                            clear_color=[0.9, 0.9, 0.9, 1.0]
                        )

                        contour_preview = gr.Image(
                            label="Contour Preview",
                            height=150
                        )

                        contour_stats = gr.Markdown(
                            value="Upload an image and click 'Generate' to create your cookie cutter!"
                        )

                        contour_download_btn = gr.Button(
                            "Download STL",
                            variant="secondary"
                        )

                        contour_stl_file = gr.File(
                            label="STL Download",
                            visible=True
                        )

            # Tab 3: Cylinder Seals
            with gr.TabItem("Cylinder Seal", id="cylinder"):
                gr.Markdown(
                    """
                    **Best for:** Creating rollable cylinder seals (like ancient Sumerian seals).
                    The image is wrapped around a cylinder - rolling it imprints the design.
                    """
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 1. Upload Image")
                        cylinder_image = gr.Image(
                            label="Upload your image (click or drag & drop)",
                            type="numpy",
                            sources=["upload"],
                            height=250,
                            show_download_button=False
                        )

                        gr.Markdown("### 2. Adjust Settings")

                        cylinder_radius = gr.Slider(
                            minimum=10,
                            maximum=40,
                            value=20,
                            step=1,
                            label="Outer Radius (mm)"
                        )

                        cylinder_height = gr.Slider(
                            minimum=30,
                            maximum=100,
                            value=60,
                            step=5,
                            label="Height (mm)"
                        )

                        cylinder_displacement = gr.Slider(
                            minimum=0.5,
                            maximum=4.0,
                            value=2.0,
                            step=0.25,
                            label="Carving Depth (mm)",
                            info="How deep the design is carved"
                        )

                        with gr.Accordion("Advanced Settings", open=False):
                            cylinder_wall = gr.Slider(
                                minimum=2.0,
                                maximum=6.0,
                                value=4.0,
                                step=0.5,
                                label="Wall Thickness (mm)"
                            )

                            cylinder_resolution = gr.Slider(
                                minimum=180,
                                maximum=720,
                                value=360,
                                step=90,
                                label="Resolution",
                                info="Higher = more detail but larger file"
                            )

                            cylinder_smoothing = gr.Slider(
                                minimum=0.0,
                                maximum=3.0,
                                value=1.0,
                                step=0.5,
                                label="Smoothing",
                                info="Gaussian blur to reduce noise"
                            )

                            cylinder_invert = gr.Checkbox(
                                label="Invert (dark = carved)",
                                value=True,
                                info="Usually checked for seals"
                            )

                            cylinder_constant_wall = gr.Checkbox(
                                label="Constant wall thickness",
                                value=True,
                                info="Inner follows outer surface"
                            )

                        cylinder_generate_btn = gr.Button(
                            "Generate Cylinder Seal",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### 3. Preview & Download")

                        cylinder_model_3d = gr.Model3D(
                            label="3D Preview",
                            height=300,
                            clear_color=[0.9, 0.9, 0.9, 1.0]
                        )

                        cylinder_preview = gr.Image(
                            label="Unwrapped Preview (yellow=raised, purple=carved)",
                            height=150
                        )

                        cylinder_stats = gr.Markdown(
                            value="Upload an image and click 'Generate' to create your cylinder seal!"
                        )

                        cylinder_download_btn = gr.Button(
                            "Download STL for 3D Printing",
                            variant="secondary"
                        )

                        cylinder_stl_file = gr.File(
                            label="STL Download",
                            visible=True
                        )

        # Examples section
        if EXAMPLES_DIR.exists():
            example_files = list(EXAMPLES_DIR.glob("*.png")) + list(EXAMPLES_DIR.glob("*.jpg"))
            if example_files:
                gr.Markdown("### Example Images")
                gr.Examples(
                    examples=[[str(f)] for f in example_files[:4]],
                    inputs=[relief_image],
                    label="Click an example to try it"
                )

        gr.Markdown(
            """
            ---
            **Tips:**
            - **Relief Embossing** creates a stamp that presses details into the cookie
            - **Outline Only** creates just the cutting edge shape
            - **Cylinder Seal** creates a rollable stamp (like ancient Sumerian seals)
            - For photos/characters, use Relief Embossing
            - For simple shapes (stars, hearts), use Outline Only
            - For repeating patterns or historical seal designs, use Cylinder Seal
            - Use "Invert" for dark images on light backgrounds
            """
        )

        # Event handlers - Relief
        relief_generate_btn.click(
            fn=process_image_relief,
            inputs=[relief_image, relief_diameter, relief_base, relief_depth,
                    relief_rim_height, relief_rim_thick, relief_resolution, relief_invert],
            outputs=[relief_model_3d, relief_preview, relief_stats]
        )

        relief_download_btn.click(
            fn=download_relief_stl,
            inputs=[relief_image, relief_diameter, relief_base, relief_depth,
                    relief_rim_height, relief_rim_thick, relief_resolution, relief_invert],
            outputs=[relief_stl_file]
        )

        # Event handlers - Contour
        contour_generate_btn.click(
            fn=process_image_contour,
            inputs=[contour_image, cutter_size, wall_height, wall_thickness, simplify, smart_remove_bg, invert, use_edges],
            outputs=[contour_model_3d, contour_preview, contour_stats]
        )

        contour_download_btn.click(
            fn=download_stl_contour,
            inputs=[contour_image, cutter_size, wall_height, wall_thickness, simplify, smart_remove_bg, invert, use_edges],
            outputs=[contour_stl_file]
        )

        # Event handlers - Cylinder Seal
        cylinder_generate_btn.click(
            fn=process_cylinder_seal,
            inputs=[cylinder_image, cylinder_radius, cylinder_wall, cylinder_height,
                    cylinder_displacement, cylinder_resolution, cylinder_smoothing,
                    cylinder_invert, cylinder_constant_wall],
            outputs=[cylinder_model_3d, cylinder_preview, cylinder_stats]
        )

        cylinder_download_btn.click(
            fn=download_cylinder_stl,
            inputs=[cylinder_image, cylinder_radius, cylinder_wall, cylinder_height,
                    cylinder_displacement, cylinder_resolution, cylinder_smoothing,
                    cylinder_invert, cylinder_constant_wall],
            outputs=[cylinder_stl_file]
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
