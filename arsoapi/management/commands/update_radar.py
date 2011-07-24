
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from arsoapi.models import RadarPadavin, fetch_radar, filter_radar, annotate_geo_radar
		import simplejson
		
		imgdata, last_modified = fetch_radar()
		r = RadarPadavin(picdata=imgdata.encode('base64'), last_modified=last_modified)
		r.save()
		
