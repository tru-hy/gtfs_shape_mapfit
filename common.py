import io
import csv
from collections import namedtuple, defaultdict, OrderedDict
import codecs

import pyproj

# Change this according to your location
coord_proj = pyproj.Proj(init="epsg:3067")

class NamedTupleCsvReader:
	def __init__(self, *args, **kwargs):
		self._reader = iter(csv.reader(*args, **kwargs))
		hdr = self._reader.next()
		self.tupletype = namedtuple('csvtuple', hdr)
	
	def __iter__(self):
		return self
	
	def next(self):
		return self.tupletype(*self._reader.next())

def _peeking_bomstrip(f):
	c = f.peek(3)
	if c == codecs.BOM_UTF8:
		f.read(3)
	return f

def bomstrip(f):
	if hasattr(f, 'peek'):
		return _peeking_bomstrip(f)
	c = f.read(3)
	if c != codecs.BOM_UTF8:
		f.seek(-len(c), 1)
	return f


def read_gtfs_shapes(fileobj):
	fileobj = bomstrip(fileobj)
	shapes = OrderedDict()
	for row in NamedTupleCsvReader(fileobj):
		if row.shape_id not in shapes:
			shapes[row.shape_id] = []
		shapes[row.shape_id].append((
			int(row.shape_pt_sequence),
			float(row.shape_pt_lat),
			float(row.shape_pt_lon)))
	
	for shape_id, coords in shapes.iteritems():
		# Could use a heap if this causes
		# performance problems (probably wont)
		coords.sort()
		lat, lon = zip(*coords)[1:]
		latlon = zip(lat, lon)
		yield (shape_id, latlon)

def read_gtfs_routes(fileobj):
	fileobj = bomstrip(fileobj)
	routes = {}
	for row in NamedTupleCsvReader(fileobj):
		routes[row.route_id] = row
	return routes

def read_gtfs_stops(fileobj):
	fileobj = bomstrip(fileobj)
	return NamedTupleCsvReader(fileobj)

def read_gtfs_shape_trips(fileobj):
	fileobj = bomstrip(fileobj)
	routes = defaultdict(list)
	for row in NamedTupleCsvReader(fileobj):
		routes[row.shape_id].append(row)
	return routes

class GtfsShapeWriter:
	def __init__(self, output):
		self.output = output
		output.write("shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n")
	
	def __call__(self, shape_id, coords):
		for i, c in enumerate(coords, 1):
			self.output.write("%s,%f,%f,%i\n"%(
				shape_id, c[0], c[1], i))

