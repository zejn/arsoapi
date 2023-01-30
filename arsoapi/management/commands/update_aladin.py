
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from arsoapi.models import Aladin, fetch_aladin
		import datetime
		import base64
		
		now = datetime.datetime.now()
		hour = 0
		if  14 < now.hour <= 23:
			hour = 12
		if 0 <= now.hour <= 4:
			hour = 12
			now = now - datetime.timedelta(1)
		ft = datetime.datetime(now.year, now.month, now.day, hour)
		
		class AlreadyProcessed(Exception): pass
		try:
			for n in range(6,73,3):
				img_data, last_modified = fetch_aladin(ft, n)
				try:
					a = Aladin.objects.get(forecast_time=ft, timedelta=n)
					raise AlreadyProcessed()
				except Aladin.DoesNotExist:
					a = Aladin(timestamp=last_modified, forecast_time=ft, timedelta=n, picdata=base64.b64encode(img_data))
					a.save()
					a.process()
		except AlreadyProcessed:
			pass
