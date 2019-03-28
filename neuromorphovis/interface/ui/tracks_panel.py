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
STREAMLINE_MATERIAL_NAME = 'streamline_mat_1'
GROUPNAME_HELPER_GEOMETRY = 'Helper Geometry'
GROUPNAME_ROI_VOLUMES = 'ROI Volumes'

# Groups of imported streamlines
_tck_groups = {}


################################################################################
# Support functions
################################################################################

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


def track_group_coordinates(group_obj):
    """
    Convert Blender group of curves to list of coordinate lists.
    """
    curves_pts = []
    for curve_obj in group_obj.objects:
        if curve_obj.type != 'CURVE':
            continue
        crv_geom = curve_obj.data.splines[0]
        num_pts = len(crv_geom.points)
        curves_pts.append([crv_geom.points[i].co[0:3] for i in range(num_pts)])
    return curves_pts


def get_streamline_material():
    """
    Get skeleton materials, while only creating them once.
    """
    mat = bpy.data.materials.get(STREAMLINE_MATERIAL_NAME, None)
    if mat is None:
        current_scene = bpy.context.scene
        if not current_scene.render.engine == 'BLENDER_RENDER':
            current_scene.render.engine = 'BLENDER_RENDER'

        # Create a new material
        mat = bpy.data.materials.new(STREAMLINE_MATERIAL_NAME)

        # Set the diffuse parameters
        mat.diffuse_color = [1.0, 0.707, 0.014] # yellow
        mat.diffuse_shader = 'LAMBERT'
        mat.diffuse_intensity = 0.8

        # Set the specular parameters (leave default)
        # mat.specular_color = [1.0, 1.0, 1.0]
        # mat.specular_shader = 'WARDISO'
        # mat.specular_intensity = 0.5

        # 'Transparency' menu parameters
        mat.alpha = 1.0

        # 'Shading' menu parameters
        mat.ambient = 1.0
        mat.emit = 0.0 # positive for 'glowing' effect
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

    bpy.types.Scene.StreamlinesOutputDirectory = StringProperty(
        name="Output Directory",
        description="Select a directory where the results will be generated",
        default="Select Directory", maxlen=5000, subtype='DIR_PATH')

    bpy.types.Scene.StreamlinesOutputFileName = StringProperty(
        name="Output Filename",
        description="Select file name for axon groups.",
        default="axon_groups")

    # bpy.types.Scene.ProjectionPrePopLabel = StringProperty(
    #     name="Pre-synaptic Label",
    #     description="Label for pre-synaptic population of projection.",
    #     default="PRE")

    # bpy.types.Scene.ProjectionPostPopLabel = StringProperty(
    #     name="Post-synaptic label",
    #     description="Label for post-synaptic population of projection.",
    #     default="POST")

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
        row_import_header = layout.row()
        row_import_header.label(text='Import streamlines:',
                                icon='LIBRARY_DATA_DIRECT')
        # Select directory
        row_dir = layout.row()
        row_dir.prop(scene, 'StreamlinesFile')

        # Output directory
        output_directory_row = layout.row()
        output_directory_row.prop(scene, 'StreamlinesOutputDirectory')

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

        row_max_load = layout.row()
        row_max_load.prop(context.scene, 'MaxLoadStreamlines')

        row_min_length = layout.row()
        row_min_length.prop(context.scene, 'MinStreamlineLength')

        row_scale =layout.row()
        row_scale.prop(context.scene, 'StreamlineUnitScale')

        # Draw Streamlines
        col_sketch = layout.column(align=True)
        col_sketch.operator('import.streamlines', icon='IPO')

        # ROIs -----------------------------------------------------------------
        row_export = layout.row()
        row_export.label(text='ROIs:', icon='ALIASED')

        # ROI name
        layout.row().prop(context.scene, 'RoiName')

        # Button to import ROI
        layout.column(align=True).operator('add.roi', icon='IMPORT')
        
        # Button to center view
        layout.column(align=True).operator('view3d.view_selected', icon='RESTRICT_VIEW_OFF')

        # Exporting ------------------------------------------------------------

        # Saving morphology options
        row_export = layout.row()
        row_export.label(text='Export Streamlines:', icon='LIBRARY_DATA_DIRECT')

        col_export = layout.column(align=True)
        col_export.operator('export.streamlines', icon='SAVE_COPY')

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
        group_name = "Streamlines-{}".format(fname_base)
        tck_group = bpy.data.groups.get(group_name, None)
        if tck_group is None:
            tck_group = bpy.data.groups.new(group_name)

        # Material for streamlines
        tck_mat = get_streamline_material()
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

            tck_group.objects.link(crv_obj)

        # Save references to objects
        _tck_groups[tck_group.name] = tck_group
        return {'FINISHED'}


class AddROI(bpy.types.Operator):
    """
    Add ROI for positioning cells and streamlines.
    """

    # Operator parameters
    bl_idname = "add.roi"
    bl_label = "Add to ROIs"


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
        tck_data = {
            name: track_group_coordinates(grp) for name, grp in _tck_groups.items()
        }

        # save as pickle to selected path
        out_dir = context.scene.StreamlinesOutputDirectory
        out_fname = context.scene.StreamlinesOutputFileName
        out_fpath = os.path.join(out_dir, out_fname + '.pkl')
        with open(out_fpath, "wb") as f:
            pickle.dump(tck_data, f)
        return {'FINISHED'}


class SetAxonPreCell(bpy.types.Operator):
    """
    Operator SetAxonPreCell
    """
    bl_idname = "set_axon.pre"
    bl_label = "Set pre-synaptic cell for axon"

    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        # Get blender objects representing neuron and axon
        selected = list(context.selected_objects)
        cell_obj = next((obj for obj in selected if 'neuron_morphology_name' in obj.keys()), None)
        if cell_obj is None:
            self.report({'ERROR'}, 'Please select at least one neuronal geometry element.')
            return {'FINISHED'}
        axon_obj = next((obj for obj in selected if obj.type == 'CURVE'), None)
        if axon_obj is None:
            self.report({'ERROR'}, 'Please select at least one axon curve.')
            return {'FINISHED'}

        # Get the morphology object
        cell_morph = nmvif.dbs_panel.get_morphology_from_object(cell_obj)

        # Set pre-synaptic cell GID
        axon_obj['presynaptic_cell_GID'] = cell_morph.gid
        axon_obj['presynaptic_cell_name'] = cell_morph.label

        return {'FINISHED'}


class SetAxonPostCell(bpy.types.Operator):
    """
    Operator SetAxonPostCell
    """
    bl_idname = "set_axon.post"
    bl_label = "Set post-synaptic cell for axon"

    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        # Get blender objects representing neuron and axon
        selected = list(context.selected_objects)
        axon_obj = next((obj for obj in selected if obj.type == 'CURVE'), None)
        if axon_obj is None:
            self.report({'ERROR'}, 'Please select at least one axon curve.')
            return {'FINISHED'}

        # Get cell GID of all selected object that represent neuron geometry
        post_cell_gids = set((obj['neuron_morphology_gid'] for obj in selected
                                if 'neuron_morphology_gid' in obj.keys()))
        if len(post_cell_gids) == 0:
            self.report({'ERROR'}, 'Please select at least one neuronal geometry element.')
            return {'FINISHED'}

        # Set pre-synaptic cell GID
        old_post_gids = set(axon_obj.get('postsynaptic_cell_GIDs', []))
        axon_obj['postsynaptic_cell_GIDs'] = sorted(old_post_gids.union(post_cell_gids))

        return {'FINISHED'}


################################################################################
# GUI Registration
################################################################################


# Classes to register with Blender
_reg_classes = [
    StreamlinesPanel, ImportStreamlines, ExportStreamlines, AddROI
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
