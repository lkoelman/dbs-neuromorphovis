"""
Access to circuit data.

@author     Lucas Koelman
"""

import re

import bpy

# import neuromorphovis as nmv
from neuromorphovis.interface.ui import ui_data
from neuromorphovis.interface.ui.ui_data import NMV_PROP, NMV_TYPE
from neuromorphovis.skeleton.neuron import Neuron

nmv_group_names = {
    NMV_TYPE.NEURON_GEOMETRY: 'Neuron Morphologies',
    NMV_TYPE.BRAIN_STRUCTURE: 'Brain Structures',
}

# all neurons in the scene
neurons = {} # GID -> Neuron

# Settings for building geometries from morphology definitions
morph_3d_options = ui_data.ui_options
morph_3d_options.morphology.set_default()
# options.morphology.reconstruction_method = \
    #   nmv.enums.Skeletonization.Method.DISCONNECTED_SKELETON_ORIGINAL
    #   nmv.enums.Skeletonization.Method.DISCONNECTED_SECTIONS
    #   nmv.enums.Skeletonization.Method.CONNECTED_SECTION_ORIGINAL # default

################################################################################
# PERSISTENCE
################################################################################

@bpy.app.handlers.persistent
def restore_neurons_from_blend_data(scene):
    for bobj in bpy.data.objects:

        # Query our custom properties
        nmv_type = bobj.get(NMV_PROP.OBJECT_TYPE, None)
        swc_type = bobj.get(NMV_PROP.SWC_STRUCTURE_ID, None)
        SOMA_TYPE = 1
        
        if (nmv_type == NMV_TYPE.NEURON_GEOMETRY and swc_type == SOMA_TYPE):
            add_neuron(Neuron(parent_geometry=bobj, draw_geometry=False))


@bpy.app.handlers.persistent
def save_neurons_to_blend_data(scene):
    for neuron in neurons.values():
        neuron.serialize_to_blend()


@bpy.app.handlers.persistent
def create_nmv_groups(scene):
    """
    Create blender object groups for grouping objects managed by the addon.
    """
    for grp_name in nmv_group_names.values():
        group = bpy.data.groups.get(grp_name, None)
        if group is None:
            group = bpy.data.groups.new(grp_name)


def register_handlers():
    bpy.app.handlers.load_post.append(create_nmv_groups)
    bpy.app.handlers.load_post.append(restore_neurons_from_blend_data)
    bpy.app.handlers.load_post.append(save_neurons_to_blend_data)


################################################################################
# CIRCUIT MANAGEMENT
################################################################################

def add_neuron(neuron):
    global neurons
    neurons[neuron.gid] = neuron

    # Get group object for neurons
    grp_name = 'Neuron Morphologies'
    group = bpy.data.groups.get(grp_name, None)
    if group is None:
        group = bpy.data.groups.new(grp_name)
    
    # Add neuron's geometry to group
    for bobj in neuron.geometry:
        if bobj.name not in group.objects:
            group.objects.link(bobj)

def get_neurons():
    return neurons.values()

def import_neuron_from_file(swc_file):
    neuron = Neuron(swc_file=swc_file,
                    draw_geometry=True,
                    draw_options=morph_3d_options)
    add_neuron(neuron)


def add_neuron_with_geometry(parent_obj):
    """
    Add neuron with dummy geometry.
    """
    pass


def get_neuron_from_blend_object(bobj):
    """
    Get the Neuron associated with a blender object.

    :return:
        Neuron object represented by the blend geometry, or None
        if no neuron found.
    """
    # return next((n for n in neurons if bobj in n.geometry), None)
    gid = bobj.get(NMV_PROP.CELL_GID, None)
    return neurons.get(gid, None)


def get_neurons_from_blend_objects(selected):
    """
    Get all Neurons associated with blend objects in selection.

    :param selected:
        list(blender object)
    """
    gids = set((obj[NMV_PROP.CELL_GID] for obj in selected if 
                NMV_PROP.CELL_GID in obj.keys()))
    return [neurons[gid] for gid in gids if gid in neurons.keys()]


def get_neuron_geometries_from_selection(selected):
    """
    Get all objects representing neuron geometries from selection.
    """
    return [obj for obj in selected if
        obj.get(NMV_PROP.OBJECT_TYPE, None) == NMV_TYPE.NEURON_GEOMETRY]

def get_geometries_of_type(nmv_type, selected, selector=None):
    """
    Get only the blender objects that represent the given NMV object type
    (neuron, streamline, electrode, ...).

    :param nmv_type:
        ui_data.NmvObjectTypes (NMV_TYPE)
    """
    if isinstance(nmv_type, str):
        nmv_type = [nmv_type]

    if selector is None:
        filter_func = lambda crv: True
    elif isinstance(selector, str):
        filter_func = lambda crv: crv.get(selector, False)
    else:
        # assume selector is callable
        filter_func = selector

    return [obj for obj in selected if (
                (obj.get(NMV_PROP.OBJECT_TYPE, None) in nmv_type)
                and (filter_func(obj)))]


def make_duplicate_label(neuron):
    """
    Generate a name for a duplicate cell.
    """
    # Check if morphology is a copy (ends in '.<digits>')
    match = re.search(r'\.(\d+)$', neuron.label)
    if match:
        num_copies = int(match.groups()[0])
    else:
        num_copies = 0
    # Increment digits to name the duplicate
    while True:
        num_copies += 1
        if num_copies >= 1e6:
            raise Exception('Too many duplicates.')
        elif num_copies >= 1e3:
            suffix = '.{:06d}'
        else:
            suffix = '.{:03d}'
        duplicate_label = neuron.label + suffix.format(num_copies)
        if not any((n.label == duplicate_label for n in neurons.values())):
            return duplicate_label


