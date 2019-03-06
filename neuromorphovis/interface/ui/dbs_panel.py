####################################################################################################
# Copyright (c) 2016 - 2018, EPFL / Blue Brain Project
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


# System imports
import copy

# Blender imports
import bpy
from bpy.props import BoolProperty

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.edit
import neuromorphovis.interface
import neuromorphovis.scene
import neuromorphovis.consts

# Globals
# Morphology editor
morphology_editor = None

# A flag to indicate that the morphology has been edited and ready for update
is_skeleton_edited = False
in_edit_mode = False



class DbsPositioningPanel(bpy.types.Panel):
    """
    Panel containing operators to position neuron morphology around
    DBS electrode.
    """

    # Panel parameters
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'DBS Morphology Positioning'
    bl_category = 'NeuroMorphoVis'
    bl_options = {'DEFAULT_CLOSED'}

    # Register a variable that indicates that the morphology is sketched to be able to update the UI
    bpy.types.Scene.MorphologySketched = BoolProperty(default=False)
    bpy.types.Scene.MorphologyCoordinatesEdited = BoolProperty(default=False)

    # Morphology directory 
    bpy.types.Scene.MorphologiesDirectory = StringProperty(
        name="SWC Directory",
        description="Select a directory to mesh all the morphologies in it",
        default="Select Directory", maxlen=2048, subtype='DIR_PATH')


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
            sketching_morphology_column.operator('sketch.skeleton', icon='PARTICLE_POINT')

        # Reconstruction options
        edit_coordinates_row = layout.row()
        edit_coordinates_row.label(text='Editing Samples Coordinates:',
                                   icon='OUTLINER_OB_EMPTY')

        global is_skeleton_edited
        if not is_skeleton_edited:
            # Morphology edit button
            edit_morphology_column = layout.column(align=True)
            edit_morphology_column.operator('edit.morphology_coordinates', icon='MESH_DATA')
        else:
            # Morphology update buttons
            update_morphology_column = layout.column(align=True)
            update_morphology_column.operator('update.morphology_coordinates', icon='MESH_DATA')

        # Saving morphology buttons
        if not in_edit_mode:

            # Saving morphology options
            save_morphology_row = layout.row()
            save_morphology_row.label(text='Save Morphology As:', icon='MESH_UVSPHERE')

            save_morphology_buttons_column = layout.column(align=True)
            save_morphology_buttons_column.operator('export_morphology.swc', icon='GROUP_VERTEX')


class SketchSkeleton(bpy.types.Operator):
    """
    Repair the morphology skeleton, detect the artifacts and fix them
    """

    # Operator parameters
    bl_idname = "sketch.skeleton"
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

        # Load the morphology files
        loading_result = nmv.interface.ui.load_morphologies(self, context.scene)

        # If the result is None, report the issue
        if loading_result is None:
            self.report({'ERROR'}, 'Please select a morphology file')
            return {'FINISHED'}

        # Plot the morphology (whatever issues it contains)
        nmv.interface.ui.sketch_morphology_skeleton_guide(
            morphology=nmv.interface.ui_morphology,
            options=copy.deepcopy(nmv.interface.ui_options))

        return {'FINISHED'}


def load_morphologies(panel_object, context_scene):
    """
    Load morphologies from directory.

    :param panel_object:
        An object of a UI panel.

    :param context_scene:
        Current scene in the rendering context.
    """

    global current_morphology_label
    global current_morphology_path

    # Read the data from a given morphology file either in .h5 or .swc formats
    if bpy.context.scene.InputSource == nmv.enums.Input.H5_SWC_FILE:

        # Pass options from UI to system
        nmv.interface.ui_options.morphology.morphology_file_path = context_scene.MorphologyFile

        # Ensure that a file has been selected
        if 'Select File' in context_scene.MorphologyFile:
            return None

        # If no morphologies are loaded
        if current_morphology_path is None:

            # Update the morphology label
            nmv.interface.ui_options.morphology.label = nmv.file.ops.get_file_name_from_path(
                context_scene.MorphologyFile)

        # If there is file that is loaded
        else:

            # If the same path, then return
            if current_morphology_path == nmv.interface.ui_options.morphology.morphology_file_path:
                return 'ALREADY_LOADED'

        # Load the morphology from the file
        loading_flag, morphology_object = nmv.file.readers.read_morphology_from_file(
            options=nmv.interface.ui_options)

        # Verify the loading operation
        if loading_flag:
            # Update the morphology
            nmv.interface.ui_morphology = morphology_object

        # Otherwise, report an ERROR
        else:
            panel_object.report({'ERROR'}, 'Invalid Morphology File')

            # None
            return None

    else:
        # Report an invalid input source
        panel_object.report({'ERROR'}, 'Invalid Input Source')

        # None
        return None

    return 'NEW_MORPHOLOGY_LOADED'


class EditMorphologyCoordinates(bpy.types.Operator):
    """Update the morphology coordinates following to the repair process
    """

    # Operator parameters
    bl_idname = "edit.morphology_coordinates"
    bl_label = "Edit Coordinates"


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
            morphology=nmv.interface.ui_morphology, options=nmv.interface.ui_options)
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



class UpdateMorphologyCoordinates(bpy.types.Operator):
    """Update the morphology coordinates following to the repair process.
    """

    # Operator parameters
    bl_idname = "update.morphology_coordinates"
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
        nmv.interface.ui.sketch_morphology_skeleton_guide(
            morphology=nmv.interface.ui_morphology,
            options=copy.deepcopy(nmv.interface.ui_options))

        # Update the edit mode
        global in_edit_mode
        in_edit_mode = False

        return {'FINISHED'}


class ExportMorphologySWC(bpy.types.Operator):
    """
    Export the reconstructed morphology in an SWC file
    """

    # Operator parameters
    bl_idname = "export_morphology.swc"
    bl_label = "SWC (.swc)"

    def execute(self,
                context):
        """
        Executes the operator.

        :param context: Operator context.
        :return: {'FINISHED'}
        """

        # Ensure that there is a valid directory where the meshes will be written to
        if nmv.interface.ui_options.io.output_directory is None:
            self.report({'ERROR'}, nmv.consts.Messages.PATH_NOT_SET)
            return {'FINISHED'}

        if not nmv.file.ops.file_ops.path_exists(context.scene.OutputDirectory):
            self.report({'ERROR'}, nmv.consts.Messages.INVALID_OUTPUT_PATH)
            return {'FINISHED'}

        # Create the meshes directory if it does not exist
        if not nmv.file.ops.path_exists(nmv.interface.ui_options.io.morphologies_directory):
            nmv.file.ops.clean_and_create_directory(
                nmv.interface.ui_options.io.morphologies_directory)

        # Export the reconstructed morphology as an .swc file
        nmv.file.write_morphology_to_swc_file(
            nmv.interface.ui_morphology, nmv.interface.ui_options.io.morphologies_directory)

        return {'FINISHED'}


def register_panel():
    """Registers all the classes in this panel.
    """

    # Morphology analysis panel
    bpy.utils.register_class(DbsPositioningPanel)

    # Morphology analysis button
    bpy.utils.register_class(SketchSkeleton)

    # Edit morphology coordinates button
    bpy.utils.register_class(EditMorphologyCoordinates)

    # Morphology analysis button
    bpy.utils.register_class(UpdateMorphologyCoordinates)

    # Export morphology as SWC file
    bpy.utils.register_class(ExportMorphologySWC)


def unregister_panel():
    """Un-registers all the classes in this panel.
    """

    # Morphology analysis panel
    bpy.utils.unregister_class(DbsPositioningPanel)

    # Morphology analysis button
    bpy.utils.unregister_class(SketchSkeleton)

    # Edit morphology coordinates button
    bpy.utils.unregister_class(EditMorphologyCoordinates)

    # Update the coordinates
    bpy.utils.unregister_class(UpdateMorphologyCoordinates)

    # Export the morphology
    bpy.utils.unregister_class(ExportMorphologySWC)
