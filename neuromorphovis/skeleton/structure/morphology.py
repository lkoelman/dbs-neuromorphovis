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

# System imports
import copy

# Blender imports
from mathutils import Matrix

# Internal imports
import neuromorphovis as nmv
import neuromorphovis.bbox
import neuromorphovis.skeleton


####################################################################################################
# Morphology
####################################################################################################
class Morphology:
    """
    A class to represent the morphological skeleton of a tree structure, for example neuron.
    """

    ################################################################################################
    # @__init__
    ################################################################################################
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
            A given label to the morphology.
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
        self.gid = gid

        # Morphology type
        self.mtype = mtype

        # Morphology label (will be morphology name or gid)
        self.label = label

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

    ################################################################################################
    # @compute_bounding_box
    ################################################################################################
    def compute_bounding_box(self):
        """
        Computes the bounding box of the morphology
        """

        # Compute the bounding box
        axon_bounding_box = None
        if self.has_axon():
            axon_bounding_box = nmv.skeleton.ops.compute_arbor_bounding_box(self.axon)

        # Compute basal dendrites bounding boxes
        basal_dendrites_bounding_boxes = []
        if self.dendrites is not None:
            for dendrite in self.dendrites:
                basal_dendrite_bounding_box = nmv.skeleton.ops.compute_arbor_bounding_box(dendrite)
                basal_dendrites_bounding_boxes.append(basal_dendrite_bounding_box)

        # Compute apical dendrite bounding box
        apical_dendrite_bounding_box = None
        if self.has_apical_dendrite():
            apical_dendrite_bounding_box = nmv.skeleton.ops.compute_arbor_bounding_box(
                self.apical_dendrite)

        # Get the joint bounding box of the entire morphology by collecting the individual ones in a
        # list and then merging the list into a single bounding box
        morphology_bounding_boxes = basal_dendrites_bounding_boxes

        # If the axon is there, add it
        if axon_bounding_box is not None:
            morphology_bounding_boxes.append(axon_bounding_box)

        # If the apical dendrite is there, add it
        if apical_dendrite_bounding_box is not None:
            morphology_bounding_boxes.append(apical_dendrite_bounding_box)

        # Get the joint bounding box from the list
        morphology_bounding_box = nmv.bbox.extend_bounding_boxes(morphology_bounding_boxes)

        # Extend the bounding box a little to verify the results
        morphology_bounding_box.p_min[0] -= 5
        morphology_bounding_box.p_min[1] -= 5
        morphology_bounding_box.p_min[2] -= 5
        morphology_bounding_box.p_max[0] += 5
        morphology_bounding_box.p_max[1] += 5
        morphology_bounding_box.p_max[2] += 5
        morphology_bounding_box.bounds[0] += 10
        morphology_bounding_box.bounds[1] += 10
        morphology_bounding_box.bounds[2] += 10

        # Save the morphology bounding box
        self.bounding_box = morphology_bounding_box

        # Compute the unified bounding box
        self.unified_bounding_box = nmv.bbox.compute_unified_bounding_box(self.bounding_box)

    ################################################################################################
    # @fix_arbor_first_section
    ################################################################################################
    def fix_arbor_first_section(self,
                                arbor):
        """
        Fixes the first section of the given arbor.
        :param arbor: A given arbor.
        """

        # Count the first section samples
        nmv.logger.log('********************************************************************************')
        nmv.logger.log('Section:[%s, %s] '
              '\n\t* Number samples:[%d] '
              '\n\t* Length:[%f um]'
              '\n\t* First sample distance :[%f um]' %
              (str(arbor.id), arbor.get_type_string(), len(arbor.samples),
               nmv.skeleton.ops.compute_section_length(arbor), arbor.samples[0].point.length))

        # If the section has only a single sample, report this issue
        if len(arbor.samples) == 0:
            nmv.logger.log('MORPHOLOGY ERROR: The section [%s: %s] has NO samples at all!' %
                  (arbor.get_type_string(), str(arbor.id)))
        elif len(arbor.samples) == 1:
            nmv.logger.log('MORPHOLOGY ERROR: The section [%s: %s] has only one sample' %
                  (arbor.get_type_string(), str(arbor.id)))
        elif len(arbor.samples) == 2:
            nmv.logger.log('MORPHOLOGY WARNING: The section [%s: %s] has two samples' %
                  (arbor.get_type_string(), str(arbor.id)))

        # Get the distance between the center and the first sample on the arbor
        first_sample_distance = arbor.samples[0].point.length

        # If the first sample is relatively far away, then connect it back to the soma
        if first_sample_distance > 20:
            # Report the issue
            nmv.logger.log('MORPHOLOGY ERROR: The first sample of [%s: %s] is far away [%f] from the soma!' %
                  (arbor.get_type_string(), str(arbor.id), first_sample_distance))

            # Get the direction of the first sample
            first_sample_direction = arbor.samples[0].point.normalized()

            # Set the point of the first sample at a convenient distance
            # TODO: Add the __first_sample_distance__ to the constants
            __first_sample_distance__ = 17.5
            arbor.samples[0].point = __first_sample_distance__ * first_sample_direction

        # Remove the negative samples
        for i, sample in enumerate(arbor.samples):

            # Do not compare the first sample with itself
            if i == 0:
                continue

            # Compare the location of the sample to that of the first sample
            if sample.point.length < first_sample_distance:

                # Report the issue
                nmv.logger.log('MORPHOLOGY ERROR: Negative sample [%d]!' % i)

                # Verify the length of the list
                if len(arbor.samples) > 2:

                    nmv.logger.log('MORPHOLOGY FIX: Removing a negative sample [%s]' % str(sample.id))
                    arbor.samples.remove(sample)

                # If the section has one sample, then the code should not reach this point
                elif len(arbor.samples) == 1:
                    nmv.logger.log(
                    'MORPHOLOGY SEVERE ERROR: Cannot remove a single sampled section, EXITING!')
                    exit(0)

                # If the section has only two samples, and the second one is negative, then we must
                # replace the first sample position to a convenient place
                elif len(arbor.samples) == 2:
                    nmv.logger.log('MORPHOLOGY FIX: Changing the position of the first sample.')

                    # TODO: Add the __sample_shift_value__ to the constants
                    __sample_shift_value__ = 0.5
                    direction = (arbor.samples[0].point - arbor.samples[1].point).normalized()
                    arbor.samples[0].point = arbor.samples[
                                                 1].point - direction * __sample_shift_value__

                else:
                    nmv.logger.log('MORPHOLOGY SEVERE ERROR: Unreported case, EXITING!')
                    exit(0)

    ################################################################################################
    # @fix_arbor
    ################################################################################################
    def fix_arbor(self,
                  arbor):
        """
        Applies the automated fixing algorithm to repair the arbor.
        This function runs a list of fixes that we have integrated in this framework that would
        potentially help during the meshing procedure.

        :param arbor: A given arbor to repair.
        :return:
        """

        # Fix the first sections
        #self.fix_arbor_first_section(arbor)
        pass

    ################################################################################################
    # @fix_artifacts
    ################################################################################################
    def fix_artifacts(self):
        """
        Fixes the artifacts of the morphology, if there are any artifacts.
        """

        # Fix the axon if exists
        if self.has_axon():
            self.fix_arbor(self.axon)

        # Fix the apical dendrite if exists
        if self.has_apical_dendrite():
            self.fix_arbor(self.apical_dendrite)

        # Fix the basal dendrites
        for basal_dendrite in self.dendrites:
            self.fix_arbor(basal_dendrite)

    ################################################################################################
    # @set_section_branching_order
    ################################################################################################
    def set_section_branching_order(self,
                                    section,
                                    order=1):
        """Sets the branching order of the section and its children recursively.

        :param section:
            A given section.
        :param order:
            Section branching order.
        """

        # Set the branching order of the section
        section.branching_order = order

        # Set the branching order of the children
        for child in section.children:
            self.set_section_branching_order(section=child, order=order + 1)

    ################################################################################################
    # @update_branching_order
    ################################################################################################
    def update_branching_order(self):

        # Apical dendrite
        if self.has_apical_dendrite():
            self.set_section_branching_order(self.apical_dendrite)

        # Axon
        if self.has_axon():
            self.set_section_branching_order(self.axon)

        # Basal dendrites
        if self.has_dendrites():
            for dendrite in self.dendrites:
                self.set_section_branching_order(dendrite)


