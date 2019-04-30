"""
Panel for defining neuronal circuits and saving them to
a circuit configuration file.

@author Lucas Koelman

@date   20/03/2019
"""

# Python imports
import os
import json
import collections

# Blender imports
# import bgl
import blf
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
import bpy_extras.view3d_utils
from mathutils import Vector

# Third party imports
# import numpy as np

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.interface as nmvif
import neuromorphovis.file.writers.json as jsonutil
from neuromorphovis.interface.ui.ui_data import NMV_PROP, NMV_TYPE, set_nmv_type, get_nmv_type
from neuromorphovis.interface.ui import circuit_data

################################################################################
# State variables
################################################################################

# Debugging
DEBUG = True

pop_items = [
    ('STN', 'STN', 'Subthalamic Nucleus'),
    ('GPE', 'GPe', 'Globus Pallidus external segment'),
    ('GPi', 'GPi', 'GPi or EPN'),
    ('CTX', 'Ctx', 'Cortex')
]


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

    bpy.types.Scene.CircuitName = StringProperty(
        name="Circuit Name",
        description="Name for exported circuit",
        default='unnamed-circuit')

    bpy.types.Scene.ExportStreamlinesWithConfig = BoolProperty(
        name="Export streamlines with config.",
        description="Export streamlines again when writing circuit config.",
        default=True)

    
    bpy.types.Scene.DefinedPopLabels = EnumProperty(
        name='Populations',
        items=pop_items)
    # bpy.types.Scene.DefinedPopLabels = bpy.props.CollectionProperty(
    #     type=bpy.types.StringProperty) # TODO: figure out CollectionProperty

    bpy.types.Scene.NewPopLabel = StringProperty(
        name="Population Label",
        description="Label for new population",
        default='POP.X')

    # bpy.types.Scene.AssignedPopLabel = StringProperty(
    #     name="Population Label",
    #     description="Label assigned to population",
    #     default='CTX')



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

        # Assign population to cells
        layout.row().prop(context.scene, 'DefinedPopLabels')
        # layout.row().prop_search(context.scene, 'AssignedPopLabel',
        #                          context.scene, 'ExistingPopLabels')
        layout.column(align=True).operator(AssignPopulation.bl_idname,
                                            icon='MOD_SKIN')

        # Define a new population label
        layout.row().prop(context.scene, 'NewPopLabel')
        layout.column(align=True).operator(DefinePopulation.bl_idname)

        # Projections: associate axons
        layout.column(align=True).operator(SetAxonPreCell.bl_idname, 
                                            icon='FORCE_CURVE')
        layout.column(align=True).operator(SetAxonPostCell.bl_idname,
                                            icon='PARTICLE_TIP')

        # Exporting ------------------------------------------------------------
        layout.row().label(text='Export Circuit:', icon='LIBRARY_DATA_DIRECT')

        layout.row().prop(context.scene, 'CircuitName')
        layout.row().prop(context.scene, 'ExportStreamlinesWithConfig')
        layout.column(align=True).operator(ExportCircuit.bl_idname, icon='FILE_SCRIPT')


################################################################################
# Operators
################################################################################

class DefinePopulation(bpy.types.Operator):
    """
    Define a new cell population
    """
    bl_idname = "define.population"
    bl_label = "Define population"

    def execute(self, context):
        global pop_items
        new_pop = context.scene.NewPopLabel
        labels = [pop_def[0] for pop_def in pop_items]
        if new_pop in labels:
            self.report({'ERROR'}, 'Population "{}" already defined'.format(new_pop))
            return {'FINISHED'}

        pop_items.append((new_pop, new_pop,
                        "User-defined population '{}'".format(new_pop)))

        # Re-define property
        bpy.types.Scene.DefinedPopLabels = EnumProperty(
                                            name='Populations',
                                            items=pop_items)

        return {'FINISHED'}


class AssignPopulation(bpy.types.Operator):
    """
    Assign population label to cells.
    """
    bl_idname = "assign.population"
    bl_label = "Assign population"

    def execute(self, context):
        num_assigned = 0
        new_label = context.scene.DefinedPopLabels
        for obj in context.selected_objects:
            nmv_type = get_nmv_type(obj)

            # Check if object represents a neuron cell
            if nmv_type is None:
                set_nmv_type(obj, NMV_TYPE.NEURON_PROXY)
            elif nmv_type != NMV_TYPE.NEURON_GEOMETRY:
                continue

            obj[NMV_PROP.POP_LABEL] = new_label
            num_assigned += 1

        self.report({'INFO'}, "Aded {} neurons to population '{}'".format(
                   num_assigned, new_label))
        return {'FINISHED'}


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

        # Get selected neuron
        selected_neurons = circuit_data.get_neurons_from_blend_objects(selected)
        if len(selected_neurons) != 1:
            self.report({'ERROR'}, 'Please select exactly one neuron geometry.')
            return {'FINISHED'}
        neuron = selected_neurons[0]
        
        # Get selected streamline
        selected_axons = circuit_data.get_geometries_of_type(NMV_TYPE.STREAMLINE)
        if len(selected_axons) == 0:
            self.report({'ERROR'}, 'Please select at least one axon curve.')
            return {'FINISHED'}

        # Set pre-synaptic cell GID
        for axon_obj in selected_axons:
            axon_obj[NMV_PROP.AX_PRE_GID] = neuron.gid
            axon_obj[NMV_PROP.AX_PRE_NAME] = neuron.label

        # Also toggle the axon for export
        bpy.ops.axon.toggle_export(export=True, toggle=False)

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
        axon_obj[NMV_PROP.AX_POST_GIDS] = sorted(old_post_gids.union(post_cell_gids))

        # Also toggle the axon for export
        bpy.ops.axon.toggle_export(export=True, toggle=False)

        return {'FINISHED'}


class ExportCircuit(bpy.types.Operator):
    """
    Save circuit configuration to file

    The circuit configuration is a JSON file with following layout:

    {
        'cells': [
            {
                'gid': <int>,               (gid ig cell)
                'morphology': <string/None>,(name of morphology)
                'transform': <list/None>,   (4x4 transform matrix)
            },
            ...
        ],
        'connections': [
            {
                'axon': <string>,           (name of axon curve in blend file)
                'pre_gid': <int>,           (gid of source cell for axon)
                'post_gids': <list[int]>,   (gids of target cells for axon)
            }
        ]
    }
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
        circuit_config = collections.OrderedDict()
        circuit_config['cells'] = []
        circuit_config['connections'] = []

        # Add all cells and connections
        for neuron in circuit_data.get_neurons():
            xform_mat = neuron.get_transform()
            xform_list = [list(xform_mat[i]) for i in range(4)]
            circuit_config['cells'].append({
                'gid': neuron.gid,
                'morphology': neuron.label,
                'transform': jsonutil.NoIndent(xform_list)
            })
        
        # Find axons tagged for export
        streamlines = nmvif.ui.tracks_panel.get_streamlines(
                            selector='INCLUDE_EXPORT')
        for curve_obj in streamlines:
            circuit_config['connections'].append({
                'axon': curve_obj.name,
                'pre_gid': curve_obj.get(NMV_PROP.AX_PRE_GID, None),
                'post_gids': curve_obj.get(NMV_PROP.AX_POST_GIDS, []),
            })


        # Subdirectories for outputs are defined on io_panel.py
        out_basedir = context.scene.OutputDirectory
        out_fulldir = os.path.join(out_basedir, 'circuits')
        if not nmv.file.ops.path_exists(out_fulldir):
            nmv.file.ops.clean_and_create_directory(out_fulldir)

        # Write to JSON file
        out_fname = context.scene.CircuitName + '.json'
        out_fpath = os.path.join(out_fulldir, out_fname)
        with open(out_fpath, 'w') as f:
            json.dump(circuit_config, f, indent=2, cls=jsonutil.VariableIndentEncoder)

        # Write streamlines if requested
        if context.scene.ExportStreamlinesWithConfig:
            bpy.ops.export.streamlines()

        return {'FINISHED'}


def draw_labels_callback(self, context):
    """
    Callback function for drawing on the screen.
    """

    # camera = context.scene.camera # first needs to be aligned with view
    font_id = 0  # XXX, need to find out how best to get this.
    font_size = 10

    # area = context.area # next((a for a in context.screen.areas if a.type == 'VIEW_3D'))
    viewport = context.region # area.regions[4]
    region = context.space_data.region_3d # area.spaces[0].region_3d

    for obj in context.scene.objects:

        # Check if it's a neuron with population label
        if get_nmv_type(obj) not in (NMV_TYPE.NEURON_GEOMETRY,
                                     NMV_TYPE.NEURON_PROXY):
            continue
        pop_label = obj.get(NMV_PROP.POP_LABEL, None)
        if pop_label is None:
            continue

        # Get bounding box
        # bbox_corners = np.array([obj.matrix_world * Vector(corner)
        #                                 for corner in obj.bound_box])
        # xyz_min = bbox_corners.min(axis=0)
        # xyz_max = bbox_corners.max(axis=0)
        # world_loc = Vector(0.5 * (xyz_min + xyz_max))
        world_loc = obj.matrix_world.translation

        # Get screen position of object
        # ALT1: camera.getScreenPosition(obj)
        # ALT2: bpy_extras.view3d_utils.location_3d_to_region_2d(...)
        # ALT3: bpy_extras.object_utils.world_to_camera_view(scene, camera_obj, co_3d)

        # screen_loc = bpy_extras.object_utils.world_to_camera_view(
        #                 context.scene, camera, world_loc)

        # view_mat = context.space_data.region_3d.perspective_matrix
        # total_mat = view_mat * obj.matrix_world
        # screen_loc = total_mat.translation # (0, 0, 0) in object spac 

        screen_loc = bpy_extras.view3d_utils.location_3d_to_region_2d(
                                                viewport, region, world_loc)

        # draw some text
        if screen_loc:
            x, y = screen_loc[0:2]
            blf.position(font_id, x, y, 0.0)
            blf.size(font_id, font_size, 72)
            blf.draw(font_id, pop_label)


class ShowPopLabels(bpy.types.Operator):
    """
    Show population labels on the screen
    """

    bl_idname = "populations.show_labels"
    bl_label = "Show population labels on the screen"

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            pass

        elif event.type == 'LEFTMOUSE':
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}


    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            # the arguments we pass the the callback
            args = (self, context)
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                                draw_labels_callback, args, 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


################################################################################
# GUI Registration
################################################################################

# Classes to register with Blender
_reg_classes = [
    CircuitsPanel, DefinePopulation, AssignPopulation, ExportCircuit,
    SetAxonPreCell, SetAxonPostCell, ShowPopLabels
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