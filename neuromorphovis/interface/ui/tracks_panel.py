"""
Panel for importing streamlines generated using diffusion tractography.

@author Lucas Koelman

@date   19/03/2019
"""

# Python imports
import os
import pickle

# Blender imports
import bpy
from bpy.props import FloatProperty, IntProperty, StringProperty

# External imports
import numpy as np
import nibabel as nib

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.scene
import neuromorphovis.interface as nmvif


################################################################################
# State variables
################################################################################

# Constants
DEBUG = True
STREAMLINE_MATERIAL_PREFIX = 'streamline_mat_'
GROUPNAME_HELPER_GEOMETRY = 'Helper Geometry'
GROUPNAME_ROI_VOLUMES = 'ROI Volumes'

# Groups of imported streamlines
_tck_groups = {}

# Materials
_STREAMLINE_MATERIAL_DEFS = {
    'DEFAULT': {
        'diffuse_color': [1.0, 0.707, 0.014], # yellow
        'diffuse_shader': 'LAMBERT',
        'diffuse_intensity': 0.8,
        'alpha': 1.0,
        'ambient': 1.0,
        'emit': 0.0,
    },
    # Unassigned properties are taken from DEFAULT
    'INCLUDE_EXPORT': {
        'diffuse_color': [0.707, 0.108, 0.652],
        'emit': 0.6,
    }
}

# Custom Blender properties used by this module
_PROP_AX_EXPORT = nmvif.mkprop('include_export')
_PROP_OBJECT_TYPE = nmv.interface.ui.ui_data._PROP_OBJECT_TYPE

################################################################################
# Support functions
################################################################################

def get_streamlines(bpy_objects=None, selector=None):
    """
    Get all streamlines in the object collection

    :param  bpy_objects:
        bpy_collection, e.g. context.scene.objects or bpy.data.objects
    """
    if bpy_objects is None:
        bpy_objects = bpy.data.objects
    if selector is None:
        selector = lambda crv: True
    return [o for o in bpy_objects if (
                (o.get(_PROP_OBJECT_TYPE, None) == 'streamline')
                and (selector(o)))]


def load_streamlines(file_path, max_num=1e12, min_length=0.0):
    """
    Load streamlines from file
    """
    tck_file = nib.streamlines.load(file_path, lazy_load=True)

    # Make sure tracts are defined in RAS+ world coordinate system
    tractogram = tck_file.tractogram.to_world(lazy=True)

    # Manual transformation to RAS+ world coordinate system
    # vox2ras = tck_file.tractogram.affine_to_rasmm
    # tck_ras_coords = nib.affines.apply_affine(vox2ras, streamline)

    streamlines_filtered = []
    for i, streamline in enumerate(tractogram.streamlines): # lazy-loading generator
        # streamline is (N x 3) matrix
        if len(streamlines_filtered) >= max_num:
            break
        # check length
        if min_length > 0:
            tck_len = np.sum(np.linalg.norm(np.diff(streamline, axis=0), axis=1))
        else:
            tck_len = 1.0
        if tck_len >= min_length:
            streamlines_filtered.append(streamline)

    return streamlines_filtered


def streamline_coordinates(curve_object):
    """
    Get vertex coordinates of Blender curve representing a streamline.
    """
    if curve_object.type != 'CURVE':
        raise ValueError(curve_object.type)
    crv_geom = curve_object.data.splines[0]
    num_pts = len(crv_geom.points)
    return [crv_geom.points[i].co[0:3] for i in range(num_pts)]


def get_streamline_material(state='DEFAULT'):
    """
    Get skeleton materials, while only creating them once.
    """
    mat_name = STREAMLINE_MATERIAL_PREFIX + state
    mat = bpy.data.materials.get(mat_name, None)
    if mat is None:
        current_scene = bpy.context.scene
        if not current_scene.render.engine == 'BLENDER_RENDER':
            current_scene.render.engine = 'BLENDER_RENDER'

        # Create a new material
        mat = bpy.data.materials.new(mat_name)

        # Set material properties
        for prop_name, default_val in _STREAMLINE_MATERIAL_DEFS['DEFAULT'].items():
            value = _STREAMLINE_MATERIAL_DEFS[state].get(prop_name, default_val)
            setattr(mat, prop_name, value)

    return mat


def get_streamline_bevel_profile(radius=1.0):
    """
    Create a 'bevel object' for a streamline curve. This is a native Blender
    curve property that determines the extrusion profile.
    """
    bev_name = 'streamline_bevel_profile_radius-{}'.format(radius)
    bev_obj = bpy.data.objects.get(bev_name, None)
    if bev_obj is None:
        bpy.ops.object.select_all(action='DESELECT')

        bpy.ops.curve.primitive_bezier_circle_add(location=[0., 0., 0.])

        # Set its geometrical properties
        num_verts = 16
        bpy.context.object.data.resolution_u = num_verts / 4
        bev_obj = bpy.context.scene.objects.active
        bev_obj.scale[0] = radius
        bev_obj.scale[1] = radius
        bev_obj.scale[2] = radius

        # Make it findable
        bev_obj.name = bev_name
        group = bpy.data.groups.get(GROUPNAME_HELPER_GEOMETRY, None)
        if group is None:
            group = bpy.data.groups.new(GROUPNAME_HELPER_GEOMETRY)
        group.objects.link(bev_obj)

    return bev_obj


def set_streamline_appearance(curve_obj, material=None, solid=True,
                              bevel_object=None, caps=True):
    """
    Set the appearance of any Blender curve.
    """
    line_data = curve_obj.data

    # The line is drawn in 3D
    line_data.dimensions = '3D'
    line_data.fill_mode = 'FULL'

    # Setup the spatial data of a SOLID line
    if solid:
        # Leave default, scaled by radius associated with each point
        line_data.bevel_depth = 1.0

        # Adjust the texture coordinates of the poly-line.
        # line_data.use_auto_texspace = False
        # line_data.texspace_size[0] = 5
        # line_data.texspace_size[1] = 5
        # line_data.texspace_size[2] = 5

        # If a bevel object is given, use it for scaling the diameter of the poly-line
        if bevel_object is not None:
            line_data.bevel_object = bevel_object
            line_data.use_fill_caps = caps

    # Setup appearance
    if material is not None:
        # line_data.materials.clear()
        line_data.materials.append(material)


################################################################################
# UI elements
################################################################################

class StreamlinesPanel(bpy.types.Panel):
    """
    Panel containing operators to position neuron morphology around
    DBS electrode.
    """

    # Panel parameters
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Track Positioning'
    bl_category = 'NeuroMorphoVis'
    bl_options = {'DEFAULT_CLOSED'}

    # --------------------------------------------------------------------------
    # Properties for UI state

    # Streamlines file
    debug_tck_file = '/home/luye/Documents/mri_data/Waxholm_rat_brain_atlas/WHS_DTI_v1_ALS/S56280_track_filter-ROI-STN.tck'
    default_tck_file = debug_tck_file if DEBUG else 'Select File'

    bpy.types.Scene.StreamlinesFile = StringProperty(
        name="Streamlines File",
        description="Select streamlines file",
        default=default_tck_file, maxlen=2048,  subtype='FILE_PATH')


    bpy.types.Scene.MaxLoadStreamlines = IntProperty(
        name="Max Streamlines",
        description="Maximum number of loaded streamlines",
        default=100, min=1, max=10000)

    bpy.types.Scene.MinStreamlineLength = FloatProperty(
        name="Min Length",
        description="Minimum streamline length (mm)",
        default=1.0, min=1.0, max=1e6)

    bpy.types.Scene.StreamlineUnitScale = FloatProperty(
        name="Scale",
        description="Streamline scale relative to microns (units/um)",
        default=1e3, min=1e-12, max=1e12)

    bpy.types.Scene.RoiName = StringProperty(
        name="ROI Name",
        description="Name for selected ROI volume",
        default='ROI-1')


    # --------------------------------------------------------------------------
    # Panel overriden methods

    def draw(self, context):
        """
        Layout UI elements in the panel.

        :param context:
            Rendering context
        """
        layout = self.layout
        scene = context.scene

        # File Paths -----------------------------------------------------------
        layout.row().label(text='Import streamlines:', icon='LIBRARY_DATA_DIRECT')

        # Select directory
        layout.row().prop(scene, 'StreamlinesFile')

        # Import Options -------------------------------------------------------

        # labels for PRE and POST synaptic populations
        # row_pops_header = layout.row()
        # row_pops_header.column(align=True).label(text='Pre-syn.')
        # row_pops_header.column(align=True).label(text='Post-syn.')
        # row_pops_fields = layout.row()
        # row_pops_fields.column(align=True).prop(
        #     context.scene, 'ProjectionPrePopLabel', text='')
        # row_pops_fields.column(align=True).prop(
        #     context.scene, 'ProjectionPostPopLabel', text='')

        layout.row().prop(context.scene, 'MaxLoadStreamlines')

        layout.row().prop(context.scene, 'MinStreamlineLength')

        layout.row().prop(context.scene, 'StreamlineUnitScale')

        # Draw Streamlines
        layout.column(align=True).operator('import.streamlines', icon='IPO')

        # ROIs -----------------------------------------------------------------
        layout.row().label(text='ROIs:', icon='ALIASED')

        # ROI name
        layout.row().prop(context.scene, 'RoiName')

        # Button to import ROI
        layout.column(align=True).operator('add.roi', icon='IMPORT')
        
        # Button to center view
        layout.column(align=True).operator('view3d.view_selected', icon='RESTRICT_VIEW_OFF')

        # Exporting ------------------------------------------------------------

        layout.row().label(text='Export Streamlines:', icon='LIBRARY_DATA_DIRECT')

        layout.column(align=True).operator('axon.toggle_export', icon='EXPORT')
        layout.column(align=True).operator('export.streamlines', icon='SAVE_COPY')

################################################################################
# Operators
################################################################################

class ImportStreamlines(bpy.types.Operator):
    """
    Import streamlines from tractography file.

    See https://nipy.org/nibabel/reference/nibabel.streamlines.html
    for supported formats.
    """

    # Operator parameters
    bl_idname = "import.streamlines"
    bl_label = "Import Streamlines"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context

        :return:
            'FINISHED'
        """

        # Load the streamlines as N x 3 arrays
        streamlines = load_streamlines(context.scene.StreamlinesFile,
                        max_num=context.scene.MaxLoadStreamlines,
                        min_length=context.scene.MinStreamlineLength)
        if streamlines is None:
            self.report({'ERROR'}, 'Invalid streamlines file.')
            return {'FINISHED'}

        # convert to Blender polyline curves
        fname_base, ext = os.path.splitext(os.path.split(context.scene.StreamlinesFile)[1])

        # Create group
        group_name = "Axons ({})".format(fname_base)
        tck_group = bpy.data.groups.get(group_name, None)
        if tck_group is None:
            tck_group = bpy.data.groups.new(group_name)

        # Material for streamlines
        tck_mat = get_streamline_material(state='DEFAULT')
        tck_scale = context.scene.StreamlineUnitScale
        bev_obj = get_streamline_bevel_profile(radius=tck_scale*1e-3)

        # Create curves
        for tck_coords in streamlines:
            tck_name = 'tck_' + fname_base # copies are numbered by Blender

            # Scale units
            coords_micron = tck_coords * tck_scale

            # Draw using our simple function
            crv_obj = nmv.geometry.draw_polyline_curve(tck_name, coords_micron,
                                                        curve_type='POLY')
            # context.scene.objects.active = crv_obj
            # bpy.ops.object.material_slot_add()
            set_streamline_appearance(crv_obj, material=tck_mat, solid=True, 
                caps=True, bevel_object=bev_obj)

            # Alternative: line_ops.draw_poly_line
            # crv_obj = nmv.geometry.ops.draw_poly_line(
            #     poly_line_data=coords_micron,
            #     poly_line_radii=np.ones((len(coords_micron), 1)),
            #     name=tck_name, material=tck_mat,
            #     bevel_object=bev_obj)

            # Organize object so we can recognize it
            tck_group.objects.link(crv_obj)
            prop_name = nmvif.mkprop('object_type')
            crv_obj[prop_name] = 'streamline'

        # Save references to objects
        _tck_groups[tck_group.name] = tck_group
        return {'FINISHED'}


class AddROI(bpy.types.Operator):
    """
    Add ROI for positioning cells and streamlines.
    """

    # Operator parameters
    bl_idname = "add.roi"
    bl_label = "Add as ROI"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context

        :return:
            'FINISHED'
        """
        sel_obj = context.scene.objects.active
        sel_obj.name = context.scene.RoiName

        group = bpy.data.groups.get(GROUPNAME_ROI_VOLUMES, None)
        if group is None:
            group = bpy.data.groups.new(GROUPNAME_ROI_VOLUMES)
        group.objects.link(sel_obj)

        return {'FINISHED'}


class ToggleAxonExport(bpy.types.Operator):
    """
    Tag or untag selected axon for export.
    """
    bl_idname = "axon.toggle_export"
    bl_label = "(Un)mark for export"

    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        # Get blender objects representing neuron and axon
        crv_objs = [obj for obj in context.selected_objects if obj.type == 'CURVE']
        if len(crv_objs) == 0:
            self.report({'ERROR'}, 'Please select at least one axon curve.')
            return {'FINISHED'}

        # Toggle the export flag for each axon
        mat_exclude = nmvif.ui.tracks_panel.get_streamline_material(state='DEFAULT')
        mat_include = nmvif.ui.tracks_panel.get_streamline_material(state='INCLUDE_EXPORT')
        for curve in crv_objs:
            should_export = curve.get(_PROP_AX_EXPORT, False)
            curve[_PROP_AX_EXPORT] = not should_export # toggle it

            # Adjust material property to reflect inclusion
            material = mat_exclude if should_export else mat_include # we flipped it!
            curve.data.materials.clear()
            curve.data.materials.append(material)


        return {'FINISHED'}


class ExportStreamlines(bpy.types.Operator):
    """
    Import streamlines from tractography file.

    See https://nipy.org/nibabel/reference/nibabel.streamlines.html
    for supported formats.
    """

    # Operator parameters
    bl_idname = "export.streamlines"
    bl_label = "Export Streamlines"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        # Just export raw streamlines, metadata should be in config file
        streamlines = get_streamlines(selector=lambda crv: crv.get(_PROP_AX_EXPORT, False))
        tck_dict = {
            crv.name: streamline_coordinates(crv) for crv in streamlines
        }

        # Subdirectories for outputs are defined on io_panel.py
        out_basedir = context.scene.OutputDirectory
        out_fulldir = os.path.join(out_basedir, 'axons')
        if not nmv.file.ops.path_exists(out_fulldir):
            nmv.file.ops.clean_and_create_directory(out_fulldir)

        # save as pickle to selected path
        out_fpath = os.path.join(out_fulldir, 'axon_coordinates.pkl')
        with open(out_fpath, "wb") as f:
            pickle.dump(tck_dict, f)

        self.report({'INFO'}, 'Wrote axons to file {}'.format(out_fpath))
        return {'FINISHED'}


################################################################################
# GUI Registration
################################################################################


# Classes to register with Blender
_reg_classes = [
    StreamlinesPanel, ImportStreamlines, ExportStreamlines, AddROI,
    ToggleAxonExport
]


def register_panel():
    """
    Registers all the classes in this panel.
    """
    for cls in _reg_classes:
        bpy.utils.register_class(cls)


def unregister_panel():
    """
    Un-registers all the classes in this panel.
    """
    for cls in _reg_classes:
        bpy.utils.unregister_class(cls)
