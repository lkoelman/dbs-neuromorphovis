"""
Access to circuit data.

@author     Lucas Koelman
"""

# all loaded morphologies
ui_morphologies = []

# Prefix for all custom properties on Blender objects
CUSTOM_PROPERTY_PREFIX = 'NMV_'
def mkprop(property_name):
    """
    Make custom property name that is easily identifiable
    as a reserved NeuroMorphoVis property.
    """
    return CUSTOM_PROPERTY_PREFIX + property_name

# Custom Blender properties used by this module
_PROP_OBJECT_TYPE = mkprop('object_type')