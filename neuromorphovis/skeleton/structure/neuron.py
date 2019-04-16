"""
Classes that represent neuron cells.

The goal was to have a more flexible class than the Morphology class
provided by NeuroMorphoVis.

@author     Lucas Koelman
"""


class Neuron:
    """
    Class representing a neuron.

    It can be either a reconstructed morphology or dummy geometry
    for manipulation in Blender. The class keeps track of its geometrical
    entities in Blender and the transformations applied to it.
    """

    # For assigning new GIDs to morphologies
    gid_counter = 0

    def __init__(self,
                 soma=None, 
                 axon=None, 
                 dendrites=None, 
                 apical_dendrite=None, 
                 gid=None, 
                 mtype=None,
                 label=None):
        """Constructor

        :param soma:
            Morphology soma.
        :param axon:
            Morphology axon sections, if available.
        :param dendrites:
            Morphology dendrites sections, if available.
        :param apical_dendrite:
            Morphology apical dendrite sections, if available.
        :param gid:
            Morphology GID, if available.
        :param mtype:
            Morphology type, if available.
        :param label:
            A given label to the morphology. If the morphology is loaded from a file, the label
            will be set to the file prefix, however, if it was loaded from a circuit it will be
            set to its gid prepended by a 'neuron_' prefix.
        """

        # Morphology soma
        self.soma = soma

        # Morphology axon
        self.axon = axon

        # Morphology basal dendrites
        self.dendrites = dendrites

        # Morphology apical dendrite
        self.apical_dendrite = apical_dendrite

        # A copy of the original axon, needed for comparison
        self.original_axon = copy.deepcopy(axon)

        # A copy of the original basal dendrites list, needed for comparison
        self.original_dendrites = copy.deepcopy(dendrites)

        # A copy of the original apical dendrite, needed for comparison
        self.origin_apical_dendrite = copy.deepcopy(apical_dendrite)

        # Morphology GID
        if gid is None:
            Morphology.gid_counter += 1
            gid = Morphology.gid_counter
        self.gid = gid

        # Morphology type
        self.mtype = mtype

        # Morphology label (will be morphology name or gid)
        self.label = label
        if gid is not None:
            self.label += '.GID-{}'.format(gid)

        # Morphology full bounding box
        self.bounding_box = None

        # Morphology unified bounding box
        self.unified_bounding_box = None

        # Update the bounding boxes
        self.compute_bounding_box()

        # Update the branching order
        self.update_branching_order()

        # Transformation matrix for sample points
        self.matrix_world = Matrix.Identity(4)


    def duplicate(self, label):
        """
        Create a copy of this morphology with same geometry and new name.

        :param label:
            label for duplicated morphology
        """
        return Morphology(soma=copy.deepcopy(self.soma),
                    axon=copy.deepcopy(self.axon),
                    dendrites=copy.deepcopy(self.dendrites),
                    apical_dendrite=copy.deepcopy(self.apical_dendrite),
                    label=label)


    def transform_sample_points(self, matrix):
        """
        Applies 4x4 transformation matrix to each sample point.

        :param matrix:
            mathutils.Matrix (4x4)
        """
        xform_pt = lambda pt: (matrix * pt.to_4d()).to_3d()

        def transform_subtree(section):
            # transform all sample points in section
            for i in range(0, len(section.samples)):
                new_pt = matrix * section.samples[i].point.to_4d()
                section.samples[i].point = new_pt.to_3d()
            # recursively do the same for children
            for child in section.children:
                transform_subtree(child)

        # Transform soma
        self.soma.centroid = xform_pt(self.soma.centroid)
        self.soma.profile_points = [
            xform_pt(pt) for pt in self.soma.profile_points]
        if self.soma.arbors_profile_points is not None:
            self.soma.arbors_profile_points = [
                xform_pt(pt) for pt in self.soma.arbors_profile_points
            ]

        # Transform axon if exists
        if self.has_axon():
            self.transform_subtree(self.axon)

        # Transform apical dendrite if exists
        if self.has_apical_dendrite():
            self.transform_subtree(self.apical_dendrite)

        # Transform basal dendrites
        for basal_dendrite in self.dendrites:
            transform_subtree(basal_dendrite)

        # Save new transformation matrix
        self.matrix_world = matrix * self.matrix_world


    def has_axon(self):
        """
        Checks if the morphology has axon reported in the data or not.

        :return: True or False.
        """
        return (self.axon is not None)


    def get_axon_terminal_point(self):
        """
        Get axon terminal point.
        """
        if not self.has_axon():
            return None

        terminal_section = self.axon
        while len(terminal_section.children) > 0:
            terminal_section = terminal_section.children[0]

        num_pt = len(terminal_section.samples)
        return terminal_section.samples[num_pt-1]


    def has_dendrites(self):
        """
        Checks if the morphology has basal dendrites reported in the data or not.

        :return: True or False.
        """

        if self.dendrites is None:
            return False

        return True


    def has_apical_dendrite(self):
        """
        Checks if the morphology has an apical dendrites reported in the data or not.

        :return: True or False.
        """

        if self.apical_dendrite is None:
            return False

        return True