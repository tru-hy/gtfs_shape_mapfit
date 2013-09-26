# GTFS shape mapfit

Fits GTFS shape files to a given OSM map file. Uses
[pymapmatch](https://github.com/tru-hy/pymapmatch) for the matching.
Quite accurate, but very slow.

## License

Copyright 2013 Jami Pekkanen (with dots at helsinki.fi), released
under AGPLv3 license.

## Dependencies

What [pymapmatch](https://github.com/tru-hy/pymapmatch) needs and
argh for argument parsing. Matplotlib for visualization of the results.
Pymapmatch is included as a submodule.

Linux. May work on other unix-like systems. Does not work on Windows
due to some library dependencies not supporting the platform.

## Install
	
	git pull --recursive https://github.com/tru-hy/pymapmatch

## Usage

*NOTE*: The current implementation is mostly done with a specific fit
to city of Tampere's data in mind. In practice if you want to use this
program, it's best to contact the author.

You'll need a OSM export in XML or PBF format for the area covering the
wanted shapes, referred in examples as `map.osm`.
Due to some naive choices in current implementation, the map
size affects fitting times very strongly. Expect many minutes per one
shape. The initial loading also takes quite a while as it generates
a graph from the map and R-tree from the edges.

At the moment the map projection used is also hardcoded in `gtfs_shape_mapfit.py`,
so you'll need to change it if you are doing the matching anywhere but in Finland.

The fitting is usually done in two stages, first the fits are made
with some included statistics and stored in a pickle.
	
	./gtfs_shape_mapfit.py process map.osm < shapes_orig.txt > fits.pickle

The results can be visualized with some statistics:
	
	./gtfs_shape_mapfit.py view map.osm < fits.pickle

And exported to a new shapes.txt:
	
	./gtfs_shape_mapfit.py export < fits.pickle > shapes_fitted.txt

## Caveats

Many. If any of the measurements aren't in the search radius (default 50m)
away from the right road, the results can be very bad. The radius can be
increased with the `-s` parameter, but note that this dramatically increases
the runtime. You can select only a subset of shapes to fit with the `-w`
parameter, which is especially useful if only some shapes need a larger search
radius.

