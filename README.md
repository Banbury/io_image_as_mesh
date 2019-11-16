# Import image as mesh

This is an add-on for [Blender](http://www.blender.org), that imports images as meshes. If the image contains alpha
transparency, the mesh will have the shape of the opaque parts of the image. The resulting image is scaled according
to its resolution in inches.

## Installation

Download the repository as Zip file. Then install the add-on in Blender with
File/User Preferences/Add-ons/Install from file.

Rename the directory in the 'addons' folder to 'io_image_as_mesh'. 

## Usage

Import an image with File/Import/Image As Mesh. Multiple files can be imported at the same time.
Check `Subdivide` to create a mesh with mostly equally sized triangles. 

Currently only PNGs are allowed. Images without alpha information (like JPGs) should be imported with
with the 'Images as Planes' addon.

> If you cannot see the image, change the viewport shading to 'Texture'.

## Implementation details

The add-on uses the Marching Squares algorithm to create a polygon around the non-transparent parts of the imported
image.
Then the polygon is reduced with the Ramer-Douglas-Peucker algorithm.
Blender's bmesh.ops.triangle_fill is used to create the mesh from the polygon.
Finally uv coordintes are calculated, a material is created and the mesh is scaled to the size of the image.

## License information

The [RDP library](https://github.com/sebleier/RDP) is licensed under the BSD.

Everything else is GPL licensed.

## Changelog

**v1.2.0:**
* Better subdivision with Subdivision and Decimate modifiers
* Removed code from CoaTools

**v1.1.0:**
* Added support for Cycles material.
* Borrowed triangulation algorithm from CoaTools.
    * Triangulation can be turned on and off in the file dialog.
    * Best used with convex shapes.
