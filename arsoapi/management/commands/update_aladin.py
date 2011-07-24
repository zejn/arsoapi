
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
	def handle(self, *args, **options):
		from arsoapi.models import Aladin, fetch_aladin
		import datetime
		
		now = datetime.datetime.now()
		ft = datetime.datetime(now.year, now.month, now.day)
		if now.hour > 17:
			ft = ft.replace(hour=12)
		for n in range(6,73,3):
			img_data, last_modified = fetch_aladin(n)
			a = Aladin(timestamp=last_modified, forecast_time=ft, timedelta=n, picdata=img_data.encode('base64'))
			a.save()
		
