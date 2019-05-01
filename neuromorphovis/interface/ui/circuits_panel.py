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
import bgl
import blf
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
import bpy_extras.view3d_utils
from mathutils import Vector

# Third party imports
# import numpy as np

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.file.writers.json as jsonutil
from neuromorphovis.interface.ui.ui_data import (
    NMV_PROP, NMV_TYPE, NEURON_TYPES, set_nmv_type, get_nmv_type)
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

    @post   Blender object representing axon has custom property entries
            AX_PRE_GID and AX_PRE_NAME set to the presynaptic neuron's GID
            and label.
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
    Set axon target cells.

    @post   For each selected axon, all the selected neurons are appended
            the the axon's target GIDs.
    """
    bl_idname = "axon.set_post_cells"
    bl_label = "Set axon target cells"

    def execute(self, context):
        """
        Execute the operator.

        :param context:
            Rendering context
        :return:
            'FINISHED'
        """
        selected = list(context.selected_objects)

        # Get cell GID of all selected object that represent neuron geometry
        neuron_objs = circuit_data.get_geometries_of_type(
                            (NMV_TYPE.NEURON_GEOMETRY, NMV_TYPE.NEURON_PROXY),
                            selected)

        post_cell_gids = set((obj[NMV_PROP.CELL_GID] for obj in neuron_objs
                                if NMV_PROP.CELL_GID in obj.keys()))
        
        # Get blender objects representing neuron and axon
        axon_objs = circuit_data.get_geometries_of_type(
                                    NMV_TYPE.STREAMLINE, selected)

        if len(post_cell_gids) == 0 or len(axon_objs) == 0:
            self.report({'ERROR'}, 'Please select at least one axon and neuron.')
            return {'FINISHED'}

        # Set pre-synaptic cell GID
        for axon_obj in axon_objs:
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

        # TODO: change units based on saved units when importing
        circuit_config['units'] = {
            'transforms': 'um',
            'morphologies': 'um',
            'axons': 'um',
        }

        # Get all neurons and axons in the scene
        neurons = circuit_data.get_neurons()
        axons = circuit_data.get_geometries_of_type(
                                        NMV_TYPE.STREAMLINE,
                                        selector=NMV_PROP.INCLUDE_EXPORT)

        # Add all cells and connections
        for neuron in neurons:
            xform_mat = neuron.get_transform()
            xform_list = [list(xform_mat[i]) for i in range(4)]

            # Gather outgoing and incoming axosn
            efferent_axon = next(
                (ax for ax in axons if neuron.gid == ax.get(NMV_PROP.AX_PRE_GID, -1)),
                None)
            afferent_axons = set(
                [ax.name for ax in axons if 
                    neuron.gid in ax.get(NMV_PROP.AX_POST_GIDS, [])])

            circuit_config['cells'].append({
                'gid': neuron.gid,
                'morphology': neuron.label,
                'transform': jsonutil.NoIndent(xform_list),
                'axon': efferent_axon,
                'afferent_axons': afferent_axons,
            })
        
        # Find axons tagged for export
        for curve_obj in axons:
            circuit_config['connections'].append({
                'axon': curve_obj.name,
                'pre_gid': curve_obj.get(NMV_PROP.AX_PRE_GID, None),
                'post_gids': curve_obj.get(NMV_PROP.AX_POST_GIDS, []),
            })


        # Subdirectories for outputs are defined on io_panel.py
        out_basedir = context.scene.OutputDirectory
        out_fulldir = os.path.join(out_basedir, 'cells')
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



class OverlayCustomProperty(bpy.types.Operator):
    """
    Overlay custom property on screen.
    """

    bl_idname = "overlay.property_custom"
    bl_label = "Overlay custom property on screen"

    # Operator arguments
    default_prop_name = 'Select' # "/".join((NMV_PROP.OBJECT_TYPE,
                                 # NMV_PROP.POP_LABEL,
                                 # NMV_PROP.INCLUDE_EXPORT))

    default_candidates = [(item, item, 'Property "{}"'.format(item)) for 
                            item in (default_prop_name,
                                      NMV_PROP.OBJECT_TYPE,
                                      NMV_PROP.POP_LABEL,
                                      NMV_PROP.CELL_GID,
                                      NMV_PROP.INCLUDE_EXPORT)]
    user_prop_name = StringProperty(
                    name="Custom property name",
                    description="Name of custom property",
                    default=default_prop_name) # NMV_PROP.POP_LABEL

    candidate_prop_names = EnumProperty(
                    name='NMV Properties',
                    items=default_candidates)


    def invoke(self, context, event):

        if (self.user_prop_name == self.default_prop_name == self.candidate_prop_names):
            # Show interactive window to choose property name
            return context.window_manager.invoke_props_dialog(self, width = 400)

        if context.area.type == 'VIEW_3D':
            return self.execute(context)
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


    def execute(self, context):
        """
        Need this for changing properties in dialog window (redo support)
        """
        if self.user_prop_name == self.default_prop_name:
            self.prop_name = self.candidate_prop_names
        else:
            self.prop_name = self.user_prop_name
        
        if context.area.type == 'VIEW_3D':
            # the arguments we pass the the callback
            args = (context,)
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                                self.draw_labels_callback, args, 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'FINISHED'}


    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE':
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        else:
            # Keep running and drawing
            return {'PASS_THROUGH'} # PASS_THROUGH allows interaction, RUNNING_MODAL blocks

#    def draw(self, context):
#        """
#        Draw the props dialog window. Not needed for operator properties.
#        """
#        self.layout.row().prop(self, "prop_name")

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
            label = obj.get(self.prop_name, None)
            if label is None:
                continue
            label = str(label)

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
                blf.draw(font_id, label)


class ShowAxonPrePostCells(bpy.types.Operator):
    """
    Show axon source and target cells.
    """

    bl_idname = "axon.show_pre_post"
    bl_label = "Show axon source and target cells."


    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            return self.execute(context)
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


    def execute(self, context):
        """
        Need this for changing properties in dialog window (redo support)
        """
        if context.active_object.get(NMV_PROP.OBJECT_TYPE, None) != NMV_TYPE.STREAMLINE:
            self.report({'ERROR'}, 'Must select axon/streamline object.')
            return {'CANCELLED'}

        self.make_draw_data(context)
        
        if context.area.type == 'VIEW_3D':
            # the arguments we pass the the callback
            args = tuple()
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            # draw in 2d with 'POST_PIXEL'
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                                self.draw_callback, args, 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        
        return {'FINISHED'}


    def draw_callback(self):
        # 50% alpha, 2 pixel width line
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(1.0, 0.0, 0.0, 0.7)
        bgl.glLineWidth(2)

        # Draw POST cell to end
        for loc in self.post_cells_locs:
            bgl.glBegin(bgl.GL_LINES) # bgl.GL_LINE_STRIP for 
            bgl.glVertex3f(*self.axon_end_pt)
            bgl.glVertex3f(*loc)
            bgl.glEnd()

        # Draw PRE cell to start
        for loc in self.pre_cells_locs:
            bgl.glBegin(bgl.GL_LINES) # bgl.GL_LINE_STRIP for 
            bgl.glVertex3f(*self.axon_start_pt)
            bgl.glVertex3f(*loc)
            bgl.glEnd()


        # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


    def make_draw_data(self, context):
        """
        Calculate data for drawing.
        """
        axon_obj = context.active_object

        # Get pre and post cell locations
        axon_pre_gid = axon_obj.get(NMV_PROP.AX_PRE_GID, None)
        axon_post_gids = axon_obj.get(NMV_PROP.AX_POST_GIDS, [])

        pre_cell_objs = circuit_data.get_geometries_of_type(
            NEURON_TYPES, context.scene.objects,
            selector=lambda obj: obj.get(NMV_PROP.CELL_GID, None) == axon_pre_gid)

        post_cell_objs = circuit_data.get_geometries_of_type(
            NEURON_TYPES, context.scene.objects,
            selector=lambda obj: obj.get(NMV_PROP.CELL_GID, None) in axon_post_gids)


        self.pre_cells_locs = [obj.matrix_world.translation for obj in pre_cell_objs]
        self.post_cells_locs = [obj.matrix_world.translation for obj in post_cell_objs]

        # Get axon start and end
        spl = axon_obj.data.splines[0] # also works for polylines
        self.axon_ends = [
            (axon_obj.matrix_world * spl.points[i].co).to_3d() for i in (0, -1)
        ]

        end2pre_dists = [(self.pre_cells_locs[0] - end).length for end in self.axon_ends]
        if end2pre_dists[0] < end2pre_dists[1]:
            self.axon_start_pt = self.axon_ends[0]
            self.axon_end_pt = self.axon_ends[1]
        else:
            self.axon_start_pt = self.axon_ends[1]
            self.axon_end_pt = self.axon_ends[0]


    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE':
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        else:
            # Keep running and drawing
            return {'PASS_THROUGH'} # PASS_THROUGH allows interaction, RUNNING_MODAL blocks


################################################################################
# GUI Registration
################################################################################

# Classes to register with Blender
_reg_classes = [
    CircuitsPanel, DefinePopulation, AssignPopulation, ExportCircuit,
    SetAxonPreCell, SetAxonPostCell, OverlayCustomProperty, ShowAxonPrePostCells
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