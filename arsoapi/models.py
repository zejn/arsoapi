
import datetime
import Image
import os
import pytz
import subprocess
import tempfile
from cStringIO import StringIO
from itertools import chain

from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile

from arsoapi.util import Counter, fetch
from arsoapi.laplacian import laplacian

from osgeo import gdal
import osgeo.gdalconst as gdalc

URL_VREME_RADAR = 'http://www.arso.gov.si/vreme/napovedi%20in%20podatki/radar.gif'
URL_VREME_ALADIN = 'http://www.arso.gov.si/vreme/napovedi%%20in%%20podatki/aladin/AW00_oblpad_%.3d.png'
URL_VREME_ALADIN = 'http://meteo.arso.gov.si/uploads/probase/www/model/aladin/field/as_%s-%s_tcc-rr_si-neighbours_%.3d.png'

GDAL_TRANSLATE = '/usr/bin/gdal_translate'
GDAL_WARP = '/usr/bin/gdalwarp'
IMAGEMAGICK_CONVERT = '/usr/bin/convert'

MASK_FILE = os.path.join(os.path.dirname(__file__), 'mask.png')
MEJE_FILE = os.path.join(os.path.dirname(__file__), 'meje.png')

# init
gdal.AllRegister()

class GeoDatasourceError(Exception): pass

##############################
## Models
##############################


class RadarPadavin(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
	last_modified = models.DateTimeField(db_index=True)
	picdata = models.TextField()
	processed = models.FileField(upload_to='processed', null=True, blank=True)
	
	class Meta:
		ordering = ('-timestamp',)
	
	def pic():
		def fget(self):
			if self.picdata:
				return Image.open(StringIO(self.picdata.decode('base64')))
		def fset(self, value):
			s = StringIO()
			value.save(s)
			self.picdata = s.getvalue().encode('base64')
		return fget, fset
	pic = property(*pic())
	
	def image_name(self):
		return 'radar_%s.tif' % (self.last_modified.strftime('%Y%m%d-%H%M%S'),)
	
	def process(self):
		filtered = filter_radar(self.pic)
		geotiff = annotate_geo_radar(filtered)
		self.processed.save(name=self.image_name(), content=ContentFile(geotiff))
		self.save()

class Aladin(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
	forecast_time = models.DateTimeField(db_index=True)
	timedelta = models.IntegerField()
	picdata = models.TextField()
	processed = models.FileField(upload_to='processed', null=True, blank=True)
	
	class Meta:
		ordering = ('-forecast_time', '-timedelta')
	
	def pic():
		def fget(self):
			if self.picdata:
				return Image.open(StringIO(self.picdata.decode('base64')))
		def fset(self, value):
			s = StringIO()
			value.save(s)
			self.picdata = s.getvalue().encode('base64')
		return fget, fset
	pic = property(*pic())
	
	def image_name(self):
		return 'aladin_%s_%s.tif' % (self.forecast_time.strftime('%Y%m%d-%H%M'), self.timedelta)
	
	def process(self):
		filtered = filter_aladin(self.pic)
		geotiff = annotate_geo_aladin(filtered)
		self.processed.save(name=self.image_name(), content=ContentFile(geotiff))
		self.save()



###############################
## Functions
###############################

def fetch_radar():
	return fetch(URL_VREME_RADAR)

def fetch_aladin(ft, n):

	assert n % 3 == 0
	return fetch(URL_VREME_ALADIN % (now.strftime('%Y%m%d'), hrs, n))

RADAR_CRTE = (96,96,96)
WHITE = (255,255,255)
BLACK = (0, 0, 0)
RADAR_DEZ = {
	WHITE:			0,
	(25, 185, 0):	25,
	(250, 225, 0):	50,
	(250, 125, 0):	75,
	(250, 0, 0):	100,
}

def filter_radar(src_img):
	im = src_img.convert('RGB')
	pixels = im.load()
	
	cc = Counter()
	
	for i in range(im.size[0]):
		for j in range(im.size[1]):
			cc[pixels[i,j]] += 1
			if pixels[i,j] == RADAR_CRTE:
				c = Counter()
				for p in (pixels[i-1,j], pixels[i,j-1], pixels[i+1,j], pixels[i,j+1]):
					if p in RADAR_DEZ.keys():
						c[p] += 1
				if c.most_common():
					pixels[i,j] = c.most_common(1)[0][0]
				else:
					pixels[i,j] = WHITE
	
	return im

ALADIN_CRTE = (123,123,123)
ALADIN_BACKGROUND = (241, 241, 241)
ALADIN_MORJE = (252, 252, 252)
ALADIN_OBLACNOST = {
	(228, 228, 254): 40,
	(206, 206, 246): 60,
	(189, 189, 227): 80,
	}

ALADIN_ZELENA = (51, 153, 76)
ALADIN_MARKER_OZADJE = (230, 255, 127)

ALADIN_PADAVINE = {
	(255, 255, 189): 1,
	(246, 255, 170): 2,
	(228, 255, 151): 5,
	(189, 245, 149): 10,
	(171, 228, 150): 20,
	(134, 207, 131):  30,
	(114, 189, 126):   40,
	# unverified colors below
	(18, 115, 55):   50,
	(18, 158, 104):  60,
	(15, 183, 134):  70,
	(15, 207, 157):  80,
	(9, 227, 174):   90,
}

ALADIN_VOTABLE = tuple([WHITE] + ALADIN_OBLACNOST.keys() + ALADIN_PADAVINE.keys())
ALADIN_DISTANCE = ALADIN_VOTABLE + (ALADIN_BACKGROUND, ALADIN_MORJE)

def filter_aladin(src_img):
	im = src_img.convert('RGB')
	pixels = im.load()
	cc = Counter()
	
	mask = Image.open(MASK_FILE).convert('RGB')
	mask_pix = mask.load()
	
	# step 1: remove terrain
	for i in range(im.size[0]):
		for j in range(im.size[1]):
			p = pixels[i,j]
			m = mask_pix[i,j]
			pixels[i,j] = (
				256*p[0] / (m[0]+1),
				256*p[1] / (m[1]+1),
				256*p[2] / (m[2]+1),
				)
	
	def _surroundings(i, j):
		for a in xrange(i-2, i+3):
			for b in xrange(j-2, j+3):
				yield a, b
		
	
	# step 2: fix artefacts from previous step
	meje = Image.open(MEJE_FILE)
	meje_pix = meje.load()
	
	for i in range(2, im.size[0]-2):
		for j in range(2, im.size[1]-2):
			if meje_pix[i,j] == 0: # pixel needs repairing
				c = Counter()
				for coord in (pt for pt in _surroundings(i, j) if meje_pix[pt] != 0):
					c[pixels[coord]] += 1
				elected = c.most_common()[0][0]
				pixels[i,j] = elected
	
	edges_mask = laplacian(im.copy())
	edges_mask = edges_mask.convert('1')
	edges_pix = edges_mask.load()
	
	for i in range(2, im.size[0]-2):
		for j in range(2, im.size[1]-2):
			if edges_pix[i,j] == 0: # pixel needs repairing
				c = Counter()
				for coord in (pt for pt in _surroundings(i, j) if edges_pix[pt] != 0):
					c[pixels[coord]] += 1
				res = c.most_common()
				if res:
					elected = c.most_common()[0][0]
					pixels[i,j] = elected
	
	return im

def filter_aladin_old(src_img):
	im = src_img.convert('RGB')
	pixels = im.load()
	cc = Counter()
	
	# remove country background
	for i in range(im.size[0]):
		for j in range(im.size[1]):
			cc[pixels[i,j]] += 1
			if pixels[i,j] == ALADIN_BACKGROUND:
				c = Counter()
				try:
					neighbors = (pixels[i-1,j], pixels[i,j-1], pixels[i+1,j], pixels[i,j+1])
				except IndexError:
					continue
				pixels[i,j] = WHITE
	
	# fix crosshair in LJ
	for i,j in chain(((230, i) for i in xrange(279, 291)), ((i, 284) for i in xrange(225, 236))):
		c = Counter()
		neighbors = (
			pixels[i-1,j-1],
			pixels[i-1,j],
			pixels[i-1,j+1],
			pixels[i,j-1],
			#pixels[i-1,j], # self
			pixels[i,j+1],
			pixels[i+1,j-1],
			pixels[i+1,j],
			pixels[i+1,j+1],
		)
		for p in neighbors:
			if p in ALADIN_VOTABLE:
				c[p] += 1
		if c.most_common():
			pixels[i,j] = c.most_common(1)[0][0]
		else:
			pixels[i,j] = WHITE
	
	# remove borders and coastlines
	for i in range(im.size[0]):
		for j in range(im.size[1]):
			if pixels[i,j] == ALADIN_CRTE:
				c = Counter()
				try:
					neighbors = (pixels[i-1,j], pixels[i,j-1], pixels[i+1,j], pixels[i,j+1])
				except IndexError:
					continue
				for p in neighbors:
					if p in ALADIN_VOTABLE:
						c[p] += 1
				if c.most_common():
					pixels[i,j] = c.most_common(1)[0][0]
				else:
					pixels[i,j] = WHITE
	
	# remove green edges
	for i in range(im.size[0]):
		for j in range(im.size[1]):
			if pixels[i,j] == ALADIN_ZELENA:
				c = Counter()
				try:
					neighbors = (
						pixels[i-1,j-1],
						pixels[i-1,j],
						pixels[i-1,j+1],
						pixels[i,j-1],
						#pixels[i-1,j], # self
						pixels[i,j+1],
						pixels[i+1,j-1],
						pixels[i+1,j],
						pixels[i+1,j+1],
						)
				except IndexError:
					continue
				for p in neighbors:
					if p in ALADIN_VOTABLE:
						c[p] += 1
				if c.most_common():
					# ce ni na meji s 30mm ali 50mm potem ne more bit zelena veljavna izbira
					if not (76, 179, 76) in c and \
							not (0, 127, 51) in c and \
							ALADIN_ZELENA in c and \
							len(c.most_common()) > 1:
						del c[ALADIN_ZELENA]
					pixels[i,j] = c.most_common()[0][0]
				else:
					pixels[i,j] = WHITE
	
	# remove number boxes
	print 'removing'
	# step 1: detect
	pending_removal = {}
	for i in range(1, im.size[0]):
		for j in range(1, im.size[1]-1):
			if pixels[i,j] == ALADIN_MARKER_OZADJE and \
				pixels[i-1,j-1] == BLACK and \
				pixels[i-1,j] == BLACK and \
				pixels[i-1, j+1] == BLACK and\
				pixels[i, j-1] == BLACK and \
				pixels[i+1, j-1] == BLACK:
				pending_removal[(i,j)] = 1
	
	# step 2: find bounds
	def _getneighbors(i, j):
		yield i-1, j-1
		yield i,   j-1
		yield i+1, j-1
		yield i-1, j
		#yield i,   j # NO
		yield i+1, j
		yield i-1, j+1
		yield i,   j+1
		yield i+1, j+1
	
	markers = []
	all_checked = {}
	for pix in pending_removal.keys():
		if pix in all_checked:
			continue
		marker = {}
		checked = {}
		this_pending = {}
		this_pending[pix] = 1
		
		while this_pending:
			p = this_pending.keys()[0]
			checked[p] = 1
			all_checked[p] = 1
			
			if pixels[p] in (BLACK, ALADIN_MARKER_OZADJE):
				marker[p] = 1
				for nxt in _getneighbors(*p):
					if nxt not in checked:
						this_pending[nxt] = 1
			del this_pending[p]
		
		markers.append(marker)
	print 'n markers', len(markers)
	# step 3: find marker bounding box
	bboxes = []
	for m in markers:
		min_x = min_y = 200000
		max_x = max_y = 0
		for p in m:
			min_x = min(min_x, p[0])
			max_x = max(max_x, p[0])
			min_y = min(min_y, p[1])
			max_y = max(max_y, p[1])
		bboxes.append((min_x, max_x, min_y, max_y))
	
	# step 4: try to fill the boxes
	pending_bboxes = []
	for min_x, max_x, min_y, max_y in bboxes:
		c = Counter()
		p_top = ((i, max_y+1) for i in xrange(min_x, max_x+1))
		p_bottom = ((i, min_y-1) for i in xrange(min_x, max_x+1))
		p_left = ((min_x-1, i) for i in xrange(min_y, max_y+1))
		p_right = ((max_x+1, i) for i in xrange(min_y, max_y+1))
		for x in chain(p_top, p_bottom, p_left, p_right):
			c[pixels[x]] += 1
		if len(c.most_common()) == 1:
			the_color = c.most_common()[0][0]
			for i in xrange(min_x, max_x+1):
				for j in xrange(min_y, max_y+1):
					pixels[i,j] = the_color
		else:
			print 'simple fail'
			pending_bboxes.append((min_x, max_x, min_y, max_y))
	
	return im

def annotate_geo_radar(img):
	print 'ANN radar: Annotating'
	src = tempfile.NamedTemporaryFile(mode='w+b', dir=settings.TEMPORARY_DIR, prefix='radar1_', suffix='.tif')
	tmp = tempfile.NamedTemporaryFile(mode='w+b', dir=settings.TEMPORARY_DIR, prefix='radar2_', suffix='.tif')
	dst = tempfile.NamedTemporaryFile(mode='w+b', dir=settings.TEMPORARY_DIR, prefix='radar3_', suffix='.tif')
	img.save(src.name, 'tiff')
	src.flush()
	
	print 'ANN radar: gdal translate'
	# magic numbers, geocoded pixels
	cmd = '-gcp 251 246 401712 154018 -gcp 625 215 589532 169167 -gcp 507 479 530526 38229 -a_srs EPSG:3787'.split(' ')
	p = subprocess.Popen([GDAL_TRANSLATE] + cmd + [src.name, tmp.name])
	p.wait()
	
	print 'ANN radar: gdal warp'
	p = subprocess.Popen([GDAL_WARP] + '-s_srs EPSG:3787 -t_srs EPSG:4326'.split(' ') + [tmp.name, dst.name])
	p.wait()
	
	print 'ANN radar: done'
	dst.seek(0)
	processed = dst.read()
	return processed

def annotate_geo_aladin(img):
	print 'ANN aladin: Annotating'
	src = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='aladin1_', suffix='.tif')
	tmp = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='aladin2_', suffix='.tif')
	dst = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='aladin3_', suffix='.tif')
	img.save(src.name, 'tiff')
	src.flush()
	
	print 'ANN aladin: gdal translate'
	# old aladin
	#cmd = '-gcp 530 194 622883 149136 -gcp 360 408 530526 38229 -gcp 116 187 401712 154018 -a_srs EPSG:3787'.split(' ')
	# magic numbers - geocoded pixels
	cmd = '-gcp 573 144 622883 149136 -gcp 424 323 530526 38229 -gcp 218 136 401712 154018 -a_srs EPSG:3787'.split(' ')
	
	p = subprocess.Popen([GDAL_TRANSLATE] + cmd + [src.name, tmp.name])
	p.wait()
	
	print 'ANN aladin: gdal warp'
	p = subprocess.Popen([GDAL_WARP] + '-s_srs EPSG:3787 -t_srs EPSG:4326'.split(' ') + [tmp.name, dst.name])
	p.wait()
	
	print 'ANN aladin: done'
	dst.seek(0)
	processed = dst.read()
	return processed

def convert_geotiff_to_png(tiffdata):
	"PIL does not support GeoTIFF, therefore imagemagick convert is needed"
	src = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='convert_src_', suffix='.tif')
	dst = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='convert_dst_', suffix='.png')
	
	src.write(tiffdata)
	src.flush()
	
	p = subprocess.Popen([IMAGEMAGICK_CONVERT, src.name, dst.name])
	p.wait()
	
	dst.seek(0)
	return dst.read()

class GeocodedRadar:
	RAIN_LEVEL = RADAR_DEZ
	
	def __init__(self):
		self.bands = {}
		self.last_modified = None
	
	def refresh(self):
		r = RadarPadavin.objects.all()[0]
		if self.last_modified != r.last_modified:
			self.load_from_model(r)
	
	def load_from_model(self, instance):
		self.load_from_string(instance.processed.read())
		self.last_modified = instance.last_modified
	
	def load_from_string(self, data):
		self.tmpfile = None # clear reference
		self.tmpfile = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='radar_served_', suffix='.tif')
		self.tmpfile.write(data)
		self.tmpfile.flush()
		self.load(self.tmpfile.name)
	
	def __del__(self):
		self.clean()
	
	def clean(self):
		for b in self.bands.keys():
			del self.bands[b]
		self.transform = None
		self.rows = self.cols = None
		self.ds = None
	
	def load(self, filename):
		self.clean()
		
		self.ds = gdal.Open(filename, gdalc.GA_ReadOnly)
		if self.ds is None:
			raise GeoDatasourceError('No datasource file found')
		
		self.rows = self.ds.RasterYSize
		self.cols = self.ds.RasterXSize
		self.transform = self.ds.GetGeoTransform()
		
		for i in range(self.ds.RasterCount):
			band = self.ds.GetRasterBand(i+1)
			self.bands[i+1] = band.ReadAsArray(0, 0, self.cols, self.rows)
	
	def get_pixel_at_coords(self, lat, lng):
		yOrigin = self.transform[0]
		xOrigin = self.transform[3]
		pixelWidth = self.transform[1]
		pixelHeight = self.transform[5]
		
		xOffset = abs(int((lat-xOrigin) / pixelWidth)) # XXX remove abs
		yOffset = abs(int((lng-yOrigin) / pixelHeight))
		
		return (xOffset, yOffset), tuple((int(b[xOffset,yOffset]) for b in self.bands.itervalues()))
	
	def get_rain_at_coords(self, lat, lng):
		position, pixel = self.get_pixel_at_coords(lat, lng)
		return position, self.RAIN_LEVEL[pixel]
	

class GeocodedAladin:
	CLOUDS = ALADIN_OBLACNOST
	RAIN = ALADIN_PADAVINE
	
	def __init__(self):
		self.images = {}
		self.bands = {}
		self.tmpfiles = {}
		self.forecast_time = {}
	
	def refresh(self):
		a = Aladin.objects.all()[0]
		ft = self.forecast_time.get(6, datetime.datetime.now() - datetime.timedelta(1))
		timediff = datetime.datetime.now() - ft
		if timediff > datetime.timedelta(hours=12):
			self.load_from_models(Aladin.objects.filter(forecast_time=a.forecast_time))
	
	def load_from_models(self, instances):
		self.tmpfiles = {}
		self.clean()
		for i in instances:
			print 'ALADIN Loading :', i.timedelta
			self.load_from_string(i.processed.read(), i.timedelta, i.forecast_time)
			self.forecast_time[i.timedelta] = i.forecast_time
	
	def load_from_string(self, data, n, ft):
		self.tmpfiles[n] = None # clear reference
		self.tmpfiles[n] = tempfile.NamedTemporaryFile(dir=settings.TEMPORARY_DIR, prefix='aladin_served%s_' % n, suffix='.tif')
		self.tmpfiles[n].write(data)
		self.tmpfiles[n].flush()
		self.load(self.tmpfiles[n].name, n, ft)
	
	def __del__(self):
		self.clean()
	
	def clean(self):
		for n in self.bands.keys():
			for b in self.bands[n].keys():
				del self.bands[n][b]
			del self.bands[n]
		self.bands = {}
		self.transform = None
		self.rows = self.cols = None
		self.forecast_time = {}
		self.images = {}
	
	def load(self, filename, n, ft):
		self.images[n] = gdal.Open(filename, gdalc.GA_ReadOnly)
		if self.images[n] is None:
			raise GeoDatasourceError('No datasource file found')
		
		self.rows = self.images[n].RasterYSize
		self.cols = self.images[n].RasterXSize
		self.transform = self.images[n].GetGeoTransform()
		
		self.bands[n] = {}
		for i in range(self.images[n].RasterCount):
			band = self.images[n].GetRasterBand(i+1)
			self.bands[n][i+1] = band.ReadAsArray(0, 0, self.cols, self.rows)
			self.forecast_time[n] = ft
	
	def _get_candidates(self, i, j):
		for a in xrange(i-1, i+2):
			for b in xrange(j-1, j+2):
				yield a,b
	
	def get_pixel_at_coords(self, lat, lng):
		yOrigin = self.transform[0]
		xOrigin = self.transform[3]
		pixelWidth = self.transform[1]
		pixelHeight = self.transform[5]
		
		xOffset = abs(int((lat-xOrigin) / pixelWidth)) # XXX remove abs
		yOffset = abs(int((lng-yOrigin) / pixelHeight))
		
		resp = []
		for n in self.bands:
			candidates = self._get_candidates(xOffset, yOffset)
			c = Counter()
			for p in candidates:
				k = tuple((int(b[p]) for b in self.bands[n].itervalues()))
				c[k] += 1
				if p == (xOffset, yOffset):
					c[k] += 5
			resp.append((n, c.most_common()[0][0]))
			#resp.append((n, tuple((int(b[xOffset,yOffset]) for b in self.bands[n].itervalues()))))
		
		return (xOffset, yOffset), list(sorted(resp))
	
	def _nearest_color(self, p, palette):
		dists = []
		for c in palette:
			d = sum([abs(a - b) for a, b in zip(p, c)])
			dists.append((d, c))
		mindist = sorted(dists)[0][0]
		all_mindist = [i for i in dists if i[0] == mindist]
		if len(all_mindist) == 1 and all_mindist[0][0] < 20:
			return all_mindist[0][1]
		else:
			return p
	
	def _get_value(self, pixel):
		clouds = self.CLOUDS.get(self._nearest_color(pixel, self.CLOUDS), 0)
		rain = self.RAIN.get(self._nearest_color(pixel, self.RAIN), 0)
		return {
			'clouds': clouds,
			'rain': rain,
			}
	
	def get_forecast_at_coords(self, lat, lng):
		position, pixel = self.get_pixel_at_coords(lat, lng)
		
		forecast = []
		for n, p in pixel:
			print self.forecast_time[n]
			ft = self.forecast_time[n] + datetime.timedelta(hours=n)
			ft = ft.replace(tzinfo=pytz.UTC)
			ft = ft.astimezone(pytz.timezone('Europe/Ljubljana'))
			d = {'offset': n, 'forecast_time': ft.strftime('%Y-%m-%d %H:%M') }
			d.update(self._get_value(p))
			forecast.append(d)
		
		return position, tuple(forecast)

