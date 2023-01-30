
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from django.core.files import File
		from arsoapi.models import Toca, fetch_toca
		import simplejson
		import base64
		
		imgdata, last_modified = fetch_toca()
		try:
			r = Toca.objects.get(last_modified=last_modified)
		except Toca.DoesNotExist:
			r = Toca(picdata=base64.b64encode(imgdata), last_modified=last_modified)
			r.save()
			r.process()
