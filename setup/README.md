This directory is used for assets that require pre-processing before
they can be consumed in your project.

You should place your assets into a subdirectory that contains a
Makefile to run your pre-processing steps.

When you build your project with `make`, it automatically makes every
subdirectory undep ./setup to run the pre-processing steps for all
assets. You can also re-run those steps manually at any time by
running `make generate`.

By default, this template project provides default ngdevkit assets to
print characters on the fixed tilemap, as well as a the ngdevkit logo
in sprite tiles, that is prepared for being displayed in the attract
mode animation.
