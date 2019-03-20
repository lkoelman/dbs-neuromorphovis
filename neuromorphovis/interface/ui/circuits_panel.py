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

################################################################################
# State variables
################################################################################

# Debugging
DEBUG = True

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
        scene = context.scene


        # Populations: define population
        layout.column(align=True).operator('define.population', icon='MOD_PARTICLES')

        # Projections: associate axons
        layout.column(align=True).operator('set_axon.pre', icon='MOD_PARTICLES')
        layout.column(align=True).operator('set_axon.post', icon='MOD_PARTICLES')

        # Saving morphology options
        row_export = layout.row()
        row_export.label(text='Export Circuit:', icon='LIBRARY_DATA_DIRECT')

        # Output directory
        output_directory_row = layout.row()
        output_directory_row.prop(scene, 'StreamlinesOutputDirectory')

        col_export = layout.column(align=True)
        col_export.operator('export.circuit', icon='SAVE_COPY')


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
    TODO: operator SetAxonPreCell
    """
    bl_idname = "set_axon.pre"
    bl_label = "Set pre-synaptic cell for axon"


class SetAxonPostCell(bpy.types.Operator):
    """
    TODO: operator SetAxonPostCell
    """
    bl_idname = "set_axon.post"
    bl_label = "Set post-synaptic cell for axon"


class ExportCircuit(bpy.types.Operator):
    """
    TODO: operator ExportCircuit
    """
    bl_idname = "export.circuit"
    bl_label = "Save circuit definition to file"


# Classes to register with Blender
_reg_classes = [
    CircuitsPanel, DefinePopulation, SetAxonPreCell, SetAxonPostCell,
    ExportCircuit
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