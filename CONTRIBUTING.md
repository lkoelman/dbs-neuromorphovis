# Install development version

Install compatible version of Blender:
- See https://github.com/BlueBrain/NeuroMorphoVis/blob/master/docs/user/installation/install.md

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

# Install PIP for Blender Python

This lets you install any additional Python packages required by your addon.
It uses the 'ensurepip' module packaged with Blender to install pip.

```sh
cd /path/to/blender/python/bin
./python -m ensurepip
./python -m pip install ipython
./python -m pip install numpy --user # installs in ~/.local/lib/python3.X/site-packages/ so it doesn't conflict with packaged numpy in blender/2.XX/python/lib/python2.x/site-packages which cannot be imported
./python -m pip install nibabel
```

# Debugging

Start blender from terminal to see stdout and stderr (all output from print
statements).

The following line simulate a breakpoint:

```python
import IPython; IPython.embed()
```

# Code structure

## Initialization

The addon is loaded in the top-level `__init__.py`, in function `register()`.
This provides a good entry point into the module structure.

## State variables

A lot of variables related to the UI workflow are stored in the `ui_options` variable defined in `neuromorphovis/interface/ui/ui_data.py`.

Interesting classes:

```python
nmv.file.readers.morphology.SWCReader # creates Morphology object from file
nmv.builders.SkeletonBuilder # builds skeleton geometry for loaded morphology
```

Interesting variables:

```python
neuromorphovis.interface.ui_options # nmv.options.NeuroMorphoVisOptions
# `-> stores options related to UI interaction
neuromorphovis.interface.ui_morphologies # list(nmv.skeleton.structure.Morphology)
# `-> stores the loaded morphologies
neuromorphovis.interface.ui_reconstructed_skeletons # dict[str, list()]
# `-> stores Blender geometry corresponding to each morphology (by label)
```

# Useful Blender commands

Useful commands, search using spacebar menu.

- `View Selected` : does what it says

- Don't clip far-away objects:
    - `View > Properties > View > Clip: End` > set to higher value

- Enable faster selection:
    - Preferences > System > Selection > tick 'OpenGL Occlusion Queries'

- Snap to objects during selection/move:
    - `SHIFT+TAB` or Magnet icon + set snap to Vertex