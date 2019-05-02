####################################################################################################
# Copyright (c) 2016 - 2018, EPFL / Blue Brain Project
#               Marwan Abdellah <marwan.abdellah@epfl.ch>
#
# This file is part of NeuroMorphoVis <https://github.com/BlueBrain/NeuroMorphoVis>
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, version 3 of the License.
#
# This Blender-based tool is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <http://www.gnu.org/licenses/>.
####################################################################################################

# Blender imports
import bpy
from mathutils import Vector, Matrix
import bmesh

# Third party imports
import numpy as np

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.scene
from neuromorphovis.geometry import spline


def draw_cyclic_curve_from_points(curve_name,
                                  list_points):
    """Draw a cyclic poly curve form a list of points.

    :param curve_name:
        The name of the curve.
    :param list_points:
        A list of points to draw the curve from.
    :return:
        A reference to the drawn curve.
    """

    # Create the curve data
    curve_data = bpy.data.curves.new(name="c_%s" % curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.25
    line_material = bpy.data.materials.new('color')
    line_material.diffuse_color = (1, 1, 0.1)
    curve_data.materials.append(line_material)

    # Create an object to the curve and link it to the scene
    curve_object = bpy.data.objects.new("o_%s" % curve_name, curve_data)
    curve_object.location = (0, 0, 0)
    bpy.context.scene.objects.link(curve_object)

    curve = curve_data.splines.new('POLY')
    curve.points.add(len(list_points) - 1)
    for i in range(len(list_points)):
        vector = list_points[i]
        curve.points[i].co = ((vector[0], vector[1], vector[2])) + (1,)

    curve.order_u = len(curve.points) - 1
    curve.use_cyclic_u = True

    # Return a reference to the created curve object
    return curve


def draw_polyline_curve(name, vertices, curve_type='POLY',
                        select=True, active=True):
    """
    Draw polyline as Curve geometry.
    """
    # Container for curve
    curvedata = bpy.data.curves.new(name='curve_'+name, type='CURVE')
    curvedata.dimensions = '3D'
    if curve_type == 'NURBS':
        curvedata.resolution_u = 2 

    # Create the curve
    polyline = curvedata.splines.new(curve_type)
    polyline.points.add(len(vertices)-1)
    for i, coord in enumerate(vertices):
        x,y,z = coord
        polyline.points[i].co = (x, y, z, 1)

    if curve_type == 'NURBS':
        polyline.order_u = len(polyline.points)-1
        polyline.use_endpoint_u = True # curve runs to endpoints

    # create Object
    curve_obj = bpy.data.objects.new(name, curvedata)

    # attach to scene and validate context
    bpy.context.scene.objects.link(curve_obj)
    bpy.context.scene.objects.active = curve_obj
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS') # ORIGIN_CENTER_OF_MASS

    curve_obj.select = select # add to selection
    return curve_obj


def draw_polyline_mesh(name, vertices, select=True):
    """
    Draw polyline as Mesh edge.
    """
    bm = bmesh.new()

    for i in range(len(vertices)-1):
        bm.edges.new([vertices[i], vertices[i+1]])

    # Create Mesh object to add to scene
    mesh_geom = bpy.data.meshes.new('mesh_'+name)
    mesh_obj = bpy.data.objects.new(name, mesh_geom)
    bpy.context.scene.objects.link(mesh_obj)

    # Store bmesh geometry in Mesh object
    bm.to_mesh(mesh_geom)
    bm.free()

    # Set the origin
    bpy.context.scene.objects.active = mesh_obj
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS') # ORIGIN_CENTER_OF_MASS

    mesh_obj.select = select
    return mesh_obj


def polyline_to_nurbs(tck_obj, subsample=1, origin_to=None):
    """
    Convert polyline or any curve coordinates to NURBS that interpolates

    @param  crv_obj : bpy.object
            A CURVE object whose verticel wil be used to create NURBS
    """
    # Get streamline points
    tck_spl = tck_obj.data.splines[0] # also works for polylines
    tck_pts = [tck_spl.points[i].co[0:3] for i in range(len(tck_spl.points))]
    ctl_pts = tck_pts[::subsample]
    if (len(tck_pts) % subsample != 0):
        # Always include last point
        ctl_pts.append(tck_pts[-1])

    # Add a generic 'curve data' container for the curve
    crv_data = bpy.data.curves.new(name=tck_obj.name + '_NURBS', type='CURVE')
    crv_data.dimensions = '3D'
    crv_data.resolution_u = 12 # smoothness

    # Add a spline to the curve data (can be NURBS/BEZIER/POLYLINE)
    spl = crv_data.splines.new('NURBS')
    spl.points.add(len(ctl_pts)-1) # 1lready 1 point present by default
    for i, coord in enumerate(ctl_pts):
        x, y, z = coord
        spl.points[i].co = (x, y, z, 1)

    # see https://en.wikipedia.org/wiki/Non-uniform_rational_B-spline#Technical_specifications
    spl.order_u = min(4, len(spl.points))
    spl.use_endpoint_u = True # curve runs to endpoints

    # Add it as an object to the scene
    curve_obj = bpy.data.objects.new(tck_obj.name + '_NURBS', crv_data)
    curve_obj.matrix_world = tck_obj.matrix_world

    # attach to scene and validate context
    bpy.context.scene.objects.link(curve_obj)
    bpy.context.scene.objects.active = curve_obj
    
    # Set curve origin to its starting point for easy positioning
    if origin_to is not None:
        pt_idx = 0 if origin_to == 'start' else -1
        old_pos = bpy.context.scene.cursor_location
        new_pos = tck_spl.points[pt_idx].co.to_3d() + tck_obj.matrix_world.translation
        bpy.context.scene.cursor_location = new_pos
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR') # ORIGIN_CENTER_OF_MASS
        bpy.context.scene.cursor_location = old_pos

    return curve_obj


def spline_to_polyline(crv_obj, spacing=1.0, raw_coordinates=False):
    """
    Convert any spline-type curve to a polyline by sampling it
    at regular intervals.

    @return     curve : bpy_types.Object or list[Vector]
                If raw_coordinates is true, return list of coordinates,
                else return blender object in scene.
    """
    # Curve length for parameterization of curve
    arclength = spline.arclength(crv_obj)
    if spacing >= arclength:
        raise ValueError('Spacing must be larger than length of curve.')

    # sample every X mm and make polyline
    t_spacing = spacing / arclength
    t_samples = np.arange(0.0, 1.0 + t_spacing, t_spacing)
    t_samples = np.concatenate((t_samples[t_samples < 1], [1.0]))
    # t_samples = np.inspace(0, 1, int(arclength/spacing), endpoint=True)

    if raw_coordinates:
        # Global coordinates
        return [spline.calct(crv_obj, t, local=False) for t in t_samples]
    else:
        # Local coordinates, since we will apply same matrix_world
        verts = [spline.calct(crv_obj, t, local=True) for t in t_samples]

    new_name = crv_obj.name + '_POLY'
    # crv_poly = draw_polyline_curve(new_name, verts, curve_type='POLY')

    # Create underlying curve data
    curvedata = bpy.data.curves.new(name='PolyLine', type='CURVE')
    curvedata.dimensions = '3D'
    polyline = curvedata.splines.new('POLY')
    polyline.points.add(len(verts)-1)
    for i, coord in enumerate(verts):
        x,y,z = coord
        polyline.points[i].co = (x, y, z, 1)

    # create Scene object
    crv_poly = bpy.data.objects.new(new_name, curvedata)
    bpy.context.scene.objects.link(crv_poly)

    # Set coordinate system
    crv_poly.matrix_world = Matrix(crv_obj.matrix_world) # .copy()
    crv_poly.matrix_basis = Matrix(crv_obj.matrix_basis) # .copy()

    return crv_poly



def draw_closed_circle(radius=1,
                       location=Vector((0, 0, 0)),
                       vertices=4,
                       name='circle',
                       caps=True):
    """Create a local circle that doesn't account for the transformations applied on it.

    :param radius:
        The radius of the circle.
    :param location:
        The location of the circle.
    :param vertices:
        The number of vertices used to construct the sides of the circle.
    :param name:
        The name of the circle.
    :param caps:
        A flag to indicate whether to close the caps of the circle or not.
    :return:
        A reference to the circle object.
    """

    # Deselect all the objects in the scene
    nmv.scene.ops.deselect_all()

    # Fill the circle
    fill = 'NGON' if caps else 'NOTHING'
    bpy.ops.mesh.primitive_circle_add(
        vertices=vertices, radius=radius/2, location=location, fill_type=fill)

    # Return a reference to the circle objects
    circle = bpy.context.scene.objects.active

    # Rename the circle
    circle.name = name

    # Return a reference to the created circle.
    return circle