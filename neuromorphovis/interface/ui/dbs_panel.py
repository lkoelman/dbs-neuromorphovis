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

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.edit
import neuromorphovis.interface as nmvif
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

def debug_log(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def debug_break():
    """
    HOWTO:
    - install ipython using pip with bundled python
    - exit or ctrl+d to continue
    """
    import IPython
    IPython.embed()

# Info about currently loaded morphologies
nmvif.ui_options.morphology.morphologies_loaded_directory = None
# 3D objects sketched around skeletons, equivalent of nmvif.ui_reconstructed_skeleton
# for multiple morphologies, with their labels as keys
nmvif.ui_reconstructed_skeletons = dict() # dict[str, list()]

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
    bpy.types.Scene.MorphologiesDirectory = StringProperty(
        name="Morphologies",
        description="Select a directory to mesh all the morphologies in it",
        default=default_dir, maxlen=2048, subtype='DIR_PATH')

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

        # Importing ------------------------------------------------------------
        row_import_header = layout.row()
        row_import_header.label(text='Import morphologies:',
                                icon='LIBRARY_DATA_DIRECT')
        # Select directory
        row_dir = layout.row()
        row_dir.prop(scene, 'MorphologiesDirectory')

        # Morphology sketching button
        if not in_edit_mode:
            col_sketch = layout.column(align=True)
            col_sketch.operator('sketch.skeleton_dbs', icon='PARTICLE_POINT')

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
        col_dup_button = layout.column(align=True)
        col_dup_button.operator('set.duplication_boundary',
                                text='Set boundary volume',
                                icon='MESH_ICOSPHERE')

        ## Duplication - duplicate button
        col_dup_button = layout.column(align=True)
        col_dup_button.operator('duplicate.morphology',
                                icon='MOD_PARTICLES')

        # Editing --------------------------------------------------------------
        col_edit_header = layout.row()
        col_edit_header.label(text='Editing Samples Coordinates:',
                              icon='OUTLINER_OB_EMPTY')

        # Morphology edit / update button
        global is_skeleton_edited
        if not is_skeleton_edited:
            col_edit_morph = layout.column(align=True)
            col_edit_morph.operator('edit.morphology_coordinates_dbs',
                                    icon='MESH_DATA')
        else:
            col_update_morph = layout.column(align=True)
            col_update_morph.operator('update.morphology_coordinates_dbs',
                                      icon='MESH_DATA')

        # Saving morphology ----------------------------------------------------
        if not in_edit_mode:

            # Saving morphology options
            row_save_morph = layout.row()
            row_save_morph.label(text='Save Morphology As:', icon='MESH_UVSPHERE')

            col_save_morph = layout.column(align=True)
            col_save_morph.operator('export_morphology_dbs.swc',
                                    icon='GROUP_VERTEX')

################################################################################
# Support functions
################################################################################

def load_morphologies(panel_object, context_scene):
    """
    Load multiple morphologies from directory.

    NOTE: Customized version of nmv.interface.ui.common.load_morphologies(),
    adjusted to load multiple morphologies at once.

    :param panel_object:
        An object of a UI panel.

    :param context_scene:
        Current scene in the rendering context.
    """
    # Globals from this module
    # NOTE: use ui_options.morphology instead
    # global current_morphology_label
    # global current_morphology_path


    # NOTE: the difference between
    # - selected in widget: nmv.interface.ui_options.io.morphologies_input_directory 
    # - actually loaded: nmv.interface.ui_options.morphology.morphologies_loaded_directory

    # Get directory selected through widget
    input_dir = nmvif.ui_options.io.morphologies_input_directory = context_scene.MorphologiesDirectory
    loaded_dir = nmvif.ui_options.morphology.morphologies_loaded_directory 

    # Ensure that a folder has been selected
    if 'Select Directory' in input_dir:
        return None

    if (loaded_dir is not None) and (loaded_dir == input_dir):
        # Morphologies are loaded : return if same as selected
        return 'ALREADY_LOADED'

    # Global variables for keeping track of loaded objects
    nmvif.ui_morphologies = []

    # Load each morphology in input directory
    morphology_file_paths = [os.path.join(input_dir, p) for p in os.listdir(input_dir) if p.endswith('.swc')]
    for morph_path in morphology_file_paths:
        # Update the morphology label
        # morph_labels.append(nmv.file.ops.get_file_name_from_path(morph_path))    

        # Load the morphology from the file
        # NOTE: also assigns filename as label to morphology_object
        nmvif.ui_options.morphology.morphology_file_path = morph_path
        loading_flag, morphology_object = nmv.file.readers.read_morphology_from_file(
            options=nmvif.ui_options)

        if loading_flag:
            nmvif.ui_morphologies.append(morphology_object)

    return 'NEW_MORPHOLOGY_LOADED'


def sketch_morphology_skeleton_guide(morphology, options):
    """
    Sketches basic 3D shapes around the morphology skeleton to give it
    a simple geometric representation.

    NOTE: Customized version of function with same name in nmv.interface.ui.analysis_panel_ops,
    adjusted to sketch multiple morphologies at once.

    :param morphology:
        Morphology skeleton.
    :param options:
        Instance of NMV options, but it will be modified here to account for the changes we must do.
    """

    # Set the morphology options to the default after they have been already initialized
    options.morphology.set_default()
    # options.morphology.reconstruction_method = \
    #   nmv.enums.Skeletonization.Method.DISCONNECTED_SKELETON_ORIGINAL
    #   nmv.enums.Skeletonization.Method.DISCONNECTED_SECTIONS
    #   nmv.enums.Skeletonization.Method.CONNECTED_SECTION_ORIGINAL # default

    # Clear the scene
    # nmv.scene.clear_scene()

    # Create a skeletonizer object to build the morphology skeleton
    builder = nmv.builders.SkeletonBuilder(morphology, options)

    # Draw morphology skeleton and store list of reconstructed objects
    geometry = builder.draw_morphology_skeleton(
                    parent_to_soma=False, group_geometry=True)
    nmvif.ui_reconstructed_skeletons[morphology.label] = geometry
    return geometry
        

def get_morphology_from_object(blender_object):
    """
    Get the morphology object associated with a blender object.
    """
    for label, geometry_list in nmvif.ui_reconstructed_skeletons.items():
        if blender_object in geometry_list:
            # return nmvif.ui_morphologies[label]
            return next((morph for morph in nmvif.ui_morphologies if morph.label == label))
    return None

################################################################################
# Operators
################################################################################

class DbsSketchSkeleton(bpy.types.Operator):
    """
    Repair the morphology skeleton (as volumetric mesh),
    detect the artifacts and fix them.
    """

    # Operator parameters
    bl_idname = "sketch.skeleton_dbs"
    bl_label = "Sketch Skeleton"


    def execute(self, context):
        """Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """

        # Clear the scene
        # nmv.scene.ops.clear_scene()
        # NOTE: sketch_morphology_skeleton_guide also clears the scene

        # Load the morphology files
        loading_result = load_morphologies(self, context.scene)

        # If the result is None, report the issue
        if loading_result is None:
            self.report({'ERROR'}, 'Please select a morphology file')
            return {'FINISHED'}

        # Plot the morphology (whatever issues it contains)
        for morphology_object in nmvif.ui_morphologies:
            sketch_morphology_skeleton_guide(
                morphology=morphology_object,
                options=copy.deepcopy(nmvif.ui_options))

        return {'FINISHED'}



class DbsEditMorphologyCoordinates(bpy.types.Operator):
    """
    Update the morphology coordinates following to the repair process
    """

    # Operator parameters
    bl_idname = "edit.morphology_coordinates_dbs"
    bl_label = "Edit Coordinates"

    # FIXME: update operator EditMorphologyCoordinates to work with ui_morphologies
    #        variable and currently selected morphology


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """

        # Create an object of the repairer
        global morphology_editor

        # Clear the scene
        nmv.scene.ops.clear_scene()

        # Sketch the morphological skeleton for repair
        morphology_editor = nmv.edit.MorphologyEditor(
            morphology=nmvif.ui_morphology, options=nmvif.ui_options)
        morphology_editor.sketch_morphology_skeleton()

        # Switch to edit mode, to be able to export the mesh
        bpy.ops.object.mode_set(mode='EDIT')

        # The morphology is edited
        global is_skeleton_edited
        is_skeleton_edited = True

        # Update the edit mode
        global in_edit_mode
        in_edit_mode = True

        return {'FINISHED'}



class DbsUpdateMorphologyCoordinates(bpy.types.Operator):
    """
    Update the morphology coordinates following to the repair process.
    """

    # Operator parameters
    bl_idname = "update.morphology_coordinates_dbs"
    bl_label = "Update Coordinates"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """

        # Create an object of the repairer
        global morphology_editor

        # Create the morphological skeleton
        if morphology_editor is not None:

            # Switch back to object mode, to be able to export the mesh
            bpy.ops.object.mode_set(mode='OBJECT')

            # Update samples of Morphology object based on edited skeleton
            morphology_editor.update_skeleton_coordinates()

            global is_skeleton_edited
            is_skeleton_edited = False

        # Clear the scene
        nmv.scene.ops.clear_scene()

        # Plot the morphology (whatever issues it contains)
        nmvif.ui.sketch_morphology_skeleton_guide(
            morphology=nmvif.ui_morphology,
            options=copy.deepcopy(nmvif.ui_options))

        # Update the edit mode
        global in_edit_mode
        in_edit_mode = False

        return {'FINISHED'}


class DuplicateMorphology(bpy.types.Operator):
    """
    Make duplicates of selected morphology and optionally
    distribute them in space.
    """

    # Operator parameters
    bl_idname = "duplicate.morphology"
    bl_label = "Duplicate Morphology"

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

    def make_duplicate_label(self, morphology):
        """
        Generate a name for a duplicate cell.
        """
        num_copies = 0
        match = re.search(r'\.(\d+)$', morphology.label)
        if match:
            num_copies = int(match.groups()[0])
        while True:
            if num_copies >= 1e6:
                raise Exception('Too many duplicates.')
            elif num_copies >= 1e3:
                suffix = '.{:06d}'
            else:
                suffix = '.{:03d}'
            duplicate_label = morphology.label + suffix.format(num_copies)
            if not any((morph.label == duplicate_label for morph in nmvif.ui_morphologies)):
                return duplicate_label
            num_copies += 1


    def make_duplicate_origins(self, context, source_object):
        """
        Generate origin points for all cell duplicates.

        :return:
            List of points
        """
        layout_method = context.scene.DuplicationLayoutMethod # 'GRID' or 'RANDOM'
        density = context.scene.DuplicationDensity
        max_dups = context.scene.MaxCellDuplicates

        # Get bounding box of target volume
        bounds_obj = context.scene.objects[context.scene.DuplicationBoundaryName]
        bbox_corners = np.array([bounds_obj.matrix_world * mathutils.Vector(corner)
                                    for corner in bounds_obj.bound_box])
        xyz_min = bbox_corners.min(axis=0)
        xyz_max = bbox_corners.max(axis=0)
        # xyz_max = [max((corner[j] for corner in bbox_corners)) for j in range(3)]

        # Generate coordinates in bounding box of boundary volume
        if layout_method == 'GRID':
            cell_per_mm = int(density ** (1./3.))
            grid_samples = [] # one dimension (x/y/z) per row
            for i in range(3):
                ncell = int(cell_per_mm * (xyz_max[i] - xyz_min[i]))
                grid_samples.append(
                    np.linspace(xyz_min[i], xyz_max[i], num=ncell, endpoint=False))
            origins = np.array([co.ravel() for co in np.meshgrid(*grid_samples)]).T
        elif layout_method == 'RANDOM':
            pass
        else:
            raise ValueError('Unexpected layout method', layout_method)

        # Prune points that are not inside boundary volume
        inside_mask = np.zeros((max(origins.shape), 1), dtype=bool)
        for i, pt in origins:
            point, normal, face = bounds_obj.closest_point_on_mesh(pt, 1e12)
            inside_mask[i] = (point-p).dot(normal) >= 0.0
        origins = origins[inside_mask, :]

        # Ensure we don't exceed maximum number of copies
        src_loc = np.array(source_object.location)
        if origins.shape[0] > max_dups:
            # sort by distance from source location, keep closest
            dists = np.linalg.norm(origins - src_loc, axis=1)

        return origins

    ############################################################################
    # Operator override methods

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
        if context.scene.DuplicationBoundaryName == 'None':
            self.report({'ERROR'}, 'Please select a boundary volume first.')
            return {'FINISHED'}


        return self.execute(context)


    def execute(self, context):
        """
        Executes the operator.

        :param context: Operator context.
        :return: {'FINISHED'}
        """
        # Get selected morphology
        selected_object = context.scene.objects.active
        selected_morphology = get_morphology_from_object(selected_object)
        if selected_morphology is None:
            self.report({'ERROR'}, 'Please select a morphology to duplicate')
            return {'FINISHED'}


        # Get locations to place duplicates
        dup_origins = self.make_duplicate_origins(context, selected_object)

        for dup_pt in dup_origins:

            # Duplicate selected morphology
            duplicate_label = self.make_duplicate_label(selected_morphology)
            dup_morphology = selected_morphology.duplicate(label=duplicate_label)

            # Apply transformation to underlying morphology
            # xform = mathutils.Matrix.Translation(mathutils.Vector(
            #             (self.offset_x, self.offset_y, self.offset_z)))
            # dup_morphology.apply_transform(xform)

            # Sketch morphology (create geometry for skeleton)
            dup_geom_objs = sketch_morphology_skeleton_guide(
                                morphology=dup_morphology,
                                options=copy.deepcopy(nmvif.ui_options))

            # New transform is that of source object with translation to new origin
            xform_mod = selected_object.matrix_world
            xform_mod.translation = mathutils.Vector(dup_pt)

            # First apply the transforms already applied to selected objects
            # xform_prev = selected_object.matrix_world
            # xform_new = mathutils.Matrix.Translation(mathutils.Vector(
            #                 (self.offset_x, self.offset_y, self.offset_z)))

            # [if morphology updated from geometry] Transform duplicated geometry
            for geom_obj in dup_geom_objs:
                geom_obj.matrix_world = xform_mod * geom_obj.matrix_world

        return {'FINISHED'}


class SetDuplicationBoundary(bpy.types.Operator):
    """
    Update the morphology coordinates following to the repair process.
    """

    # Operator parameters
    bl_idname = "set.duplication_boundary"
    bl_label = "Set boundary volume for cell duplicates"

    bpy.types.Scene.DuplicationBoundaryName = StringProperty(
        name="DuplicationBoundaryName",
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

        nvert_nonmanifold = nmv.bmeshi.ops.count_non_manifold_vertices(context)
        if nvert_nonmanifold > 0:
            self.report({'ERROR'}, 'Selected mesh is not watertight. '
                                 'Please select a watertight mesh as boundary.')
            return {'FINISHED'}

        # Store name of boundary object for later use
        context.scene.DuplicationBoundaryName = obj.name

        return {'FINISHED'}


class DbsExportMorphologySWC(bpy.types.Operator):
    """
    Export the reconstructed morphology in an SWC file
    """

    # Operator parameters
    bl_idname = "export_morphology_dbs.swc"
    bl_label = "SWC (.swc)"

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

        # Create the meshes directory if it does not exist
        if not nmv.file.ops.path_exists(nmvif.ui_options.io.morphologies_directory):
            nmv.file.ops.clean_and_create_directory(
                nmvif.ui_options.io.morphologies_directory)

        # Export the reconstructed morphology as an .swc file
        # FIXME: update to export selected or all morphologies
        nmv.file.write_morphology_to_swc_file(
            nmvif.ui_morphology, nmvif.ui_options.io.morphologies_directory)

        return {'FINISHED'}


def register_panel():
    """
    Registers all the classes in this panel.
    """

    # Register UI Elements
    bpy.utils.register_class(DbsPositioningPanel)

    # Register Operators
    bpy.utils.register_class(DbsSketchSkeleton)
    bpy.utils.register_class(DbsEditMorphologyCoordinates)
    bpy.utils.register_class(DbsUpdateMorphologyCoordinates)
    bpy.utils.register_class(DbsExportMorphologySWC)
    bpy.utils.register_class(DuplicateMorphology)
    bpy.utils.register_class(SetDuplicationBoundary)

def unregister_panel():
    """Un-registers all the classes in this panel.
    """
    # Morphology analysis panel
    bpy.utils.unregister_class(DbsPositioningPanel)

    # Unregister Operators
    bpy.utils.unregister_class(DbsSketchSkeleton)
    bpy.utils.unregister_class(DbsEditMorphologyCoordinates)
    bpy.utils.unregister_class(DbsUpdateMorphologyCoordinates)
    bpy.utils.unregister_class(DbsExportMorphologySWC)
    bpy.utils.unregister_class(DuplicateMorphology)
    bpy.utils.unregister_class(SetDuplicationBoundary)
