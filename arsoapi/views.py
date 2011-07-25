from cStringIO import StringIO
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404

import datetime
import time
import Image
import simplejson
from arsoapi.models import (
	RadarPadavin, filter_radar, annotate_geo_radar, convert_geotiff_to_png, GeocodedRadar,
	Aladin, filter_aladin, annotate_geo_aladin, GeocodedAladin, GeocodedToca
	)

geocoded_radar = GeocodedRadar()
geocoded_toca = GeocodedToca()
geocoded_aladin = GeocodedAladin()

def _dumps(s):
	return simplejson.dumps(s, use_decimal=True, ensure_ascii=True)

def _datetime2timestamp(dt):
	return int(time.mktime(dt.timetuple()))

def jsonresponse(func):
	def _inner(*args, **kwargs):
		jsondata = func(*args, **kwargs)
		return HttpResponse(_dumps(jsondata), mimetype='application/json')
	return _inner

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
	
	if not (45.089036 <= lat <= 47.055154 and 12.919922 <= lon <= 16.831055):
		return {
			'status': 'fail',
			'error': 'Coordinates out of bounds.'
			}
	else:
		posR, rain_level = geocoded_radar.get_rain_at_coords(lat, lon)
		posT, toca_level = geocoded_toca.get_toca_at_coords(lat, lon)
		posA, forecast = geocoded_aladin.get_forecast_at_coords(lat, lon)
		
		utc_diff = tz2utc_diff()
		
		resp = {
			'status': 'ok',
			'lat': request.GET.get('lat'),
			'lon': request.GET.get('lon'),
			'radar': {
				'updated': _datetime2timestamp(geocoded_radar.last_modified + utc_diff),
				'updated_text': (geocoded_radar.last_modified + utc_diff).strftime('%Y-%m-%d %H:%M'),
				'x': posR[0],
				'y': posR[1],
				'rain_level': rain_level,
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





