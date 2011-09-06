from django.core.management.base import BaseCommand

class Command(BaseCommand):
	def handle(self, *args, **options):
		from arsoapi.models import Toca
		from arsoapi.views import dump_data
		import datetime
		
		if len(args):
			day = datetime.datetime.strptime(args[0], '%Y-%m-%d')
		else:
			day = datetime.datetime.now() - datetime.timedelta(2)
		
		dump_data(model=Toca, day=day)
