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

# Debugging
DEBUG = True

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
    TODO: Convert Blender group of curves to list of coordinate arrays.
    """
    pass


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
    debug_tck_file = '/home/luye/Documents/mri_data/Waxholm_rat_brain_atlas/WHS_DTI/S56280_1e4tracks.tck'
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

    bpy.types.Scene.ProjectionPrePopLabel = StringProperty(
        name="Pre-synaptic Label",
        description="Label for pre-synaptic population of projection.",
        default="PRE")

    bpy.types.Scene.ProjectioPostPopLabel = StringProperty(
        name="Post-synaptic label",
        description="Label for post-synaptic population of projection.",
        default="POST")

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
        row_pops_header = layout.row()
        row_pops_header.column(align=True).label(text='Pre-syn.')
        row_pops_header.column(align=True).label(text='Post-syn.')

        row_pops_fields = layout.row()
        row_pops_fields.column(align=True).prop(
            context.scene, 'ProjectionPrePopLabel', text='')
        row_pops_fields.column(align=True).prop(
            context.scene, 'ProjectioPostPopLabel', text='')

        row_max_load = layout.row()
        row_max_load.prop(context.scene, 'MaxLoadStreamlines')

        row_min_length = layout.row()
        row_min_length.prop(context.scene, 'MinStreamlineLength')

        row_scale =layout.row()
        row_scale.prop(context.scene, 'StreamlineUnitScale')

        # Draw Streamlines
        col_sketch = layout.column(align=True)
        col_sketch.operator('sketch.streamlines',
                                icon='MOD_PARTICLES')

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
    bl_idname = "sketch.streamlines"
    bl_label = "Sketch Streamlines"


    def execute(self, context):
        """Execute the operator.

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
        group_name = "{}-to-{}_tck-{}".format(context.scene.ProjectionPrePopLabel,
                        context.scene.ProjectionPostPopLabel, fname_base)
        tck_group = bpy.data.groups.get(group_name, bpy.data.groups.new(group_name))
        for tck_coords in streamlines:
            tck_name = 'tck_' + fname_base # copies are numbered by Blender
            coords_micron = tck_coords * context.scene.StreamlineUnitScale
            crv_obj = nmv.geometry.draw_polyline_curve(tck_name, coords_micron,
                                                        curve_type='POLY')
            tck_group.objects.link(crv_obj)

        # Save references to objects
        _tck_groups[tck_group.name] = tck_group
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
    StreamlinesPanel, ImportStreamlines, ExportStreamlines
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
