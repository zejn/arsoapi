
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from arsoapi.models import Aladin, fetch_aladin
		import datetime
		
		now = datetime.datetime.now()
		hrs = '0000'
		if  12 < now.hour <= 23:
			hrs = '1200'
		if 0 <= now.hour <= 4:
			hrs = '1200'
			now = now - datetime.timedelta(1)
		
		for n in range(6,73,3):
			img_data, last_modified = fetch_aladin(n)
			a = Aladin(timestamp=last_modified, forecast_time=ft, timedelta=n, picdata=img_data.encode('base64'))
			a.save()
			a.process()
		
