# Image2Mono3D - A Fusion360 Add-In
This tool creates a monochrome 3D representation of a provided image, also known as lithophane.
It provides a single command, named 'Image2Mono3D' under the Solid Modify pane.

For multiple reasons, and mainly performance, it is recommended to run this tool in direct modelling environment.
However, for smaller images, the tool runs similarly fast in parametric design.

## Install/Uninstall

Install the tool directly from the store [here](https://apps.autodesk.com/Detail/Index?id=3176639410093050089) or manually using a copy of this repository - note the missing libraries mentioned in [Dependencies](#Dependencies-not-included-in-this-repo).
More information about the installation can be found [here](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html).\
Uninstalling the add-in manually only works by deleting the source folder, like so:
- Within Fusion, head to Toolbar > Utilities > Add-ins > Scripts and Add-ins
- Right-click the Add-in and select Open File Location.
- Delete the folder named 'Image2Mono3D' 

Uninstall with Autodesk Installer:\
You can unload the add-in without uninstalling it by clicking the "Stop" button when the add-in is selected in the list box on the "Add-Ins" tab of the "Scripts and Add-Ins" dialog.
Unchecking "Run on Startup" causes the add-in not to be loaded in future sessions of Autodesk® Fusion 360®.
To uninstall this plug-in, simply rerun the installer, and select the "Uninstall" button.
Or, you can uninstall it from 'Control Panel/Programs and Features' (Windows 8.1/10/11), just as you would uninstall any other application from your system.


### Dependencies not included in this repo
- [Pillow](https://python-pillow.org/)
- [Fusion360Utils](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-DF32F126-366B-45C0-88B0-CEB46F5A9BE8)

For a local installation, please add the libraries into the `lib` directory in the root directory.

## LICENSE
[LICENSE](LICENSE)
