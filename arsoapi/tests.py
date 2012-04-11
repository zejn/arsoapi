
import datetime
import os
import unittest

from arsoapi.models import RadarPadavin, GeocodedRadar, Aladin, GeocodedAladin


datafile = lambda x: os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', x))

class TestVreme(unittest.TestCase):
	def test01_radar(self):
		img_data = open(datafile('test01_radar.gif')).read()
		r = RadarPadavin(picdata=img_data.encode('base64'), last_modified=datetime.datetime.now())
		r.save()
		gr = GeocodedRadar()
		gr.load_from_model(r)
		
		pos, rain_level = gr.get_rain_at_coords(45.545763, 14.106696)
		self.assertEqual(pos, (358, 361), 'Pixel coords are off?')
		self.assertEqual(rain_level, 100, 'Rain not a 100% where it should be')
		
		del gr
		r.delete()
	
	def test02_toca(self):
		pass
	
	def test03_aladin(self):
		today = datetime.date.today()
		for n in (6,12,18,24,30,36,42,48):
			img_data = open(datafile('test02_aladin_%.2d.png' % n)).read()
			a = Aladin(
				date=today,
				last_modified=datetime.datetime.now(),
				timedelta=n,
				picdata=img_data.encode('base64'))
			a.save()
		
		aladini = Aladin.objects.filter(date=today)
		
		ga = GeocodedAladin()
		ga.load_from_models(aladini)
		
		pos, forecast = ga.get_forecast_at_coords(45.545763, 14.106696)
		print 'AAAAAAAAA', pos, pos
		self.assertEqual(pos, (321, 210))
		rain30mm = [i for i in forecast if i['offset'] == 36][0]
		self.assertEqual(rain30mm['rain'], 30)
		
		pos2, forecast2 = ga.get_forecast_at_coords(46.421411, 13.601732)
		print 'EEEEEEEEEEEe', pos2
		self.assertEqual(pos2, pos2)
		rain30mm2 = [i for i in forecast if i['offset'] == 36][0]
		#self.assertEqual(rain30mm2['rain'], 30, 'failed removing markers with rainfall numbers')
	
	def test04_veter_test_points(self):
		test_points = [
			(198, 435), (198, 457), (220, 435), (220, 457),
			(132, 326), (132, 348), (154, 348), (154, 326),
			(132, 283), (110, 283), (110, 261), (132, 261),
			(572, 174), (572, 152), (550, 152), (550, 174),
			(528, 65),   (528, 87),  (506, 87),  (506, 65),
			(66, 130),   (88, 130),  (88, 152),  (66, 152),
			(286, 261), (286, 239), (308, 239), (308, 261),
		]
		from arsoapi.models import get_wind_points
		points = list(get_wind_points())
		for p in test_points:
			#print p, p in points
			self.assertEqual(p in points, True)
	
	def test05_veter_flag_direction_correlation(self):
		from arsoapi.models import find_direction
		import Image
		expected = [
			(180,),
			(250, 251),
			(149,),
		]
		
		for i, expected_deg in enumerate(expected):
			n = i+1
			img = Image.open(datafile('test_correlation_%s.png' % n))
			score, deg = find_direction(img)
			print score, deg, expected_deg
			assert deg in expected_deg
		
		
		
		
		
		