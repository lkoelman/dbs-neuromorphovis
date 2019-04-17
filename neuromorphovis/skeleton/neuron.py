"""
Classes that represent neuron cells.

The goal was to have a more flexible class than the Morphology class
provided by NeuroMorphoVis.

@author     Lucas Koelman
"""
import operator

import numpy as np
import mathutils

import neuromorphovis as nmv
from neuromorphovis.interface.ui import ui_data
from neuromorphovis.interface.ui.ui_data import NMV_PROP, SWC_SAMPLE, NMV_OBJ_TYPE
from neuromorphovis.scene.ops import scene_ops

# For assigning new GIDs to morphologies
gid_counter = 0

def make_gid():
    """
    Make global identifier for cell.
    """
    global gid_counter
    gid_count = gid_counter
    gid_counter += 1
    return gid_count


class Neuron(object):
    """
    Keep track of a neuron's Blender geometry and sample points.

    A neuron be either a reconstructed morphology or dummy geometry
    for manipulation in Blender. The class keeps track of its geometrical
    entities in Blender and any transformations applied to it.
    """

    def __init__(self,
                 label=None,
                 swc_samples=None,
                 swc_file=None,
                 parent_geometry=None,
                 draw_geometry=True,
                 draw_options=None):
        """
        Create neuron from SWC file or existing Blender geometry.

        :param swc_samples:
            iterable(indexable) : List of samples, see SWC file specification.
        """
        if swc_file and swc_samples:
            raise ValueError("Provide either SWC file or samples but not both.")

        # Morphology GID
        self.gid = make_gid()

        # Morphology label (will be morphology name or gid)
        if label is None:
            if swc_file:
                label_prefix = nmv.file.ops.get_file_name_from_path(swc_file)
            else:
                label_prefix = 'neuron'
            self.label = label_prefix + '.GID-{}'.format(self.gid)
        else:
            self.label = label

        # Default state
        self.geometry = None
        self.morphology = None

        # Samples are given, so we create the geometry
        if swc_file or swc_samples:
            reader =  nmv.file.readers.SWCReader(swc_file=swc_file)
            if swc_file:
                reader.read_samples()
            elif swc_samples:
                reader.set_samples(swc_samples)

            self.morphology = reader.build_morphology(
                                label=self.label, gid=self.gid)
            self.swc_samples = reader.get_samples()

            if draw_geometry:
                # Draw morphology skeleton and store list of reconstructed objects
                if draw_options is None:
                    draw_options = nmv.options.NeuroMorphoVisOptions()
                    draw_options.morphology.set_default()
                builder = nmv.builders.SkeletonBuilder(
                                    self.morphology, draw_options)
                self.geometry = builder.draw_morphology_skeleton(
                                    parent_to_soma=True, group_geometry=False)

        if parent_geometry is not None:
            # Get SWC samples saved on parent geometry
            samples = parent_geometry.get(NMV_PROP.SWC_SAMPLES, None)
            if samples is not None:
                self.swc_samples = samples

            # Add all child objects to neuron geometry
            self.geometry = []
            children = [parent_geometry]
            while len(children) > 0:
                child = children.pop()
                self.geometry.append(child)
                children.extend(child.children)

        # Save morphology name and gid on each geometry
        if self.geometry:
            for bobj in self.geometry:
                bobj[NMV_PROP.CELL_LABEL] = self.label
                bobj[NMV_PROP.CELL_GID] = self.gid
                bobj[NMV_PROP.OBJECT_TYPE] = NMV_OBJ_TYPE.NEURON_GEOMETRY

            # Save neuron data on Blend geometry
            self.serialize_to_blend()


    def duplicate(self, label):
        # Get soma and neuron geometry
        soma_geometry = self.get_soma_geometry()
        neurite_geometry = [bobj for bobj in self.geometry if 
                            bobj.get(NMV_PROP.SWC_STRUCTURE_ID, None) != SWC_SAMPLE.SOMA]

        # Duplicate the geometry
        soma_copy = scene_ops.duplicate_simple(soma_geometry)
        geometry_copy = [soma_copy]
        
        for bobj in neurite_geometry:
            new_geom = scene_ops.duplicate_simple(bobj)
            new_geom.parent = soma_copy
            geometry_copy.append(new_geom)

        # Uses the copied geometry to query samples, creates new GID
        neuron_copy = Neuron(label, parent_geometry=soma_copy)

        return neuron_copy


    def get_soma_geometry(self):
        geom_objs = self.get_geometry(swc_type=SWC_SAMPLE.SOMA)
        if len(geom_objs) > 1:
            raise Exception("More than one soma geometry.")
        elif len(geom_objs) < 1:
            raise Exception("No soma geometry found.")
        return geom_objs[0]


    def get_geometry(self, swc_type=None, exclude_type=False):
        """
        Get blender geometry representing the neuron's morphology.

        :param exclude_type:
            bool: return all geometry except 'swc_type'
        """
        if swc_type is None:
            return self.geometry
        elif exclude_type:
            compare = operator.ne
        else:
            compare = operator.eq
        return [bobj for bobj in self.geometry if compare(swc_type,
                    bobj.get(NMV_PROP.SWC_STRUCTURE_ID, None))]


    def get_transform(self):
        soma_geom = self.get_soma_geometry()
        return soma_geom.matrix_world


    def serialize_to_blend(self):
        """
        Serialize persistent data to blend file for later restore.
        """
        if self.geometry is not None:
            soma_bobj = self.get_soma_geometry()
            soma_bobj[NMV_PROP.SWC_SAMPLES] = self.swc_samples


    def get_transformed_samples(self):
        """
        Get SWC samples with neuron's transform applied to them.

        :return samples:
            Transformed samples as Nx7 numpy array
        """
        xform = self.get_transform()
        xform_matrix = np.array(xform) # 4x4 array

        sample_matrix = np.array(self.swc_samples)
        coord_matrix = sample_matrix[:, 2:6] # x, y, z, radius
        coord_matrix[:, 3] = 1.0 # for application of 4x4 transform

        coords_transformed = np.dot(coord_matrix, xform_matrix.T)
        sample_matrix[:, 2:5] = coords_transformed[:, 0:3]

        return sample_matrix