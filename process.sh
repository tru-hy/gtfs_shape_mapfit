#!/bin/sh
./gtfs_shape_mapfit.py process "$@" |./gtfs_shape_mapfit.py export
