from io import BytesIO
from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.utils._os import safe_join
from django.utils.timezone import make_aware, utc
from django.conf import settings
from django.db import models, connection

import datetime
import os
import time
from PIL import Image
import simplejson
from arsoapi.models import (
	GeocodedRadar, GeocodedToca, GeocodedAladin,
	RadarPadavin, Toca, Aladin,
	mmph_to_level,
	annotate_geo_radar,
	DataError,
	)
from arsoapi.formats import radar_get_format

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
		raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))

def dump_data(model, day, use_new=True):
	from django.db import connection
	yday = day + datetime.timedelta(1)
	the_day = datetime.datetime(day.year, day.month, day.day, 0, 0, 0)
	
	dump_dir = safe_join(settings.DUMP_DIR, the_day.strftime('%Y-%m'))

	if not os.path.isdir(dump_dir):
		os.makedirs(dump_dir)

	if use_new and the_day >= datetime.datetime(2015, 7, 31):
		# transition to utc timestamps
		if the_day == datetime.datetime(2015, 7, 31):
			start = the_day
			end = make_aware(start, utc) + datetime.timedelta(1)
		else:
			start = make_aware(the_day, utc)
			end = start + datetime.timedelta(1)

		qs = model.objects.filter(timestamp__gte=start, timestamp__lt=end)
		
		if qs.count() == 0:
			return

		sql, params = qs.query.get_compiler('default').as_sql()
		dump_file = safe_join(dump_dir, the_day.strftime(model.__name__.lower() + '_%Y-%m-%d.csv'))

		cur = connection.cursor()
		copy_sql = 'COPY (' + sql + ') TO stdout WITH CSV HEADER;'
		full_sql = cur.cursor.mogrify(copy_sql, params)

		f = open(dump_file, 'w')
		cur.cursor.copy_expert(full_sql, f)
		f.close()

		os.system('/bin/gzip -9f %s' % dump_file)

		qs.delete()
	else:
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
		dump_file = safe_join(dump_dir, the_day.strftime(model.__name__.lower() + '_%Y-%m-%d.json'))
		
		f = open(dump_file, 'w')
		for frag in simplejson.JSONEncoder(default=datetime_encoder).iterencode(dumper):
			f.write(frag)
		f.close()
		
		os.system('/bin/gzip -9 %s' % dump_file)
		
		qs.delete()

def jsonresponse(func):
	def _inner(*args, **kwargs):
		jsondata = func(*args, **kwargs)
		return HttpResponse(_dumps(jsondata), content_type='application/json')
	return _inner

def image_radar(request):
	r = RadarPadavin.objects.all()[0]
	return _png_image(r)

def align_radar(request):
	r = RadarPadavin.objects.all()[0]
	fmt = radar_get_format(r.format_id)

	geotiff = annotate_geo_radar(r.pic, fmt, scale=4)

	img = Image.open(BytesIO(geotiff)).convert('RGBA')

	a = numpy.array(numpy.asarray(img))
	d = numpy.zeros(a.shape[:2], dtype=numpy.bool)
	for c in fmt.COLOR_IGNORE:
		d |= (a[:,:,0] == c[0]) & (a[:,:,1] == c[1]) & (a[:,:,2] == c[2])

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
		image_view = 'arsoapi.views.align_radar'
	else:
		image_view = 'arsoapi.views.image_radar'
	return _kml_radar(request, reverse(image_view))

def _kml_radar(request, image_url):
	m = geocoded_radar
	m.refresh()
	context = _kml_file(m)
	expires = (datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=300)).isoformat() + 'Z'
	context.update({
		'host': request.META.get('HTTP_HOST', 'localhost'),
		'image_url': image_url,
		'description': 'Radarska slika padavin',
		'expires': expires,
		})
	return render('template.kml', context)

def kml_toca(request):
	m = geocoded_toca
	m.refresh()
	context = _kml_file(m)
	expires = (datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=300)).isoformat() + 'Z'
	context.update({
		'host': request.META.get('HTTP_HOST', 'localhost'),
		'image_url': reverse('arsoapi.views.image_toca'),
		'description': 'Verjetnost toce',
		'expires': expires,
		})
	return render('template.kml', context)

def _png_image(model):
	model.processed.open()
	img = Image.open(model.processed).convert('RGBA')

	fmt = radar_get_format(model.format_id)

	a = numpy.array(numpy.asarray(img))

	# select white color
	d =	(a[:,:,0] == fmt.COLOR_BG[0]) & \
		(a[:,:,1] == fmt.COLOR_BG[1]) & \
		(a[:,:,2] == fmt.COLOR_BG[2])

	# make white pixels completely transparent
	a[d,3] = 0
	# make non-white pixels partially transparent
	a[~d,3] = 128

	return _png_image_fromarray(a)

def _png_image_fromarray(a):
	s = BytesIO()
	img = Image.fromarray(a, mode='RGBA')
	img.save(s, 'png')
	data = s.getvalue()
	return HttpResponse(data, content_type='image/png')

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
	except Exception:
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
		response = {
			'lat': request.GET.get('lat'),
			'lon': request.GET.get('lon'),
			'copyright': u'ARSO, Agencija RS za okolje',
			'status': 'ok',
		}

		utc_diff = tz2utc_diff()

		def datetime2timestamp(dt_or_none, utc_diff):
			if dt_or_none is None:
				return None
			return _datetime2timestamp(dt_or_none + utc_diff)

		def datetime2text(dt_or_none, utc_diff):
			if dt_or_none is None:
				return None
			return (dt_or_none + utc_diff).strftime('%Y-%m-%d %H:%M')

		try:
			posR, rain_mmph = geocoded_radar.get_rain_at_coords(lat, lon)
		except DataError:
			response["radar"] = {
				"updated": None,
				"updated_text": None,
				"x": None,
				"y": None,
				"rain_level": None,
				"raim_mmph": None,
			}
		else:
			response['radar'] = {
				'updated': datetime2timestamp(geocoded_radar.last_modified, utc_diff),
				'updated_text': datetime2text(geocoded_radar.last_modified, utc_diff),
				'x': posR[0],
				'y': posR[1],
				'rain_level': mmph_to_level(rain_mmph),
				'rain_mmph': rain_mmph,
			}

		try:
			posT, toca_level = geocoded_toca.get_toca_at_coords(lat, lon)
		except DataError:
			response["hailprob"] = {
				"updated": None,
				"updated_text": None,
				"x": None,
				"y": None,
				"hail_level": None,
			}
		else:
			response['hailprob'] = {
				'updated': datetime2timestamp(geocoded_toca.last_modified, utc_diff),
				'updated_text': datetime2text(geocoded_toca.last_modified, utc_diff),
				'x': posT[0],
				'y': posT[1],
				'hail_level': toca_level,
			}

		try:
			posA, forecast = geocoded_aladin.get_forecast_at_coords(lat, lon)
		except DataError:
			response["forecast"] = {
				"updated": None,
				"x": None,
				"y": None,
				"data": None,
			}
		else:
			response['forecast'] = {
				'updated': _datetime2timestamp(geocoded_aladin.forecast_time.get(6, None)),
				'x': posA[0],
				'y': posA[1],
				'data': forecast,
			}

		return response
