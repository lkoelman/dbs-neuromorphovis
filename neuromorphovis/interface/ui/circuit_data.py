"""
Access to circuit data.

@author     Lucas Koelman
"""

import bpy

# import neuromorphovis as nmv
from neuromorphovis.interface.ui.ui_data import NMV_PROP, NMV_OBJ_TYPE
from neuromorphovis.skeleton.neuron import Neuron


# all loaded neurons
neurons = []


def add_neuron(neuron):
    global neurons
    neurons.append(neuron)

    # Add to blender group
    grp_name = 'Neuron Morphologies'
    group = bpy.data.groups.get(grp_name, None)
    if group is None:
        group = bpy.data.groups.new(grp_name)
    for bobj in neuron.geometry:
        if bobj.name not in group.objects:
            group.objects.link(bobj)


def import_neuron_from_file(swc_file):
    neuron = Neuron(swc_file=swc_file, draw_geometry=True)
    add_neuron(neuron)


def restore_neurons_from_blend_data():
    for bobj in bpy.data.objects:

        # Query our custom properties
        nmv_type = bobj.get(NMV_PROP.OBJECT_TYPE, None)
        swc_type = bobj.get(NMV_PROP.SWC_STRUCTURE_ID, None)
        SOMA_TYPE = 1
        
        if (nmv_type == NMV_OBJ_TYPE.NEURON_GEOMETRY and swc_type == SOMA_TYPE):
            add_neuron(Neuron(parent_geometry=bobj, draw_geometry=False))


def add_neuron_with_geometry(parent_obj):
    """
    Add neuron with dummy geometry.
    """
    pass


def get_neuron_from_blend_object(bobj):
    """
    Get the Neuron associated with a blender object.
    """
    return next((n for n in neurons if bobj in n.geometry), None)