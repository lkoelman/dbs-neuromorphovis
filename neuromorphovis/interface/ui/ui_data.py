####################################################################################################
# Copyright (c) 2016 - 2018, EPFL / Blue Brain Project
#               Marwan Abdellah <marwan.abdellah@epfl.ch>
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

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.options

# A global variable for the system options.
# All the parameters of the system are stored in this global variable and updated following the
# execution of an active element in the GUI.
# You can access all the parameters of the system as follows:
#   ui_options.options.io.VARIABLE : for the input/output directories
#   ui_options.options.soma.VARIABLE : for the soma options
#   ui_options.options.morphology.VARIABLE : for the morphology options
#   ui_options.options.mesh.VARIABLE : for the mesh options
#   ui_options.options.analysis.VARIABLE : for the analysis options
ui_options = nmv.options.NeuroMorphoVisOptions()

# The morphology skeleton object loaded after UI interaction.
ui_morphology = None

# The reconstructed soma mesh object
ui_soma_mesh = None

# A list of all the objects that correspond to the reconstructed morphology skeleton
ui_reconstructed_skeleton = list()

# A list of all the objects that correspond to the reconstructed mesh of the neuron
# NOTE: If this list contains a single mesh object, then it accounts for the entire mesh after
# joining all the mesh objects together
ui_reconstructed_mesh = list()

################################################################################
# NeuroCircuitVis
################################################################################

# Prefix for all custom properties on Blender objects
CUSTOM_PROPERTY_PREFIX = 'NMV_'

nmv_reserved_property_names = {}


def mkprop(property_name, dtype):
    """
    Make custom property name that is easily identifiable
    as a reserved NeuroMorphoVis property.
    """
    global nmv_reserved_property_names
    prop_name = CUSTOM_PROPERTY_PREFIX + property_name
    nmv_reserved_property_names[prop_name] = {'dtype': dtype}
    return prop_name

class NmvPropertyNames:
    """
    Custom property names for use with Blender objects.
    """
    OBJECT_TYPE = mkprop('object_type', str)

    # Neurons
    SWC_SAMPLES = mkprop('swc_samples', list)
    SWC_STRUCTURE_ID = mkprop('swc_structure_id', int)
    CELL_LABEL = mkprop('cell_label', str)
    CELL_GID = mkprop('cell_gid', int)
    POP_LABEL = mkprop('pop_label', str)
    PROJ_LABEL = mkprop('projection_label', str)

    # Streamlines
    INCLUDE_EXPORT = mkprop('include_export', bool)
    AX_PRE_GID = mkprop('presynaptic_cell_GID', int)
    AX_PRE_NAME = mkprop('presynaptic_cell_name', str)
    AX_POST_GIDS = mkprop('postsynaptic_cell_GIDs', list)

NMV_PROP = NmvPropertyNames


class NmvObjectTypes:
    """
    Types of objects in the scene distinguised by the addon.

    NOTE: don't make Enum class, since members won't be basic types
    """
    STREAMLINE = 'streamline'
    NEURON_GEOMETRY = 'neuron_geometry' # full neuron geometry
    NEURON_PROXY = 'neuron_proxy'       # proxy object for positioning neuron
    BRAIN_STRUCTURE = 'brain_structure' # anatomical brain structures
    ELECTRODE = 'electrode'             # electrode geometry

NMV_TYPE = NmvObjectTypes

NEURON_TYPES = [NMV_TYPE.NEURON_GEOMETRY, NMV_TYPE.NEURON_PROXY]

def set_nmv_type(obj, nmv_type):
    obj[NmvPropertyNames.OBJECT_TYPE] = nmv_type

def get_nmv_type(obj):
    return obj.get(NmvPropertyNames.OBJECT_TYPE, None)


class SwcSampleTypes:
    """
    SWC sample types (structure identifier).
    See http://www.neuronland.org/NLMorphologyConverter/MorphologyFormats/SWC/Spec.html

    Also defined in nmv.consts.arbor_consts.
    """
    SOMA = 1
    AXON = 2
    BASAL = 3
    APICAL = 4
    FORK_POINT = 5
    END_POINT = 6
    CUSTOM = 7

SWC_SAMPLE = SwcSampleTypes