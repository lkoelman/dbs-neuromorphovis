####################################################################################################
# Copyright (c) 2016 - 2018, EPFL / Blue Brain Project
#               Marwan Abdellah <marwan.abdellah@epfl.ch>
#
# This file is part of NeuroMorphoVis <https://github.com/BlueBrain/NeuroMorphoVis>
#
# This library is free software; you can redistribute it and/or modify it under the terms of the
# GNU Lesser General Public License version 3.0 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this library;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA.
####################################################################################################

__author__      = "Marwan Abdellah"
__copyright__   = "Copyright (c) 2016 - 2018, Blue Brain Project / EPFL"
__credits__     = ["Ahmet Bilgili", "Juan Hernando", "Stefan Eilemann"]
__version__     = "1.0.0"
__maintainer__  = "Marwan Abdellah"
__email__       = "marwan.abdellah@epfl.ch"
__status__      = "Production"


####################################################################################################
# @Args
####################################################################################################
class Args:
    """System arguments
    """

    ################################################################################################
    # @__init__
    ################################################################################################
    def __init__(self):
        pass

    ################################################################################################
    # Blender arguments
    ################################################################################################
    # Executable
    BLENDER_EXECUTABLE = '--blender'

    ################################################################################################
    # Input arguments
    ################################################################################################
    # What is the input source to the workflow
    INPUT_SOURCE = '--input'

    # A single morphology file
    MORPHOLOGY_FILE = '--morphology-file'

    # A directory containing a group of morphology files
    MORPHOLOGY_DIRECTORY = '--morphology-directory'

    # A single GID
    GID = '--gid'

    # A cell target composed of multiple GIDs
    TARGET = '--target'

    # A path to a blue config or circuit file
    BLUE_CONFIG = '--blue-config'

    ################################################################################################
    # Output arguments
    ################################################################################################
    # The root output directory
    OUTPUT_DIRECTORY = '--output-directory'

    ################################################################################################
    # Soma arguments
    ################################################################################################
    # Soma stiffness
    SOMA_STIFFNESS = '--soma-stiffness'

    # Soma subdivision level
    SOMA_SUBDIVISION_LEVEL = '--soma-subdivision-level'

    ################################################################################################
    # Morphology arguments
    ################################################################################################
    # Reconstruct the morphology skeleton
    RECONSTRUCT_MORPHOLOGY_SKELETON = '--reconstruct-morphology-skeleton'

    # Morphology reconstruction algorithm
    MORPHOLOGY_RECONSTRUCTION_ALGORITHM = '--morphology-reconstruction-algorithm'

    # Morphology skeleton
    MORPHOLOGY_SKELETON = '--morphology-skeleton'

    # Soma representation
    SOMA_REPRESENTATION = '--soma-representation'

    # Ignore axon
    IGNORE_AXON = '--ignore-axon'

    # Ignore apical dendrites
    IGNORE_APICAL_DENDRITES = '--ignore-apical-dendrites'

    # Ignore basal dendrites
    IGNORE_BASAL_DENDRITES = '--ignore-basal-dendrites'

    # Build spines (ignore, circuit or random)
    SPINES = '--spines'

    # Random spines percentage
    RANDOM_SPINES_PERCENTAGE = '--random-spines-percentage'

    # Spines quality (HQ, LQ)
    SPINES_QUALITY = '--spines-quality'

    # Axon branching order
    AXON_BRANCHING_ORDER = '--axon-branching-order'

    # Apical dendrites branching order
    APICAL_DENDRITES_BRANCHING_ORDER = '--basal-dendrites-branching-order'

    # Basal dednrites branching order
    BASAL_DENDRITES_BRANCHING_ORDER = '--apical-dendrites-branching-order'

    # Sections radii
    SECTIONS_RADII = '--sections-radii'

    # Radii scale factor
    RADII_SCALE_FACTOR = '--radii-scale-factor'

    # Radii fixed section
    FIXED_SECTION_RADIUS = '--fixed-section-radius'

    # Morphology bevel sides
    MORPHOLOGY_BEVEL_SIDES = '--bevel-sides'

    ################################################################################################
    # Materials and colors arguments
    ################################################################################################
    # Soma color
    SOMA_COLOR = '--soma-color'

    # Axon color
    AXON_COLOR = '--axon-color'

    # Apical dendrites color
    APICAL_DENDRITES_COLOR = '--apical-dendrites-color'

    # Basal dendrites color
    BASAL_DENDRITES_COLOR = '--basal-dendrites-color'

    # Spines colors
    SPINES_COLOR = '--spines-color'

    # Articulations color
    ARTICULATIONS_COLOR = '--articulation-color'

    # Shader
    SHADER = '--shader'

    ################################################################################################
    # Meshing arguments
    ################################################################################################
    # Reconstruct soma mesh
    RECONSTRUCT_SOMA_MESH = '--reconstruct-soma-mesh'

    # Reconstruct neuron mesh
    RECONSTRUCT_NEURON_MESH = '--reconstruct-neuron-mesh'

    # Neuron meshing algorithm
    NEURON_MESHING_ALGORITHM = '--meshing-algorithm'

    # Mesh edges
    MESH_EDGES = '--edges'

    # Mesh surface
    MESH_SURFACE = '--surface'

    # Branching method
    BRANCHING_METHOD = '--branching'

    # Mesh tessellation level
    MESH_TESSELLATION_LEVEL = '--tessellation-level'

    # Export the meshes to the global coordinates
    MESH_GLOBAL_COORDINATES = '--global-coordinates'

    ################################################################################################
    # Geometry export arguments
    ################################################################################################
    # Export morphology .SWC
    EXPORT_SWC_MORPHOLOGY = '--export-morphology-swc'

    # Export .H5 morphology
    EXPORT_H5_MORPHOLOGY = '--export-morphology-h5'

    # Export .BLEND morphology
    EXPORT_BLEND_MORPHOLOGY = '--export-morphology-blend'

    # Export the soma mesh as .PLY
    EXPORT_PLY_SOMA = '--export-soma-mesh-ply'

    # Export the soma mesh as .OBJ
    EXPORT_OBJ_SOMA = '--export-soma-mesh-obj'

    # Export the soma mesh as .STL
    EXPORT_STL_SOMA = '--export-soma-mesh-stl'

    # Export the soma mesh as .BLEND
    EXPORT_BLEND_SOMA = '--export-soma-mesh-blend'

    # Export the neuron mesh as .PLY
    EXPORT_PLY_NEURON = '--export-neuron-mesh-ply'

    # Export the neuron mesh as .OBJ
    EXPORT_OBJ_NEURON = '--export-neuron-mesh-obj'

    # Export the neuron mesh as .STL
    EXPORT_STL_NEURON = '--export-neuron-mesh-stl'

    # Export the neuron mesh as .BLEND
    EXPORT_BLEND_NEURON = '--export-neuron-mesh-blend'

    ################################################################################################
    # Rendering arguments
    ################################################################################################
    # Render the skeleton of the soma (profile points connected together)
    RENDER_SOMA_SKELETON = '--render-soma-skeleton'

    # Render a static image of the soma mesh
    RENDER_SOMA_MESH = '--render-soma-mesh'

    # Render a 360 sequence of the soma mesh
    RENDER_SOMA_MESH_360 = '--render-soma-mesh-360'

    # Render a progressive reconstruction sequence of the soma mesh
    RENDER_SOMA_MESH_PROGRESSIVE = '--render-soma-mesh-progressive'

    # Render a static image of the neuron morphology skeleton
    RENDER_NEURON_MORPHOLOGY = '--render-neuron-morphology'

    # Render a 360 sequence of the neuron morphology skeleton
    RENDER_NEURON_MORPHOLOGY_360 = '--render-neuron-morphology-360'

    # Render a progressive reconstruction sequence of the neuron morphology skeleton
    RENDER_NEURON_MORPHOLOGY_PROGRESSIVE = '--render-neuron-morphology-progressive'

    # Render a static image of the reconstructed neuron mesh
    RENDER_NEURON_MESH = '--render-neuron-mesh'

    # Render a 360 sequence of the reconstructed neuron mesh
    RENDER_NEURON_MESH_360 = '--render-neuron-mesh-360'

    # Rendering an image to scale
    RENDER_TO_SCALE = '--render-to-scale'

    # The part of the skeleton that will be rendered
    RENDERING_VIEW = '--rendering-view'

    # The view or the direction of the camera
    CAMERA_VIEW = '--camera-view'

    # The size of a close up view in microns
    CLOSE_UP_DIMENSIONS = '--close-up-dimensions'

    # The resolution of full-view (mid-shot/wide-shot) images
    FULL_VIEW_RESOLUTION = '--full-view-resolution'

    # The resolution of close-up view images
    CLOSE_UP_RESOLUTION = '--close-up-resolution'

    # Scale factor for increasing the resolution of the to-scale images
    RESOLUTION_SCALE_FACTOR = '--resolution-scale-factor'

    ################################################################################################
    # Execution arguments
    ################################################################################################
    # Execution node
    EXECUTION_NODE = '--execution-node'

    # Number of core to run the frame work
    NUMBER_CORES = '--number-cores'

    # Job granularity
    JOB_GRANULARITY = '--job-granularity'
