# Install development version

Install compatible version of Blender:
- See https://github.com/BlueBrain/NeuroMorphoVis/blob/master/docs/user/installation/install.md

Clone NeuroMorphoVis repository 

```
git clone https://github.com/BlueBrain/NeuroMorphoVis.git
cd NeuroMorphoVis
git checkout -b mybranch
```

Link your repository into Blender addons directory

```
# MacOS
blender_dir=/Applications/Blender/blender.app/Contents/Resources/2.79/scripts/addons
# Linux
blender_dir=/path/to/blender/2.x/scripts/addons
ln -s /path/to/NeuroMorphoVis $blender_dir/NeuroMorphoVis
```


In Blender go to file > user preferences > Add-ons
- type 'neuro' in search box
- check the box for NeuroMorphoVis

# Directory structure

The addon is loaded in the top-level `__init__.py`, in function `register()`.
This provides a good entry point into the module structure.

# Code structure

A lot of variables related to the UI workflow are stored in the `ui_options` variable defined in `neuromorphovis/interface/ui/ui_data.py`