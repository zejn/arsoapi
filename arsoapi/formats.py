class RadarImageFormat():
	ID = 0

	SOURCE = "Unknown"

	COLOR_IGNORE = set()
	COLOR_BG = (255, 255, 255)
	COLOR_TO_MMPH = {}

	GCP = ()

	def __init__(self):
		self.COLOR_TO_MMPH[self.COLOR_BG] = 0.

class SIRAD(RadarImageFormat):
	ID = 1

	SOURCE = "ARSO SIRAD"

	COLOR_IGNORE = frozenset( (
		(96, 96, 96),
	) )

	COLOR_TO_MMPH = {
		( 25, 185,   0):	   .5,
		(250, 225,   0):	  2.0,
		(250, 125,   0):	 15.0,
		(250,   0,   0):	100.0,
	}

	GCP = (
		(251, 246, 401712, 154018),
		(625, 215, 589532, 169167),
		(507, 479, 530526, 38229),
	)

class SIRAD_SI1SI2(RadarImageFormat):
	ID = 2

	SOURCE = "ARSO SIRAD SI1 SI2"

	COLOR_IGNORE = frozenset( (
		(96, 96, 96),
		(16, 16, 16),
	) )

	COLOR_TO_MMPH = {
		(  0, 125,   0):	.2, # interp.
		( 50, 150,   0):	.5,
		(100, 175,   0):	.7, # interp.
		(150, 200,   0):	1.0,
		(200, 225,   0):	1.5, # interp.
		(250, 225,   0):	2.0,
		(250, 187,   0):	3.5, # interp.
		(250, 125,   0):	5.0,
		(250,  62,   0):	10.0, # interp.
		(250,   0,   0):	15.0,
		(225,   0,  50):	33.0, # interp.
		(200,   0, 125):	50.0,
		(175,   0, 200):	75.0, # interp.
		(150,	0, 225):	100.0,
		(125,   0, 250):	150.0, # interp.
	}

	GCP = (
		(250, 245, 401712, 154018),
		(624, 214, 589532, 169167),
		(506, 478, 530526, 38229),
	)

class SIRAD_SI1SI2_B(SIRAD_SI1SI2):
	ID = 3

	SOURCE = "ARSO SIRAD SI1 SI2 B"

	COLOR_TO_MMPH = {
		(  8,  70, 254):	.2,
		(  0, 120, 254):	.5,
		(  0, 174, 253):	.7,
		(  0, 220, 254):	1.0,
		(  4, 216, 131):	1.5,
		( 66, 235,  66):	2.0,
		(108, 249,   0):	3.5,
		(184, 250,   0):	5.0,
		(249, 250,   0):	10.0,
		(254, 198,   0):	15.0,
		(254, 132,   0):	33.0,
		(255,  62,   1):	50.0,
		(211,   0,   0):	75.0,
		(181,   3,   3):	100.0,
		(203,   0, 204):	150.0,
	}

class SIRAD_SI1SI2_C(SIRAD_SI1SI2):
	ID = 4

	SOURCE = "ARSO SIRAD SI1 SI2 C"

	COLOR_TO_MMPH = {
		(  8,  90, 254):	.2,
		(  0, 140, 254):	.5,
		(  0, 174, 253):	.7,
		(  0, 200, 254):	1.0,
		(  4, 216, 131):	1.5,
		( 66, 235,  66):	2.0,
		(108, 249,   0):	3.5,
		(184, 250,   0):	5.0,
		(249, 250,   0):	10.0,
		(254, 198,   0):	15.0,
		(254, 132,   0):	33.0,
		(255,  62,   1):	50.0,
		(211,   0,   0):	75.0,
		(181,   3,   3):	100.0,
		(203,   0, 204):	150.0,
	}

def radar_get_format(id):
	return _id_to_format.get(id, _id_to_format[0])

def radar_detect_format(img):

	if img.size == (819, 658):
		return SIRAD()
	if img.size == (821, 660):
		c = img.convert('RGB').getpixel((804, 32))
		if c == (125, 0, 250):
			return SIRAD_SI1SI2()

		c = img.convert('RGB').getpixel((620, 32))
		if c == (0, 120, 254):
			return SIRAD_SI1SI2_B()
		elif c == (0, 140, 254):
			return SIRAD_SI1SI2_C()

	return RadarImageFormat()

_id_to_format = {}
for n in dir():
	cls = locals()[n]
	try:
		if issubclass(cls, RadarImageFormat):
			_id_to_format[cls.ID] = cls()
	except TypeError:
		pass
