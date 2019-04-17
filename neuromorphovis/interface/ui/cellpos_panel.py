"""
Morphology import and editing panel for positioning cells around electrode.

This is a modified version of the module 'neuromorphovis.interface.ui.edit_panel'.

@author Lucas Koelman

@date   8/03/2019

FIXME: whenever transform applied to geometry, also apply to morphology
- upon editing/export/save apply latest matrix_world to Morphology object
    - save initial matrix_world?

"""


# System imports
import copy
import os
import re

# Blender imports
import bpy
from bpy.props import (
    BoolProperty, FloatProperty, IntProperty,
    StringProperty, EnumProperty
)
import mathutils

# External imports
import numpy as np

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.edit
import neuromorphovis.interface as nmvif
import neuromorphovis.interface.ui.circuit_data as circuit_data
import neuromorphovis.scene
import neuromorphovis.consts
import neuromorphovis.bmeshi


# Globals
## Morphology editor
morphology_editor = None
## A flag to indicate that the morphology has been edited and ready for update
is_skeleton_edited = False
in_edit_mode = False

# Debugging
DEBUG = True

def DEBUG_LOG(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


# Info about currently loaded morphologies
nmvif.ui_options.morphology.morphologies_loaded_directory = None


################################################################################
# UI elements
################################################################################

class DbsPositioningPanel(bpy.types.Panel):
    """
    Panel containing operators to position neuron morphology around
    DBS electrode.
    """

    # Panel parameters
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Cell Positioning'
    bl_category = 'NeuroMorphoVis'
    # bl_options = {'DEFAULT_CLOSED'}

    # --------------------------------------------------------------------------
    # Properties for UI state

    ## Properties: morphology import
    default_dir = "/home/luye/Downloads/morphologies" if DEBUG else "Select Directory"

    # Already defined in IO panel
    # bpy.types.Scene.MorphologyFile = StringProperty(
    #     name="Morphology File",
    #     description="Select a specific morphology to mesh",
    #     default='Select File', maxlen=2048,  subtype='FILE_PATH')

    # bpy.types.Scene.MorphologiesDirectory = StringProperty(
    #     name="Morphologies",
    #     description="Select a directory to mesh all the morphologies in it",
    #     default=default_dir, maxlen=2048, subtype='DIR_PATH')

    bpy.types.Scene.MorphologyFileImportAll = BoolProperty(
        name="Import all in directory",
        description="Import all morphologies in file directory.",
        default=False)

    ## Properties: morphology sketching
    bpy.types.Scene.MorphologySketched = BoolProperty(default=False)
    bpy.types.Scene.MorphologyCoordinatesEdited = BoolProperty(default=False)

    ## Properties : duplication
    bpy.types.Scene.DuplicationLayoutMethod = EnumProperty(
        items=[('GRID', 'Grid', 'Distribute cells on grid.'),
               ('RANDOM', 'Random', 'Distribute cells randomly using density.')],
        name='Layout',
        default='GRID')

    bpy.types.Scene.DuplicationDensity = FloatProperty(
        name="Density",
        description="Desired cell density (cells / mm^3)",
        default=1000.0, min=1, max=1e6)

    bpy.types.Scene.MaxCellDuplicates = IntProperty(
        name="Max Duplicates",
        description="Maximum number of cell duplicates.",
        default=500, min=1, max=10000)

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

        # Import / Export ------------------------------------------------------
        row_import_header = layout.row()
        row_import_header.label(text='Import morphologies:',
                                icon='LIBRARY_DATA_DIRECT')
        # Select directory
        layout.row().prop(scene, 'MorphologyFile')
        layout.row().prop(scene, 'MorphologyFileImportAll')

        # Morphology sketching button
        if not in_edit_mode:
            layout.column(align=True).operator(
                'import.neuron_morphology', icon='PARTICLE_POINT')
 
            layout.column(align=True).operator(
                'export.morphologies', icon='GROUP_VERTEX')

        # Duplication ----------------------------------------------------------
        row_dup_header = layout.row()
        row_dup_header.label(text='Duplicate morphologies:',
                              icon='STICKY_UVS_LOC')
        
        ## Duplication - spatial layout
        row_dup_layout = layout.row()
        row_dup_layout.label(text='Layout:')
        row_dup_layout.prop(context.scene, 'DuplicationLayoutMethod', expand=True)
        
        ## Duplication - cell density
        row_dup_density = layout.row()
        row_dup_density.prop(context.scene, 'DuplicationDensity')

        row_dup_maxnum = layout.row()
        row_dup_maxnum.prop(context.scene, 'MaxCellDuplicates')

        ## Duplication - target volume
        col_bound_btn = layout.column(align=True)
        col_bound_btn.operator('set.duplication_boundary',
                                text='Set boundary volume',
                                icon='MESH_ICOSPHERE')

        row_bound_label = layout.row()
        # row_bound_label.label(text='Boundary:')
        row_bound_label.prop(context.scene, 'DuplicationBoundaryName')

        ## Duplication - duplicate button
        col_dup_button = layout.column(align=True)
        col_dup_button.operator('duplicate.morphology',
                                icon='MOD_PARTICLES')



################################################################################
# Operators
################################################################################

class ImportMorphology(bpy.types.Operator):
    """
    Repair the morphology skeleton (as volumetric mesh),
    detect the artifacts and fix them.
    """

    # Operator parameters
    bl_idname = "import.neuron_morphology"
    bl_label = "Import Morphology"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """

        # NOTE: the difference between
        # - selected in widget: nmv.interface.ui_options.io.morphologies_input_directory 
        # - actually loaded: nmv.interface.ui_options.morphology.morphologies_loaded_directory

        # Get directory selected through widget
        input_files = []
        if context.scene.MorphologyFileImportAll:
            # Import all SWC files in directory
            base_dir = os.path.dirname(context.scene.MorphologyFile)
            input_files = [os.path.join(base_dir, p) for p in os.listdir(base_dir) if 
                                p.endswith('.swc')]
        else:
            # Import only the selected SWC file
            input_files = [context.scene.MorphologyFile]


        # Global variables for keeping track of loaded objects
        nmvif.ui_morphologies = []

        # Load each morphology in input directory
        for morph_path in input_files:
            circuit_data.import_neuron_from_file(morph_path)

        return {'FINISHED'}



class DuplicateMorphology(bpy.types.Operator):
    """
    Make duplicates of selected morphology and distribute them in space.
    """

    # Operator parameters
    bl_idname = "duplicate.morphology"
    bl_label = "Mass copy morphology"

    # Operator properties (data class)
    offset_x = FloatProperty(
                    name="X Offset",
                    min=0.0, max=1e6,
                    default=50.0,
                    description="X offset of duplicate"
                    )
    
    offset_y = FloatProperty(
                    name="Y Offset",
                    min=0.0, max=1e6,
                    default=50.0,
                    description="Y offset of duplicate"
                    )
    
    offset_z = FloatProperty(
                    name="Z Offset",
                    min=0.0, max=1e6,
                    default=50.0,
                    description="Z offset of duplicate"
                    )

    ############################################################################
    # Support methods


    def make_duplicate_origins(self, context, source_object):
        """
        Generate origin points for all cell duplicates.

        :return:
            List of points, or empty array if points could not be made
        """
        layout_method = context.scene.DuplicationLayoutMethod # 'GRID' or 'RANDOM'
        density = context.scene.DuplicationDensity
        max_duplicates = context.scene.MaxCellDuplicates

        # Get bounding box of target volume
        bounds_obj = context.scene.objects.get(context.scene.DuplicationBoundaryName, None)
        if bounds_obj:
            bbox_corners = np.array([bounds_obj.matrix_world * mathutils.Vector(corner)
                                        for corner in bounds_obj.bound_box])
            xyz_min = bbox_corners.min(axis=0)
            xyz_max = bbox_corners.max(axis=0)
            # xyz_max = [max((corner[j] for corner in bbox_corners)) for j in range(3)]
        else:
            bbox_corners = np.array([source_object.matrix_world * mathutils.Vector(corner)
                                        for corner in source_object.bound_box])
            enlarge_bbox = [1000.0, 1000.0, 1000.0]
            xyz_min = bbox_corners.min(axis=0) - enlarge_bbox
            xyz_max = bbox_corners.max(axis=0) + enlarge_bbox

        # Coordinates are in micrometers, density in cells / mm^3
        cell_per_um = 1e-3 * density ** (1./3.)

        # Generate coordinates in bounding box of boundary volume
        if layout_method == 'GRID':
            grid_samples = [] # one dimension (x/y/z) per row
            for i in range(3):
                ncell = int(np.ceil(cell_per_um * (xyz_max[i] - xyz_min[i])))
                if ncell == 0:
                    self.report({'ERROR'}, 'Density too low along dimension ' +  'xyz'[i])
                grid_samples.append(
                    np.linspace(xyz_min[i], xyz_max[i], num=ncell, endpoint=False))
            # All coordinates in N x 3 matrix
            origins = np.array([co.ravel() for co in np.meshgrid(*grid_samples)]).T
        elif layout_method == 'RANDOM':
            bbox_dims = xyz_max - xyz_min
            bbox_volume = np.prod(bbox_dims) # um^3
            ncell = int(np.ceil(density * bbox_volume * 1e-9))
            origins = np.random.random((ncell, 3))
            for i in range(3):
                origins[:,i] = origins[:,i] * bbox_dims[i] + xyz_min[i]
        else:
            raise ValueError('Unexpected layout method', layout_method)
        
        DEBUG_LOG('DBS: generated {} origin points for duplicates'.format(origins.shape[0]))
        if origins.shape[0] == 0:
            return np.array([])

        # Remove points that are not inside boundary volume
        if bounds_obj:
            inside_mask = np.zeros((origins.shape[0],), dtype=bool)
            for i in range(origins.shape[0]):
                dup_pt = mathutils.Vector(origins[i,:])
                found, mesh_pt, normal, face_idx = bounds_obj.closest_point_on_mesh(dup_pt, 1e12)
                mesh_pt = bounds_obj.matrix_world * mesh_pt # was in object space
                inside_mask[i] = ((mesh_pt-dup_pt).dot(normal) >= 0.0) if found else False
            DEBUG_LOG('DBS: {} origin points were inside boundary volume'.format(
                        inside_mask.sum()))
            origins_all = origins
            origins = origins[inside_mask, :]

        # Ensure we don't exceed maximum number of copies
        src_loc = np.array(source_object.location)
        if origins.shape[0] > max_duplicates:
            # sort by distance from source location, keep closest
            dists = np.linalg.norm(origins - src_loc, axis=1)
            sorted_idx = np.argsort(dists)
            origins = origins[sorted_idx[:max_duplicates], :]

        DEBUG_LOG('DBS: {} origin points remaining after pruning'.format(origins.shape[0]))
        return origins


    # def draw(self, context):
    #     """
    #     Draw options panel for operator
    #     """
    #     layout = self.layout

    #     col = layout.column(align=True)
    #     col.prop(self, "offset_x", slider=False)
    #     col.prop(self, "offset_y", slider=False)
    #     col.prop(self, "offset_z", slider=False)


    def invoke(self, context, event):
        """
        Invoke is used to initialize the operator from the context at the moment
        the operator is called. It is typically used to assign properties
        which are then used by execute(). 
        """
        # Set properties
        # if context.scene.DuplicationBoundaryName == 'None':
        #     self.report({'ERROR'}, 'Please select a boundary volume first.')
        #     return {'FINISHED'}

        return self.execute(context)


    def execute(self, context):
        """
        Executes the operator.

        :param context:
            Operator context.

        :return:
            {'FINISHED'}
        """
        # Get selected morphology
        selected_object = context.scene.objects.active
        selected_neuron = circuit_data.get_neuron_from_blend_object(selected_object)
        if selected_neuron is None:
            self.report({'ERROR'}, 'Please select a morphology to duplicate')
            return {'FINISHED'}


        # Get locations to place duplicates
        dup_origins = self.make_duplicate_origins(context, selected_object)
        if dup_origins.size == 0:
            self.report({'ERROR'}, 'No duplicates could be created with given '
                                   'cell density and boundary volume.')
            return {'FINISHED'}

        for i, dup_pt in enumerate(dup_origins):
            # Duplicate selected morphology
            duplicate_label = circuit_data.make_duplicate_label(selected_neuron)

            DEBUG_LOG("DBS: creating duplicate morphology '{}'' ({}/{})".format(
                       duplicate_label, i, dup_origins.shape[0]))

            neuron_copy = selected_neuron.duplicate(label=duplicate_label)
            circuit_data.add_neuron(neuron_copy)

            # New transform is that of source object with translation to new origin
            xform_mod = selected_object.matrix_world.copy()
            xform_mod.translation = mathutils.Vector(dup_pt)

            # Transform only parent geometry (child geometry matrices are relative)
            soma_geom = neuron_copy.get_soma_geometry()
            soma_geom.matrix_world = xform_mod # xform_mod * geom_obj.matrix_world

            # ALTERNATIVE: generic transformation
            # xform = mathutils.Matrix.Translation(mathutils.Vector(
            #                 (self.offset_x, self.offset_y, self.offset_z)))
            # bobj.matrix_world = xform * bobj.matrix_world

        return {'FINISHED'}


class SetDuplicationBoundary(bpy.types.Operator):
    """
    Update the morphology coordinates following to the repair process.
    """

    # Operator parameters
    bl_idname = "set.duplication_boundary"
    bl_label = "Set boundary volume for cell duplicates"

    bpy.types.Scene.DuplicationBoundaryName = StringProperty(
        name="Boundary Volume",
        description="Name of object representing duplication boundary.",
        default='None')

    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """

        # Check if selected object is watertight mesh or other volume
        obj = context.scene.objects.active
        if obj.type != 'MESH':
            self.report({'ERROR'}, 'Selected object is not a mesh. ' 
                                'Please select a watertight mesh as boundary.')
            return {'FINISHED'}

        prev_mode = obj.mode
        bpy.ops.object.mode_set(mode='EDIT')
        nvert_nonmanifold = nmv.bmeshi.ops.count_non_manifold_vertices(context)
        bpy.ops.object.mode_set(mode=prev_mode)


        if nvert_nonmanifold > 0:
            self.report({'ERROR'}, 'Selected mesh is not watertight. '
                                 'Please select a watertight mesh as boundary.')
            return {'FINISHED'}

        # Store name of boundary object for later use
        context.scene.DuplicationBoundaryName = obj.name

        return {'FINISHED'}


class ExportMorphologies(bpy.types.Operator):
    """
    Export the reconstructed morphology in an SWC file
    """

    # Operator parameters
    bl_idname = "export.morphologies"
    bl_label = "Export all to SWC"

    def execute(self, context):
        """
        Executes the operator.

        :param context: Operator context.
        :return: {'FINISHED'}
        """

        # Ensure that there is a valid directory where the meshes will be written to
        if nmvif.ui_options.io.output_directory is None:
            self.report({'ERROR'}, nmv.consts.Messages.PATH_NOT_SET)
            return {'FINISHED'}

        if not nmv.file.ops.file_ops.path_exists(context.scene.OutputDirectory):
            self.report({'ERROR'}, nmv.consts.Messages.INVALID_OUTPUT_PATH)
            return {'FINISHED'}

        # Subdirectories for outputs are defined on io_panel.py
        out_basedir = context.scene.OutputDirectory
        out_fulldir = os.path.join(out_basedir, context.scene.MorphologiesPath)
        if not nmv.file.ops.path_exists(out_fulldir):
            nmv.file.ops.clean_and_create_directory(out_fulldir)

        # Get morphologies to export
        selected_neurons = circuit_data.get_neurons_from_blend_objects(
                                                list(context.selected_objects))

        # If specific cells selected, only export those
        if len(selected_neurons) > 0:
            exported_morphologies = selected_neurons
        else:
            exported_morphologies = circuit_data.get_neurons()

        self.report({'DEBUG'}, 'Found {} morphologies to export.'.format(
            len(exported_morphologies)))
        
        # Export the selected morphologies
        for neuron in exported_morphologies:
            swc_samples = neuron.get_transformed_samples()
            nmv.file.write_swc_samples_to_swc_file(swc_samples, out_fulldir, neuron.label)

        self.report({'INFO'}, 'Morphologies exported to {}'.format(out_fulldir))

        return {'FINISHED'}



################################################################################
# GUI Registration
################################################################################


# Classes to register with Blender
_reg_classes = [
    DbsPositioningPanel, ImportMorphology, ExportMorphologies,
    DuplicateMorphology, SetDuplicationBoundary
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