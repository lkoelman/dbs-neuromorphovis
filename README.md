# Introduction

_NeuroCircuitVis_ is a modified version of _Neuromorphovis_ for the purpose of defining neuronal circuits in 3D by positioning cells and axons inside anatomical brain structures.

The original _NeuroMorphoVis_ can be found [here](https://github.com/BlueBrain/NeuroMorphoVis):

> _NeuroMorphoVis_ is an interactive, extensible and cross-platform framework for building, visualizing and analyzing digital reconstructions of neuronal morphology skeletons extracted from microscopy stacks. The framework is capable of detecting and repairing several tracing artifacts, allowing the generation of high fidelity surface meshes and high resolution volumetric models for simulation and _in silico_ studies. 




# Installation 

Install compatible version of Blender: see https://github.com/BlueBrain/NeuroMorphoVis/blob/master/docs/user/installation/install.md

## Install the Blender Addon

Clone NeuroMorphoVis repository 

```sh
git clone https://github.com/BlueBrain/NeuroMorphoVis.git
cd NeuroMorphoVis
git checkout -b mybranch
```

Link your repository into Blender addons directory

```sh
# MacOS
blender_dir=/Applications/Blender/blender.app/Contents/Resources/2.79/scripts/addons
# Linux
blender_dir=/path/to/blender/2.x/scripts/addons
ln -s /path/to/NeuroMorphoVis $blender_dir/NeuroMorphoVis
```


In Blender go to file > user preferences > Add-ons
- type 'neuro' in search box
- check the box for NeuroMorphoVis

## Install PIP and python dependencies

Installing PIP lets you install Python packages required by your addon.

```sh
cd /path/to/blender/python/bin
# make sure pip is installed
./python -m ensurepip
# install numpy using --user option: this installs it in 
# ~/.local/lib/python3.X/site-packages/ so it does not conflict with 
# the Blender-packaged numpy located in # blender/2.XX/python/lib/python2.x/site-packages
./python -m pip install numpy --user 
./python -m pip install nibabel # for loading diffusion streamlines
```

# Usage


## Position Neuron Morphologies

TODO

## Connect Axons

- Open _Track Positioning_ panel

- Import Streamlines
  - set import options (_max streamlines_, _min length_, _scale_)
  - press _Import Streamlines_ button



# Acknowledgement

## Neuromorphovis

_NeuroMorphoVis_ is developed by the Visualization team at the [Blue Brain Project](https://bluebrain.epfl.ch/page-52063.html), [Ecole Polytechnique Federale de Lausanne (EPFL)](https://www.epfl.ch/) as part of [Marwan Abdellah's](http://marwan-abdellah.com/) [PhD (In silico Brain Imaging: Physically-plausible Methods for Visualizing Neocortical Microcircuitry)](https://infoscience.epfl.ch/record/232444?ln=en). Financial support was provided by competitive research funding from [King Abdullah University of Science and Technology (KAUST)](https://www.kaust.edu.sa/en).

## NeuroCircuitVis

_NeuroMorphoVis_ is developed by Lucas Koelman at the [Neuromuscular Systems Lab](https://www.neuromuscularsystemsucd.info/), University College Dublin as part of Lucas Koelman's PhD in modeling the effects of Deep Brain Stimulation for the treatment of Parkinson's Disease on basal ganglia circuitry. Financial support was provided by research funding from the European Research Council.

# License 

_NeuroCircuitVis_ is available to download and use under the GNU General Public License ([GPL](https://www.gnu.org/licenses/gpl.html), or “free software”).
