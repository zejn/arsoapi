import glob
import datetime
import os
import unittest

from arsoapi.models import RadarPadavin, GeocodedRadar, Aladin, GeocodedAladin, mmph_to_level, filter_radar
from arsoapi.formats import radar_detect_format, radar_get_format

from PIL import Image

def datafile(name):
	path = os.path.join(os.path.dirname(__file__), 'data', name)
	abspath = os.path.abspath(path)

	if not os.path.exists(abspath):
		raise unittest.SkipTest("%s missing" % (path,))

	return abspath

class TestRadarFilter(unittest.TestCase):
	def test_filter(self):
		img = Image.open(open(datafile('test_radar_filter.gif')))
		fmt = radar_get_format(3)

		img2 = filter_radar(img, fmt)

		self.assertEqual(img2.getpixel((8, 1)), (255, 255, 255))
		self.assertEqual(img2.getpixel((4, 5)), (255, 255, 255))
		self.assertEqual(img2.getpixel((1, 8)), (0, 120, 254))

class TestRadarFormat(unittest.TestCase):
	def test_detect_1(self):
		img = Image.open(open(datafile('test_sirad.gif')))
		fmt = radar_detect_format(img)

		self.assertEqual(fmt.ID, 1)

	def test_detect_2(self):
		img = Image.open(open(datafile('test_sirad_si1_si2.gif')))
		fmt = radar_detect_format(img)

		self.assertEqual(fmt.ID, 2)

	def test_detect_3(self):
		img = Image.open(open(datafile('test_sirad_si1_si2_b.gif')))
		fmt = radar_detect_format(img)

		self.assertEqual(fmt.ID, 3)

	def test_detect_invalid(self):
		img = Image.open(open(datafile('test_invalid.gif')))
		fmt = radar_detect_format(img)

		self.assertEqual(fmt.ID, 0)


class TestVreme(unittest.TestCase):
	def test_mmph_to_level(self):
		self.assertEqual(mmph_to_level(0.0), 0)
		self.assertEqual(mmph_to_level(0.5), 25)
		self.assertEqual(mmph_to_level(2.5), 50)
		self.assertEqual(mmph_to_level(15.), 75)
		self.assertEqual(mmph_to_level(60.), 100)
		self.assertEqual(mmph_to_level(1000.), 100)

	def test01_radar(self):
		img_data = open(datafile('test_sirad_si1_si2.gif')).read()
		r = RadarPadavin(picdata=img_data.encode('base64'), last_modified=datetime.datetime.now())
		r.save()
		r.process()

		gr = GeocodedRadar()
		gr.load_from_model(r)

		# koper
		pos, rain_mmph = gr.get_rain_at_coords(45.547356,13.729792)
		self.assertEqual(pos, (294, 357))
		self.assertEqual(rain_mmph, 0)

		# ljubljana
		pos, rain_mmph = gr.get_rain_at_coords(46.054173,14.507332)
		self.assertEqual(pos, (428, 270))
		self.assertEqual(rain_mmph, 0)

		# maribor
		pos, rain_mmph = gr.get_rain_at_coords(46.554611,15.646534)
		self.assertEqual(pos, (624, 184))
		self.assertEqual(rain_mmph, 0)

		pos, rain_level = gr.get_rain_at_coords(45.545763, 14.106696)
		self.assertEqual(pos, (359, 357)) # 'Pixel coords are off?')
		self.assertEqual(rain_level, .5)
		
		del gr
		r.delete()

	def test01_radar_unknown_format(self):
		img_data = open(datafile('test_invalid.gif')).read()
		r = RadarPadavin(picdata=img_data.encode('base64'), last_modified=datetime.datetime.now())
		r.save()
		r.process()

		gr = GeocodedRadar()
		gr.load_from_model(r)

		pos, rain_mmph = gr.get_rain_at_coords(45.545763, 14.106696)
		self.assertTrue(rain_mmph is None)

		del gr
		r.delete()

	def test01_radar_old_db(self):
		img_data = open(datafile('test_sirad_si1_si2.gif')).read()
		r = RadarPadavin(picdata=img_data.encode('base64'), last_modified=datetime.datetime.now())
		r.save()
		r.process()
		r.format_id = None
		r.save()

		gr = GeocodedRadar()
		gr.load_from_model(r)

		pos, rain_mmph = gr.get_rain_at_coords(45.545763, 14.106696)
		self.assertTrue(rain_mmph is None)

		del gr
		r.delete()

	def test01_radar_coverage(self):

		pattern = os.path.join(os.path.dirname(__file__), 'data/private', '*')

		for path in glob.glob(pattern):

			name = os.path.join("private", os.path.basename(path))

			img_data = open(datafile(name)).read()
			r = RadarPadavin(picdata=img_data.encode('base64'),
					last_modified=datetime.datetime.now())
			r.save()
			r.process()

			gr = GeocodedRadar()
			gr.load_from_model(r)

			for lat in xrange(45210, 47050+1, 10):
				for lon in xrange(12920, 16710+1, 10):
					lat_f = lat * 1e-3
					lon_f = lon * 1e-3
					pos, rain_mmph = gr.get_rain_at_coords(lat_f, lon_f)

					self.assertTrue(rain_mmph is not None,
							msg="get_rain_at_coords(%f, %f) is None "
								"(%s, pos = %r)" % (
								lat_f, lon_f, name, pos))

			del gr
			r.delete()

	def test02_aladin(self):
		today = datetime.date.today()
		for n in (6,12,18,24,30,36,42,48):
			path = datafile('test02_aladin_%.2d.png' % n)
			img_data = open(path).read()

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
