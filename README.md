# GTFS shape mapfit

Fits GTFS shape files and stops to a given OSM map file. Uses
[pymapmatch](https://github.com/tru-hy/pymapmatch) for the matching.
Usually quite accurate.

## License

Copyright 2013 and 2014 Jami Pekkanen (with dots at helsinki.fi), released
under AGPLv3 license.

## Dependencies

* Linux. May work on other unix-like systems. Don't know about Windows.
* Python 2.x (probably 2.7)
* Pyproj
* unzip and zip
* Python library imposm.parser
* Python argh
* Bash
* What [pymapmatch](https://github.com/tru-hy/pymapmatch) needs and
  argh for argument parsing. Pymapmatch is included as a submodule.


## Install

For the lazy, all needed dependencies can be installed in a
Debian-like distribution (tested on ubuntu 14.04) using:
	
	sudo apt-get install make swig g++ python-dev libreadosm-dev \
		libboost-graph-dev libproj-dev libgoogle-perftools-dev \
		osmctools unzip zip python-imposm-parser python-pyproj \
		python-argh

Then fetch the sources:
	
	git clone --recursive https://github.com/tru-hy/gtfs_shape_mapfit
	cd gtfs_shape_mapfit

and build the required binary stuff:

	make -C pymapmatch


## Usage

### Getting the map data
You'll need a OSM export in XML or PBF format for the area covering the
wanted shapes, referred in examples as `map.osm.pbf`. PBF is a lot faster,
so use it if you can. You can download a suitable area extract from
http://download.geofabrik.de/. As an example, for finland this is:

	wget http://download.geofabrik.de/europe/finland-latest.osm.pbf -O /tmp/finland-latest.osm.pbf

To reduce memory and computing time significantly, the map should be cropped
to only the area needed. There's a script `shapes_bbox.py` for getting the suitable
bounding box. This can be used with eg. [osmconvert](http://wiki.openstreetmap.org/wiki/Osmconvert)
to clip the map. Assuming you have osmconvert and a GTFS zip file as `/tmp/google_transit.zip`, run:
	
	osmconvert /tmp/finland-latest.osm.pbf -b=`./shapes_bbox.py /tmp/google_transit.zip` -o=/tmp/map.osm.pbf

### Selecting a map projection

In addition to the map file and GTFS zip file, you'll need to specify the map projection
used during fitting. This is specified as a PROJ.4 string. The default parameters assume
the output is in meters on a 2D plane. Using a projection not suitable for your geographic area
may cause very bad results.

For example in Finland a good choice is the ETRS-TM35FIN projection, which has
the EPSG number 3067. As a PROJ.4 string this is `+init=epsg:3067`.

### Fitting the data

With the map file, GTFS zip and the projection string, the shapes and stop locations
can be fitted on the map data with the `fit_gtfs.bash` script. Using the values
discussed in above sections and resulting to a new GTFS zip file
`/tmp/google_transit.fitted.zip`, this would be:

	./fit_gtfs.bash /tmp/map.osm.pbf +init=epsg:3067 /tmp/google_transit.zip /tmp/google_transit.fitted.zip

This will take some time, depending on your hardware, map size and number of routes.
Helsinki region with about 1800 routes takes about 40 minutes on a Intel(R) Core(TM) i3-2310M CPU @ 2.10GHz.
The performance should scale almost linearly with number of cores.

## Caveats

Currently only buslines, trams, subways and trains are fitted.

If any of the measurements aren't in the search radius (default 100m)
away from the right road, the results can be very bad. Also if roads are marked
wrong in the used map (eg. one-way street where it's actually two way), very weird
errors may occur. The script tries to detect bad errors and uses the original data instead
in such cases. These are also printed as output log of the `fit_gtfs.sh` command.

The performance is reasonable, but could be quite easily made a magnitude or three faster
with a neglible chance of non-optimal fits.

Probably many more.
