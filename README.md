# Image2Mono3D - A Fusion360 Add-In
This tool creates a monochrome 3D representation of a provided image, also known as lithophane.
It provides a single command, named 'Image2Mono3D' under the Solid Modify pane.

For multiple reasons, and mainly performance, it is recommended to run this tool in direct modelling environment.
However, for smaller images, the tool runs similarly fast in parametric design.

Install the tool directly from the store [here]() or manually using a copy of this repository - note the missing libraries mentioned in [Dependencies](#Dependencies-not-included-in-this-repo).
More information about the installation can be found [here](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html).

### Dependencies not included in this repo
- [Pillow](https://python-pillow.org/)
- [Fusion360Utils](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-DF32F126-366B-45C0-88B0-CEB46F5A9BE8)

For a local installation, please add the libraries into the `lib` directory in the root directory.

## LICENSE
[LICENSE](LICENSE)
