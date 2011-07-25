
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from django.core.files import File
		from arsoapi.models import Toca, fetch_toca
		import simplejson
		
		imgdata, last_modified = fetch_toca()
		r = Toca(picdata=imgdata.encode('base64'), last_modified=last_modified)
		r.save()
		r.process()
