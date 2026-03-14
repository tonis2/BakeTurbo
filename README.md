# Bake Turbo

A Blender addon for fast texture baking with automatic object grouping, PBR map extraction, and batch baking.

## Installation

1. Download or clone this repository
2. In Blender, go to **Edit → Preferences → Add-ons → Install**
3. Select the addon folder or ZIP file
4. Enable "Bake Turbo" in the addon list

The panel appears in the **3D Viewport sidebar → Bake** tab.

## Quick Start

1. Select your objects in the viewport
2. Set **Grouping** to "Selection" (default) — the active object is the bake target, other selected objects are the high-poly source
3. Choose a bake mode (Normal, AO, Base Color, etc.)
4. Click **Bake**

The baked image is saved to a `textures/` folder next to your .blend file and connected to the target material automatically.

## Object Naming Convention

When using **Auto** grouping, objects are grouped by their base name. Add a suffix to assign roles:

| Suffix | Role | Example |
|--------|------|---------|
| `_low`, `_lo`, `_lowpoly` | Bake target | `sword_low` |
| `_high`, `_hi`, `_hipoly` | High-poly source | `sword_high` |
| `_cage` | Custom cage | `sword_cage` |
| `_float`, `_floater` | Floating geometry | `sword_float` |

Objects without a suffix are treated as low-poly targets. Separators can be `_`, `-`, `.`, or space.

## Grouping Modes

- **Auto** — Groups objects by naming convention
- **Selection** — Active object = target, selected = source
- **Multires** — Bake from Multiresolution modifier on active object
- **Single Object** — Bake each object independently (no high-poly projection)

## Bake Modes

**Standard** — Pass-through to Blender's built-in bake types:
- Normal, AO, Shadow, Lighting (Combined), Diffuse, Roughness, Glossy, Emit, Environment, Transmission

**PBR** — Extracts values from Principled BSDF inputs:
- Base Color, Metallic, Specular, Alpha, Emission Strength, Coat Weight, SSS, Sheen, Anisotropic, and more

**Batch** — Bake multiple map types in one go. Select which maps to include with the toggle buttons.

## Settings

| Setting | Description |
|---------|-------------|
| **Size** | Image resolution (128–8192, default 1024) |
| **Padding** | Margin in pixels to prevent UV seam bleeding (default 16) |
| **Samples** | Render samples for modes that need them (AO, Lighting, Shadow) |
| **AA** | Anti-aliasing: None, 2x, or 4x supersampling |
| **Color Space** | Auto (from mode), sRGB, or Non-Color |
| **BG** | Background color for empty areas |
| **Save** | Save baked image to `textures/` folder on disk |
| **Tiling** | Repeat factor for tiled/trim sheet textures |

## Addon Preferences

Found in **Edit → Preferences → Add-ons → Bake Turbo**:

- **Device** — GPU or CPU (GPU only shown if compute drivers are available)
- **32-bit Float** — Use higher precision images
- **Normal Y** — OpenGL (+Y) or DirectX (-Y) normal map format
- **Ignore Emission/Alpha** — Zero out these channels during non-related bakes for cleaner results
- **Clean Transmission** — Zero out transmission for non-transmission bakes

## Trim Sheet Workflow

1. Set up your trim sheet objects with proper UVs
2. Select **Batch** mode
3. Toggle on the maps you need (Normal, AO, Base Color, Roughness, Metallic, etc.)
4. Click **Batch Bake** — all selected maps are baked sequentially

## Tips

- The **Bake Sets** sub-panel shows how your objects are grouped before baking
- Use **Freeze Selection** to keep your bake set selection between bakes
- Use the **Selection** buttons (Low, High, Cage, Float) to quickly select objects by role
- Cage extrusion and ray distance are available in the **High Poly Settings** sub-panel
