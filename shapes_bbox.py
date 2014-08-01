#!/usr/bin/python2
import sys
import itertools

from common import read_gtfs_shapes, coord_proj

def get_shapes_bounding_box(shapes, margin=1000.0):
	all_coords = itertools.chain(*(s[1] for s in shapes))
	lonlat = ((lon, lat) for lat, lon in all_coords)
	x, y = coord_proj(*zip(*lonlat))
	xybbox = (min(x)-margin, min(y)-margin), (max(x)+margin, max(y)+margin)

	lonlat_bbox = zip(*coord_proj(*zip(*xybbox), inverse=True))
	bbox = [c for c in lonlat_bbox]
	return bbox
	#for shape in shapes:
	#	print shape

def shapes_bbox(shapesfile, margin=1000.0, mapinput=sys.stdin):
	shapes = read_gtfs_shapes(open(shapesfile))
	bbox = get_shapes_bounding_box(shapes)
	print ",".join(map(str, itertools.chain(*bbox)))

if __name__ == '__main__':
	import argh
	argh.dispatch_command(shapes_bbox)
