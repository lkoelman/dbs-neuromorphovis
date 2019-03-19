"""
Panel for importing streamlines generated using diffusion tractography.

@author Lucas Koelman

@date   19/03/2019
"""

# Python imports
import os

# Blender imports
import bpy
from bpy.props import (
    BoolProperty, FloatProperty, IntProperty,
    StringProperty, EnumProperty
)

# External imports
import numpy as np
import nibabel as nib

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.edit
import neuromorphovis.interface as nmvif
import neuromorphovis.scene

# Debugging
DEBUG = True

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
    # bl_options = {'DEFAULT_CLOSED'}

    # --------------------------------------------------------------------------
    # Properties for UI state

    ## Properties: morphology import
    default_dir = "/home/luye/Downloads/morphologies" if DEBUG else "Select Directory"
    bpy.types.Scene.MorphologiesDirectory = StringProperty(
        name="Morphologies",
        description="Select a directory to mesh all the morphologies in it",
        default=default_dir, maxlen=2048, subtype='DIR_PATH')

    # Streamlines file
    bpy.types.Scene.StreamlinesFile = StringProperty(
        name="Streamlines File",
        description="Select streamlines file",
        default='Select File', maxlen=2048,  subtype='FILE_PATH')

    # Output directory
    bpy.types.Scene.StreamlinesOutputDirectory = StringProperty(
        name="Output Directory",
        description="Select a directory where the results will be generated",
        default="Select Directory", maxlen=5000, subtype='DIR_PATH')

    bpy.types.Scene.MaxLoadStreamlines = IntProperty(
        name="Max Streamlines",
        description="Maximum number of loaded streamlines",
        default=500, min=1, max=10000)

    bpy.types.Scene.MinStreamlineLength = FloatProperty(
        name="Min Length",
        description="Minimum streamline length (mm)",
        default=1.0, min=1.0, max=1e6)


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
        row_max_load = layout.row()
        row_max_load.prop(context.scene, 'MaxLoadStreamlines')

        row_min_length = layout.row()
        row_min_length.prop(context.scene, 'MinStreamlineLength')

################################################################################
# Operators
################################################################################

class ImportStreamlines(bpy.types.Operator):
    """
    Repair the morphology skeleton (as volumetric mesh),
    detect the artifacts and fix them.
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

        # Load the streamlines
        streamlines = load_streamlines(context.scene.StreamlinesOutputDirectory)
        if streamlines is None:
            self.report({'ERROR'}, 'Invalid streamlines file.')
            return {'FINISHED'}

        # TODO: convert to polylines
        fname_base, ext = os.path.splitext(os.path.split(context.scene.StreamlinesFile)[1])
        for tck_coords in streamlines:
            crv_obj = nmv.geometry.draw_polyline_curve('Streamline', tck_coords,
                                                        curve_type='POLY')

        # TODO: save references to objects
        return {'FINISHED'}


def load_streamlines(file_path, max_num, min_length):
    """
    Load streamlines from file
    """
    with open(file_path, 'r') as tracts_file:
        tck_file = nib.streamlines.load(tracts_file, lazy_load=True)

        # Make sure tracts are defined in RAS+ world coordinate system
        tractogram = tck_file.tractogram.to_world(lazy=True)

        # Manual transformation to RAS+ world coordinate system
        # vox2ras = tck_file.tractogram.affine_to_rasmm
        # tck_ras_coords = nib.affines.apply_affine(vox2ras, streamline)

        streamlines_filtered = []
        for i, streamline in enumerate(tractogram.streamlines): # lazy-loading generator
            # streamline is (N x 3) matrix
            if len(streamlines_filtered) > max_num:
                break
            # check length
            tck_len = np.sum(np.linalg.norm(np.diff(streamline, axis=0), axis=1))
            if tck_len >= min_length:
                streamlines_filtered.append(streamline)

        return streamlines_filtered


def register_panel():
    """
    Registers all the classes in this panel.
    """
    bpy.utils.register_class(StreamlinesPanel)


def unregister_panel():
    """
    Un-registers all the classes in this panel.
    """
    bpy.utils.unregister_class(StreamlinesPanel)
