from cStringIO import StringIO
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404

import datetime
import time
import Image
import simplejson
from arsoapi.models import (
	RadarPadavin, filter_radar, annotate_geo_radar, convert_geotiff_to_png, GeocodedRadar,
	Aladin, filter_aladin, annotate_geo_aladin, GeocodedAladin
	)

geocoded_radar = None
geocoded_aladin = None

def _dumps(s):
	return simplejson.dumps(s, use_decimal=True, ensure_ascii=True)

def _datetime2timestamp(dt):
	return int(time.mktime(dt.timetuple()))


def jsonresponse(func):
	def _inner(*args, **kwargs):
		jsondata = func(*args, **kwargs)
		return HttpResponse(_dumps(jsondata), mimetype='application/json')
	return _inner

def radar_full():
	global geocoded_radar
	
	if geocoded_radar is None:
		geocoded_radar = GeocodedRadar()
	r = RadarPadavin.objects.all()[0]
	geocoded_radar.load_from_model(r)

def aladin_full():
	global geocoded_aladin
	if geocoded_aladin is None:
		geocoded_aladin = GeocodedAladin()
	lastdate = Aladin.objects.all()[0]
	a = Aladin.objects.filter(forecast_time=lastdate.forecast_time)
	geocoded_aladin.load_from_models(a)

def get_radar(stage):
	r = RadarPadavin.objects.all()[0]
	if stage == '0':
		s = StringIO()
		r.pic.save(s, 'png')
		return s.getvalue()
	
	filtered = filter_radar(r.pic)
	if stage == '1':
		s = StringIO()
		filtered.save(s, 'png')
		return s.getvalue()
	
	annotated = annotate_geo_radar(filtered)
	if stage == '2':
		return convert_geotiff_to_png(annotated)
	raise Http404

def get_aladin(stage, n):
	a = Aladin.objects.filter(timedelta=n)[0]
	if stage == '0':
		s = StringIO()
		a.pic.save(s, 'png')
		return s.getvalue()
	filtered = filter_aladin(a.pic)
	if stage == '1':
		s = StringIO()
		filtered.save(s, 'png')
		return s.getvalue()
	annotated = annotate_geo_aladin(filtered)
	if stage == '2':
		return convert_geotiff_to_png(annotated)
	raise Http404

def image(request, what, stage, offset):
	if what == 'radar':
		data = get_radar(stage)
	elif what == 'aladin':
		try:
			offset = int(offset)
		except:
			raise Http404
		data = get_aladin(stage, offset)
	return HttpResponse(data, mimetype='image/png')

@jsonresponse
def report(request):
	if geocoded_radar is None:
		radar_full()
	if geocoded_aladin is None:
		aladin_full()
	
	try:
		lat = float(request.GET.get('lat'))
		lon = float(request.GET.get('lon'))
	except:
		return {
			'status': 'fail',
			'error': 'Invalid parameters.'
		}
	
	if not (45.089036 <= lat <= 47.055154 and 12.919922 <= lon <= 16.831055):
		return {
			'status': 'fail',
			'error': 'Coordinates out of bounds.'
			}
	else:
		posR, rain_level = geocoded_radar.get_rain_at_coords(lat, lon)
		posA, forecast = geocoded_aladin.get_forecast_at_coords(lat, lon)
		
		resp = {
			'status': 'ok',
			'lat': request.GET.get('lat'),
			'lon': request.GET.get('lon'),
			'radar': {
				'updated': _datetime2timestamp(geocoded_radar.last_modified),
				'updated_text': geocoded_radar.last_modified.strftime('%Y-%m-%d %H:%M'),
				'x': posR[0],
				'y': posR[1],
				'rain_level': rain_level,
			},
			'forecast': {
				'updated': _datetime2timestamp(geocoded_aladin.last_modified),
				'x': posA[0],
				'y': posA[1],
				'data': forecast,
			}
		}
		return resp





