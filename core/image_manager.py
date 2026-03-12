"""Image creation, circular dependency avoidance, and UDIM support."""

from __future__ import annotations

import bpy

from ..modes import BakeMode


def get_or_create_image(
    name: str,
    width: int,
    height: int,
    *,
    color_space: str = "Non-Color",
    use_float: bool = False,
    background: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
) -> bpy.types.Image:
    """Get existing image by name or create a new one."""
    image = bpy.data.images.get(name)

    if image and (image.size[0] != width or image.size[1] != height):
        bpy.data.images.remove(image)
        image = None

    if image is None:
        image = bpy.data.images.new(
            name,
            width=width,
            height=height,
            alpha=True,
            float_buffer=use_float,
        )

    image.colorspace_settings.name = color_space
    fill_image(image, background)

    return image


def fill_image(image: bpy.types.Image, color: tuple[float, float, float, float]):
    """Fill an image with a solid color."""
    pixels = list(image.pixels)
    px_count = len(pixels) // 4
    flat = list(color) * px_count
    image.pixels[:] = flat


def resolve_color_space(mode: BakeMode, override: str) -> str:
    """Determine color space: use override unless 'AUTO'."""
    if override != 'AUTO':
        return override
    return mode.color_space


def handle_circular_dependency(
    objects: list[bpy.types.Object],
    bake_image: bpy.types.Image,
) -> bpy.types.Image | None:
    """If the bake target image is used as a texture input, copy it to avoid circular read/write.

    Returns the temporary copy (to be cleaned up after bake), or None if no circular dep.
    """
    for obj in objects:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image == bake_image:
                    if node.name == "BakeTurbo_Target":
                        continue
                    # Circular dependency found — copy the image
                    temp = bake_image.copy()
                    temp.name = bake_image.name + "_bake_temp"
                    # Replace references in texture nodes (not the bake target)
                    for obj2 in objects:
                        for slot2 in obj2.material_slots:
                            mat2 = slot2.material
                            if not mat2 or not mat2.use_nodes:
                                continue
                            for n in mat2.node_tree.nodes:
                                if (n.type == 'TEX_IMAGE'
                                        and n.image == bake_image
                                        and n.name != "BakeTurbo_Target"):
                                    n.image = temp
                    return temp
    return None


def cleanup_temp_image(temp_image: bpy.types.Image | None):
    """Remove temporary image created for circular dependency avoidance."""
    if temp_image and temp_image.users == 0:
        bpy.data.images.remove(temp_image)


def create_aa_image(
    name: str,
    base_width: int,
    base_height: int,
    aa_factor: int,
    **kwargs,
) -> bpy.types.Image:
    """Create an oversized image for anti-aliasing, to be downsampled after bake."""
    return get_or_create_image(
        name + f"_aa{aa_factor}x",
        base_width * aa_factor,
        base_height * aa_factor,
        **kwargs,
    )


def downsample_image(src: bpy.types.Image, dst: bpy.types.Image, factor: int):
    """Downsample src into dst by averaging factor×factor pixel blocks."""
    sw, sh = src.size
    dw, dh = dst.size

    src_pixels = list(src.pixels)
    dst_pixels = [0.0] * (dw * dh * 4)

    inv = 1.0 / (factor * factor)

    for dy in range(dh):
        for dx in range(dw):
            r = g = b = a = 0.0
            for fy in range(factor):
                for fx in range(factor):
                    sx = dx * factor + fx
                    sy = dy * factor + fy
                    si = (sy * sw + sx) * 4
                    r += src_pixels[si]
                    g += src_pixels[si + 1]
                    b += src_pixels[si + 2]
                    a += src_pixels[si + 3]
            di = (dy * dw + dx) * 4
            dst_pixels[di] = r * inv
            dst_pixels[di + 1] = g * inv
            dst_pixels[di + 2] = b * inv
            dst_pixels[di + 3] = a * inv

    dst.pixels[:] = dst_pixels


def invert_image(image: bpy.types.Image):
    """Invert RGB channels of an image (leave alpha untouched)."""
    pixels = list(image.pixels)
    for i in range(0, len(pixels), 4):
        pixels[i] = 1.0 - pixels[i]
        pixels[i + 1] = 1.0 - pixels[i + 1]
        pixels[i + 2] = 1.0 - pixels[i + 2]
    image.pixels[:] = pixels
