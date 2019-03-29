"""
Panel for defining neuronal circuits and saving them to
a circuit configuration file.

@author Lucas Koelman

@date   20/03/2019
"""

# Python imports
import os
import json

# Blender imports
import bpy
from bpy.props import FloatProperty, IntProperty, StringProperty

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.interface as nmvif

################################################################################
# State variables
################################################################################

# Debugging
DEBUG = True

# Custom Blender properties used by this module
_PROP_AX_PRE_GID = nmvif.mkprop('presynaptic_cell_GID')
_PROP_AX_PRE_NAME = nmvif.mkprop('presynaptic_cell_name')
_PROP_AX_POST_GIDS = nmvif.mkprop('postsynaptic_cell_GIDs')


################################################################################
# UI elements
################################################################################

class CircuitsPanel(bpy.types.Panel):
    """
    Panel containing operators to position neuron morphology around
    DBS electrode.
    """

    # Panel parameters
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'Circuit Builder'
    bl_category = 'NeuroMorphoVis'
    bl_options = {'DEFAULT_CLOSED'}

    # --------------------------------------------------------------------------
    # Properties for UI state


    # --------------------------------------------------------------------------
    # Panel overriden methods

    def draw(self, context):
        """
        Layout UI elements in the panel.

        :param context:
            Rendering context
        """
        layout = self.layout

        # Circuit Building -----------------------------------------------------
        layout.row().label(text='Build Circuit:', icon='MOD_BUILD')

        # Populations: define population
        layout.column(align=True).operator('define.population', icon='MOD_SKIN')

        # Projections: associate axons
        layout.column(align=True).operator('axon.set_pre_cells', icon='FORCE_CURVE')
        layout.column(align=True).operator('axon.set_post_cells', icon='PARTICLE_TIP')

        # Exporting ------------------------------------------------------------

        # Saving morphology options
        layout.row().label(text='Export Circuit:', icon='LIBRARY_DATA_DIRECT')
        layout.column(align=True).operator('export.circuit')


################################################################################
# Operators
################################################################################

class DefinePopulation(bpy.types.Operator):
    """
    TODO: operator DefinePopulation
    """
    bl_idname = "define.population"
    bl_label = "Define cell population"


class SetAxonPreCell(bpy.types.Operator):
    """
    Set pre-synaptic cell for axon
    """
    bl_idname = "axon.set_pre_cells"
    bl_label = "Associate PRE cell"

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
        cell_morph = nmvif.ui.cellpos_panel.get_morphology_from_object(cell_obj)

        # Set pre-synaptic cell GID
        axon_obj[_PROP_AX_PRE_GID] = cell_morph.gid
        axon_obj[_PROP_AX_PRE_NAME] = cell_morph.label

        return {'FINISHED'}


class SetAxonPostCell(bpy.types.Operator):
    """
    Set post-synaptic cell for axon
    """
    bl_idname = "axon.set_post_cells"
    bl_label = "Associate POST cell"

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
        axon_obj[_PROP_AX_POST_GIDS] = sorted(old_post_gids.union(post_cell_gids))

        return {'FINISHED'}


class ExportCircuit(bpy.types.Operator):
    """
    Save circuit definition to file
    """
    bl_idname = "export.circuit"
    bl_label = "Export circuit definition"


    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        circuit_config = {
            'cells': [], # list[dict] with keys 'gid', 'morphology', 'transform'
            'connections': [], # list[dict] with keys 'pre_gids', 'post_gids', 'axon_id'
        }

        # Add all cells and connections
        for morphology in nmvif.ui_morphologies:
            circuit_config['cells'].append({
                'gid': morphology.gid,
                'morphology': morphology.label,
                'transform': [list(morphology.matrix_world[i]) for i in range(4)]
            })
        
        # Find axons tagged for export
        all_streamlines = nmvif.ui.tracks_panel.get_streamlines()
        for curve_obj in all_streamlines:
            circuit_config['connections'].append({
                'axon_id': curve_obj.name,
                'pre_gid': curve_obj.get(_PROP_AX_PRE_GID, None),
                'post_gids': curve_obj.get(_PROP_AX_POST_GIDS, []),
            })


        # Subdirectories for outputs are defined on io_panel.py
        out_basedir = context.scene.OutputDirectory
        out_fulldir = os.path.join(out_basedir, 'circuits')
        if not nmv.file.ops.path_exists(out_fulldir):
            nmv.file.ops.clean_and_create_directory(out_fulldir)

        # Write to JSON file
        out_fname = context.scene.CircuitName + '.json'
        out_fpath = os.path.join(out_fulldir, out_fname)
        json.dump(circuit_config, out_fpath, indent=2)

################################################################################
# GUI Registration
################################################################################

# Classes to register with Blender
_reg_classes = [
    CircuitsPanel, DefinePopulation, ExportCircuit,
    SetAxonPreCell, SetAxonPostCell
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