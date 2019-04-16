"""
Classes that represent neuron cells.

The goal was to have a more flexible class than the Morphology class
provided by NeuroMorphoVis.

@author     Lucas Koelman
"""
import neuromorphovis as nmv
from neuromorphovis.interface.ui import ui_data
from neuromorphovis.interface.ui.ui_data import NMV_PROP

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

    def duplicate(self, label):
        pass # TODO: duplicate Neuron


    def __init__(self,
                 swc_samples=None,
                 swc_file=None,
                 parent_geometry=None,
                 draw_geometry=True):
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
        if swc_file:
            self.label = nmv.file.ops.get_file_name_from_path(swc_file)
        else:
            self.label = 'neuron'
        self.label += '.GID-{}'.format(self.gid)
            

        # Samples are given, so we create the geometry
        if swc_file or swc_samples:
            reader =  nmv.file.readers.SWCReader(swc_file=swc_file)
            if swc_file:
                reader.read_samples()
            elif swc_samples:
                reader.set_samples(swc_samples)

            self.morphology = reader.build_morphology(
                                label=self.label, gid=self.gid)
            self.swc_samples = reader.samples_list

            if draw_geometry:
                # Draw morphology skeleton and store list of reconstructed objects
                builder = nmv.builders.SkeletonBuilder(self.morphology, ui_data.ui_options)
                self.geometry = builder.draw_morphology_skeleton(
                                    parent_to_soma=True, group_geometry=False)

                # Save morphology name and gid on each geometry
                for bobj in self.geometry:
                    bobj[NMV_PROP.CELL_LABEL] = self.label
                    bobj[NMV_PROP.CELL_GID] = self.gid

        if parent_geometry is not None:
            # Get SWC samples saved on parent geometry
            samples = parent_geometry.get(ui_data._PROP_SWC_SAMPLES, None)
            if samples is not None:
                self.swc_samples = samples

            # Add all child objects to neuron geometry
            self.geometry = []
            children = [parent_geometry]
            while len(children) > 0:
                child = children.pop()
                self.geometry.append(child)
                children.extend(child.children)
