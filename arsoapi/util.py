from urllib.request import urlopen

from operator import itemgetter as _itemgetter
from datetime import datetime
from email.utils import parsedate

# python 2.7 imitation of counter
class Counter(dict):
	def __missing__(self, k):
		return 0
	
	def most_common(self, n=None):
		return sorted(self.items(), key=_itemgetter(1), reverse=True)

def _parse_http_datetime(s):
	return datetime(*parsedate(s)[:6])

def fetch(url, postdata=None):
	u = urlopen(url, postdata)
	obfuscated_data = u.read()
	last_modified = _parse_http_datetime(u.headers.get('last-modified'))
	return obfuscated_data, last_modified
