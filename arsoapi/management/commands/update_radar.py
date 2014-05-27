
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from arsoapi.models import RadarPadavin, fetch_radar
		from StringIO import StringIO
		from PIL import Image
		
		imgdata, last_modified = fetch_radar()
		image = Image.open(StringIO(imgdata))
		try:
			r = RadarPadavin.objects.get(last_modified=last_modified)
		except RadarPadavin.DoesNotExist:
			r = RadarPadavin(picdata=imgdata.encode('base64'), last_modified=last_modified)
			r.save()
			assert image.size == (821, 660)
			r.process()
