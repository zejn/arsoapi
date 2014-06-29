from cStringIO import StringIO
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.utils._os import safe_join
from django.conf import settings
from django.db import models

import datetime
import os
import time
from PIL import Image
import simplejson
from arsoapi.models import (
	GeocodedRadar, GeocodedToca, GeocodedAladin,
	RadarPadavin, Toca, Aladin,
	mmph_to_level,
	WHITE, RADAR_CRTE,
	annotate_geo_radar,
	)

from osgeo import gdal
import osgeo.gdalconst as gdalc
import numpy

geocoded_radar = GeocodedRadar()
geocoded_toca = GeocodedToca()
geocoded_aladin = GeocodedAladin()

def _dumps(s):
	return simplejson.dumps(s, use_decimal=True, ensure_ascii=True)

def _datetime2timestamp(dt):
	return int(time.mktime(dt.timetuple()))

def datetime_encoder(obj):
	if isinstance(obj, datetime.datetime):
		return obj.isoformat()
	elif isinstance(obj, models.fields.files.FieldFile):
		return None
	else:
		raise TypeError, 'Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj))

def dump_data(model, day):
	from django.db import connection
	prevday = day
	yday = prevday + datetime.timedelta(1)
	the_day = datetime.datetime(prevday.year, prevday.month, prevday.day, 0, 0, 0)
	
	qs = model.objects.filter(timestamp__gte=the_day, timestamp__lt=the_day + datetime.timedelta(1))
	
	if qs.count() == 0:
		return
	
	sql, params = qs.query.get_compiler('default').as_sql()
	
	class Dumper(list):
		def __init__(self, sql, params):
			self.cur = connection.cursor()
			self.cur.execute(sql, params)
			self.labels = [i[0] for i in self.cur.cursor.description]
		
		def __nonzero__(self):
			return True
		
		def __iter__(self):
			return self
		
		def next(self):
			rec = self.cur.fetchone()
			if rec is not None:
				obj_data = dict(zip(self.labels, rec))
				return obj_data
			else:
				raise StopIteration
			
	
	dumper = Dumper(sql, params)
	
	dump_dir = safe_join(settings.DUMP_DIR, the_day.strftime('%Y-%m'))
	dump_file = safe_join(dump_dir, the_day.strftime(model.__name__.lower() + '_%Y-%m-%d.json'))
	
	if not os.path.isdir(dump_dir):
		os.makedirs(dump_dir)
	
	f = open(dump_file, 'w')
	for frag in simplejson.JSONEncoder(default=datetime_encoder).iterencode(dumper):
		f.write(frag)
	f.close()
	
	os.system('/bin/gzip -9 %s' % dump_file)
	
	qs.delete()

def jsonresponse(func):
	def _inner(*args, **kwargs):
		jsondata = func(*args, **kwargs)
		return HttpResponse(_dumps(jsondata), mimetype='application/json')
	return _inner

def image_radar(request):
	r = RadarPadavin.objects.all()[0]
	return _png_image(r)

def align_radar(request):
	r = RadarPadavin.objects.all()[0]

	geotiff = annotate_geo_radar(r.pic, scale=4)

	img = Image.open(StringIO(geotiff)).convert('RGBA')

	a = numpy.array(numpy.asarray(img))

	d = (a[:,:,0] == RADAR_CRTE[0]) & (a[:,:,1] == RADAR_CRTE[1]) & (a[:,:,2] == RADAR_CRTE[2])
	a[d,3] = 200
	a[~d,3] = 0

	return _png_image_fromarray(a)

def image_aladin(request, offset):
	a = Aladin.objects.all()[0]
	real = Aladin.objects.filter(forecast_time=a.forecast_time, timedelta=offset)[0]
	return _png_image(real)

def image_toca(request):
	t = Toca.objects.all()[0]
	return _png_image(t)

def _kml_file(model):
	left, lon_pixelsize, a, top, b, lat_pixelsize = model.transform
	north = top
	south = top + model.rows*lat_pixelsize
	east = left + model.cols*lon_pixelsize
	west = left
	values = [str(i) for i in (north, south, east, west)]
	return dict(zip(('north', 'south', 'east', 'west'), values))

def kml_radar(request):
	if request.GET.get('align'):
		image_view = 'arsoapi.views.image_radar'
	else:
		image_view = 'arsoapi.views.align_radar'

	return _kml_radar(request, reverse(image_view))

def _kml_radar(request, image_url):
	m = geocoded_radar
	m.refresh()
	context = _kml_file(m)
	context.update({
		'host': request.META.get('HTTP_HOST', 'localhost'),
		'image_url': image_url,
		'description': 'Radarska slika padavin',
		})
	return render_to_response('template.kml', context)

def kml_toca(request):
	m = geocoded_toca
	m.refresh()
	context = _kml_file(m)
	context.update({
		'host': request.META.get('HTTP_HOST', 'localhost'),
		'image_url': reverse('arsoapi.views.image_toca'),
		'description': 'Verjetnost toce',
		})
	return render_to_response('template.kml', context)

def _png_image(model):
	model.processed.open()
	img = Image.open(model.processed).convert('RGBA')

	a = numpy.array(numpy.asarray(img))

	# select white color
	d = (a[:,:,0] == WHITE[0]) & (a[:,:,1] == WHITE[1]) & (a[:,:,2] == WHITE[2])

	# make white pixels completely transparent
	a[d,3] = 0
	# make non-white pixels partially transparent
	a[~d,3] = 128

	return _png_image_fromarray(a)

def _png_image_fromarray(a):
	s = StringIO()
	img = Image.fromarray(a, mode='RGBA')
	img.save(s, 'png')
	data = s.getvalue()
	return HttpResponse(data, mimetype='image/png')

def tz2utc_diff():
	now = datetime.datetime.now().replace(second=0, microsecond=0)
	utcnow = datetime.datetime.utcnow().replace(second=0, microsecond=0)
	
	return (now - utcnow)

@jsonresponse
def report(request):
	geocoded_radar.refresh()
	geocoded_toca.refresh()
	geocoded_aladin.refresh()
	
	try:
		lat = float(request.GET.get('lat'))
		lon = float(request.GET.get('lon'))
	except:
		return {
			'status': 'fail',
			'error': 'Invalid parameters.'
		}
	
	if not (45.21 <= lat <= 47.05 and 12.92 <= lon <= 16.71):
		return {
			'status': 'fail',
			'error': 'Coordinates out of bounds.'
			}
	else:
		posR, rain_mmph = geocoded_radar.get_rain_at_coords(lat, lon)
		posT, toca_level = geocoded_toca.get_toca_at_coords(lat, lon)
		posA, forecast = geocoded_aladin.get_forecast_at_coords(lat, lon)
		
		utc_diff = tz2utc_diff()
		
		resp = {
			'status': 'ok',
			'lat': request.GET.get('lat'),
			'lon': request.GET.get('lon'),
			'copyright': u'ARSO, Agencija RS za okolje',
			'radar': {
				'updated': _datetime2timestamp(geocoded_radar.last_modified + utc_diff),
				'updated_text': (geocoded_radar.last_modified + utc_diff).strftime('%Y-%m-%d %H:%M'),
				'x': posR[0],
				'y': posR[1],
				'rain_level': mmph_to_level(rain_mmph),
				'rain_mmph': rain_mmph,
			},
			'hailprob': {
				'updated': _datetime2timestamp(geocoded_toca.last_modified + utc_diff),
				'updated_text': (geocoded_toca.last_modified + utc_diff).strftime('%Y-%m-%d %H:%M'),
				'x': posT[0],
				'y': posT[1],
				'hail_level': toca_level,
			},
			'forecast': {
				'updated': _datetime2timestamp(geocoded_aladin.forecast_time.get(6, None)),
				'x': posA[0],
				'y': posA[1],
				'data': forecast,
			}
		}
		return resp





