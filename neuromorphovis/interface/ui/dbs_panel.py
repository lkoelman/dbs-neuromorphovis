"""
Morphology import and editing panel for positioning cells around electrode.

This is a modified version of the module 'neuromorphovis.interface.ui.edit_panel'.

@author Lucas Koelman

@date   8/03/2019
"""


# System imports
import copy
import os

# Blender imports
import bpy
import bpy.props

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.edit
import neuromorphovis.interface as nmvif
import neuromorphovis.scene
import neuromorphovis.consts

# Globals
## Morphology editor
morphology_editor = None
## A flag to indicate that the morphology has been edited and ready for update
is_skeleton_edited = False
in_edit_mode = False

# Debugging
DEBUG = True
def logdebug(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# Aliases for global variables defined in module ui_data
ui_opts = nmvif.ui_options

# Info about currently loaded morphologies
ui_opts.morphology.morphologies_loaded_directory = None
ui_opts.morphology.morphologies_labels = None
# 3D objects sketched around skeletons, equivalent of nmvif.ui_reconstructed_skeleton
# for multiple morphologies, with their labels as keys
nmvif.ui_reconstructed_skeletons = dict() # dict[str, list()]

################################################################################
# Re-implementations of existing methods to support multiple morphologies
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

    # TODO: load all morphologies rather than one (ctrl + f Morphologyfile)
    # TODO: update variables in ui_data to hold multiple morphologies

    # NOTE: the difference between
    # - selected in widget: nmv.interface.ui_options.io.morphologies_input_directory 
    # - actually loaded: nmv.interface.ui_options.morphology.morphologies_loaded_directory

    # Get directory selected through widget
    input_dir = ui_opts.io.morphologies_input_directory = context_scene.MorphologiesDirectory
    loaded_dir = ui_opts.morphology.morphologies_loaded_directory 

    # Ensure that a folder has been selected
    if 'Select Directory' in input_dir:
        return None

    if (loaded_dir is not None) and (loaded_dir == input_dir):
        # Morphologies are loaded : return if same as selected
        return 'ALREADY_LOADED'

    # Global variables for keeping track of loaded objects
    morph_labels = ui_opts.morphology.morphologies_labels = []
    nmvif.ui_morphologies = []

    # Load each morphology in input directory
    morphology_file_paths = [os.path.join(input_dir, p) for p in os.listdir(input_dir) if p.endswith('.swc')]
    for morph_path in morphology_file_paths:
        # Update the morphology label
        morph_labels.append(nmv.file.ops.get_file_name_from_path(morph_path))    

        # Load the morphology from the file
        # NOTE: also assigns filename as label to morphology_object
        ui_opts.morphology.morphology_file_path = morph_path
        loading_flag, morphology_object = nmv.file.readers.read_morphology_from_file(
            options=ui_opts)

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

    # Clear the scene
    # nmv.scene.clear_scene()

    # Create a skeletonizer object to build the morphology skeleton
    builder = nmv.builders.SkeletonBuilder(morphology, options)

    # Draw morphology skeleton and store list of reconstructed objects
    nmvif.ui_reconstructed_skeletons[morphology.label] = \
        builder.draw_morphology_skeleton() # list of 3D elements


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
    bl_label = 'DBS Positioning'
    bl_category = 'NeuroMorphoVis'
    # bl_options = {'DEFAULT_CLOSED'}

    # Register a variable indicating that morphology is sketched to be able to update the UI
    bpy.types.Scene.MorphologySketched = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.MorphologyCoordinatesEdited = bpy.props.BoolProperty(default=False)

    # Morphology directory
    default_dir = "/Users/luye/Downloads/morphologies" if DEBUG else "Select Directory"
    bpy.types.Scene.MorphologiesDirectory = bpy.props.StringProperty(
        name="Morphologies",
        description="Select a directory to mesh all the morphologies in it",
        default=default_dir, maxlen=2048, subtype='DIR_PATH')


    def draw(self, context):
        """
        Layout UI elements in the panel.

        :param context:
            Rendering context
        """
        layout = self.layout
        scene = context.scene

        # Input morphologies for positioning
        morphologies_dir_row = layout.row()
        morphologies_dir_row.prop(scene, 'MorphologiesDirectory')

        # Morphology sketching button
        if not in_edit_mode:
            sketching_morphology_column = layout.column(align=True)
            sketching_morphology_column.operator('sketch.skeleton_dbs', icon='PARTICLE_POINT')

        # Reconstruction options
        edit_coordinates_row = layout.row()
        edit_coordinates_row.label(text='Editing Samples Coordinates:',
                                   icon='OUTLINER_OB_EMPTY')

        global is_skeleton_edited
        if not is_skeleton_edited:
            # Morphology edit button
            edit_morphology_column = layout.column(align=True)
            edit_morphology_column.operator('edit.morphology_coordinates_dbs',
                                            icon='MESH_DATA')
        else:
            # Morphology update buttons
            update_morphology_column = layout.column(align=True)
            update_morphology_column.operator('update.morphology_coordinates_dbs',
                                            icon='MESH_DATA')

        # Saving morphology buttons
        if not in_edit_mode:

            # Saving morphology options
            save_morphology_row = layout.row()
            save_morphology_row.label(text='Save Morphology As:', icon='MESH_UVSPHERE')

            save_morphology_buttons_column = layout.column(align=True)
            save_morphology_buttons_column.operator('export_morphology_dbs.swc',
                                                    icon='GROUP_VERTEX')

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
        logdebug('DBS: Loaded result: {}'.format(loading_result))

        # If the result is None, report the issue
        if loading_result is None:
            self.report({'ERROR'}, 'Please select a morphology file')
            return {'FINISHED'}

        # Plot the morphology (whatever issues it contains)
        for morphology_object in nmvif.ui_morphologies:
            logdebug('DBS: sketching skeleton ...')
            sketch_morphology_skeleton_guide(
                morphology=morphology_object,
                options=copy.deepcopy(ui_opts))

        return {'FINISHED'}



class DbsEditMorphologyCoordinates(bpy.types.Operator):
    """
    Update the morphology coordinates following to the repair process
    """

    # Operator parameters
    bl_idname = "edit.morphology_coordinates_dbs"
    bl_label = "Edit Coordinates"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        # TODO: enter edit mode for all morphologies or selected one

        # Create an object of the repairer
        global morphology_editor

        # Clear the scene
        nmv.scene.ops.clear_scene()

        # Sketch the morphological skeleton for repair
        morphology_editor = nmv.edit.MorphologyEditor(
            morphology=nmvif.ui_morphology, options=ui_opts)
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

            morphology_editor.update_skeleton_coordinates()

            global is_skeleton_edited
            is_skeleton_edited = False

        # Clear the scene
        nmv.scene.ops.clear_scene()

        # Plot the morphology (whatever issues it contains)
        nmvif.ui.sketch_morphology_skeleton_guide(
            morphology=nmvif.ui_morphology,
            options=copy.deepcopy(ui_opts))

        # Update the edit mode
        global in_edit_mode
        in_edit_mode = False

        return {'FINISHED'}


class DbsExportMorphologySWC(bpy.types.Operator):
    """
    Export the reconstructed morphology in an SWC file
    """

    # Operator parameters
    bl_idname = "export_morphology_dbs.swc"
    bl_label = "SWC (.swc)"

    def execute(self,
                context):
        """
        Executes the operator.

        :param context: Operator context.
        :return: {'FINISHED'}
        """

        # Ensure that there is a valid directory where the meshes will be written to
        if ui_opts.io.output_directory is None:
            self.report({'ERROR'}, nmv.consts.Messages.PATH_NOT_SET)
            return {'FINISHED'}

        if not nmv.file.ops.file_ops.path_exists(context.scene.OutputDirectory):
            self.report({'ERROR'}, nmv.consts.Messages.INVALID_OUTPUT_PATH)
            return {'FINISHED'}

        # Create the meshes directory if it does not exist
        if not nmv.file.ops.path_exists(ui_opts.io.morphologies_directory):
            nmv.file.ops.clean_and_create_directory(
                ui_opts.io.morphologies_directory)

        # Export the reconstructed morphology as an .swc file
        nmv.file.write_morphology_to_swc_file(
            nmvif.ui_morphology, ui_opts.io.morphologies_directory)

        return {'FINISHED'}


def register_panel():
    """Registers all the classes in this panel.
    """

    # Morphology analysis panel
    bpy.utils.register_class(DbsPositioningPanel)

    # Morphology analysis button
    bpy.utils.register_class(DbsSketchSkeleton)

    # Edit morphology coordinates button
    bpy.utils.register_class(DbsEditMorphologyCoordinates)

    # Morphology analysis button
    bpy.utils.register_class(DbsUpdateMorphologyCoordinates)

    # Export morphology as SWC file
    bpy.utils.register_class(DbsExportMorphologySWC)


def unregister_panel():
    """Un-registers all the classes in this panel.
    """
    # Morphology analysis panel
    bpy.utils.unregister_class(DbsPositioningPanel)

    # Morphology analysis button
    bpy.utils.unregister_class(DbsSketchSkeleton)

    # Edit morphology coordinates button
    bpy.utils.unregister_class(DbsEditMorphologyCoordinates)

    # Update the coordinates
    bpy.utils.unregister_class(DbsUpdateMorphologyCoordinates)

    # Export the morphology
    bpy.utils.unregister_class(DbsExportMorphologySWC)
