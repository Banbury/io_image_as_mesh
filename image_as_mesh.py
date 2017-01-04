import bpy
import bmesh
from itertools import *
from io_image_as_mesh.rdp import rdp
from io_image_as_mesh.marching_squares import create_polygon

def create_mesh_from_image(img, subdivide):
    pixels = img.pixels
    data = []

    # creates an array with info, if pixels are transparent
    # loop takes every 4th value from pixels, which is the
    # alpha value
    for alpha in islice(pixels, 3, None, 4):
        if alpha == 0:
            data.append(0)
        else:
            data.append(1)

    # split array into rows
    w = img.size[0]
    data = [data[n:n+w] for n in range(0, len(data), w)]

    # add border of empty pixels
    for row in data:
        row.insert(0, 0)
        row.append(0)
    empty_row = [0] * (w + 2)
    data.insert(0, empty_row)
    data.append(empty_row)

    poly = rdp(create_polygon(data), 1.5)

    create_sprite(poly, img, subdivide)

    # Switch to textured shading
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D' and space.viewport_shade != 'TEXTURED' and \
                                space.viewport_shade != 'RENDERED' and \
                                space.viewport_shade != 'MATERIAL':
                    space.viewport_shade = 'TEXTURED'

def create_sprite(poly, img, subdivide):
    w = img.size[0]
    h = img.size[1]

    scene = bpy.context.scene

    points = []
    edges = []
    for i, p in enumerate(poly):
        points.append([p[0] / w - 0.5 , 0, p[1] / h - 0.5])

        if i < len(poly) - 2:
            edges.append((i, i + 1))
        else:
            edges.append((i, 0))
    mesh_data = bpy.data.meshes.new("sprite_mesh")
    mesh_data.from_pydata(points, edges, [])
    mesh_data.update()

    obj = bpy.data.objects.new(img.name, mesh_data)
    scene.objects.link(obj)
    obj.select = True
    scene.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.index_update()

    triangle_fill = bmesh.ops.triangle_fill(bm, edges=bm.edges[:], use_dissolve=False, use_beauty=True)
    if subdivide and triangle_fill:
        average_edge_cuts(bm,obj)
        triangulate(bm,obj)
        smooth_verts(bm,obj)
        collapse_short_edges(bm,obj)
        smooth_verts(bm,obj)
        clean_verts(bm,obj)
        smooth_verts(bm,obj)
        triangulate(bm,obj)
        smooth_verts(bm,obj)

    if hasattr(bm.verts, "ensure_lookup_table"):
        bm.verts.ensure_lookup_table()

    uvtex = bm.faces.layers.tex.new("UVMap")
    uv_lay = bm.loops.layers.uv.new("UVMap")

    for face in bm.faces:
        face[uvtex].image = img
        for loop in face.loops:
            uv = loop[uv_lay].uv
            index = loop.vert.index
            v = bm.verts[index].co
            uv.x = v.x + 0.5
            uv.y = v.z + 0.5

    # scale image to size in inches
    dpi_x = img.resolution[0] / 39.3701
    dpi_y = img.resolution[1] / 39.3701

    for vert in bm.verts:
        v = vert.co
        v.x *= w / dpi_x
        v.z *= h / dpi_y
        vert.co = v

    bmesh.update_edit_mesh(obj.data)

    bpy.ops.object.mode_set(mode='OBJECT')

    mat = create_blender_material(obj, img)
    create_cycles_material(mat, img)

    if scene.render.engine != 'CYCLES':
        mat.use_nodes = False

def create_blender_material(obj, img):
    tex = bpy.data.textures.new('ColorTex', type = 'IMAGE')
    tex.image = img

    mat = bpy.data.materials.new(name="Material")
    mat.use_transparency = True
    mat.emit = 1.0
    mat.alpha = 0.0
    obj.data.materials.append(mat)

    texslot = mat.texture_slots.add()
    texslot.texture = tex
    texslot.texture_coords = 'UV'
    texslot.use_map_color_diffuse = True
    texslot.use_map_color_emission = True
    texslot.emission_color_factor = 0.5
    texslot.use_map_density = True
    texslot.mapping = 'FLAT'
    texslot.use_map_alpha = True

    return mat

def create_cycles_material(mat, img):
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img

    diff = nodes.new("ShaderNodeBsdfDiffuse")

    out = nodes.new('ShaderNodeOutputMaterial')

    links.new(tex.outputs[0], diff.inputs[0])
    links.new(diff.outputs[0], out.inputs[0])

# functions borrowed from CoaTools
def average_edge_cuts(bm,obj,cuts=1):
    ### collapse short edges
    edges_len_average = 0
    edges_count = 0
    shortest_edge = 10000
    for edge in bm.edges:
        if True:#edge.is_boundary:
            edges_count += 1
            length = edge.calc_length()
            edges_len_average += length
            if length < shortest_edge:
                shortest_edge = length
    edges_len_average = edges_len_average/edges_count

    subdivide_edges = []
    for edge in bm.edges:
        cut_count = int(edge.calc_length()/shortest_edge)*cuts
        if cut_count < 0:
            cut_count = 0
        if not edge.is_boundary:
            subdivide_edges.append([edge,cut_count])
    for edge in subdivide_edges:
        bmesh.ops.subdivide_edges(bm,edges=[edge[0]],cuts=edge[1])
        bmesh.update_edit_mesh(obj.data)

def triangulate(bm,obj):
    bmesh.ops.triangulate(bm,faces=bm.faces)
    bmesh.update_edit_mesh(obj.data)

def smooth_verts(bm,obj):
    ### smooth verts
    smooth_verts = []
    for vert in bm.verts:
        if not vert.is_boundary:
            smooth_verts.append(vert)
    for i in range(50):
        #bmesh.ops.smooth_vert(bm,verts=smooth_verts,factor=1.0,use_axis_x=True,use_axis_y=True,use_axis_z=True)
        bmesh.ops.smooth_vert(bm,verts=smooth_verts,factor=1.0,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bmesh.update_edit_mesh(obj.data)

def clean_verts(bm,obj):
    ### find corrupted faces
    faces = []
    for face in bm.faces:
        i = 0
        for edge in face.edges:
            if not edge.is_manifold:
                i += 1
            if i == len(face.edges):
                faces.append(face)
    bmesh.ops.delete(bm,geom=faces,context=5)

    edges = []
    for face in bm.faces:
        i = 0
        for vert in face.verts:
            if not vert.is_manifold and not vert.is_boundary:
                i+=1
            if i == len(face.verts):
                for edge in face.edges:
                    if edge not in edges:
                        edges.append(edge)
    bmesh.ops.collapse(bm,edges=edges)

    bmesh.update_edit_mesh(obj.data)
    for vert in bm.verts:
        if not vert.is_boundary:
            vert.select = False

    verts = []
    for vert in bm.verts:
        if len(vert.link_edges) in [3,4] and not vert.is_boundary:
            verts.append(vert)
    bmesh.ops.dissolve_verts(bm,verts=verts)
    bmesh.update_edit_mesh(obj.data)

def collapse_short_edges(bm,obj,threshold=1):
    ### collapse short edges
    edges_len_average = 0
    edges_count = 0
    shortest_edge = 10000
    for edge in bm.edges:
        if True:
            edges_count += 1
            length = edge.calc_length()
            edges_len_average += length
            if length < shortest_edge:
                shortest_edge = length
    edges_len_average = edges_len_average/edges_count

    verts = []
    for vert in bm.verts:
        if not vert.is_boundary:
            verts.append(vert)
    bmesh.update_edit_mesh(obj.data)

    bmesh.ops.remove_doubles(bm,verts=verts,dist=edges_len_average*threshold)

    bmesh.update_edit_mesh(obj.data)
