
import _laplacian

# print(dir(_laplacian))
from pprint import pprint

from PIL import Image
from io import BytesIO
import re

im = Image.open('b.png').convert('RGB')
#im = Image.open('t2.ppm').convert('RGB')
s = BytesIO()
im.save(s, 'ppm')

ppm = s.getvalue()
del s

header_match = re.match('^P6\n(\d+)\s(\d+)\n(\d+)\n', ppm, re.M)
print('dim', header_match.groups())

header, raw_data = ppm[:header_match.end()], ppm[header_match.end():]

w, h = im.size
print(im.size)

#itt = iter((ord(i) for i in raw_data))
#imgbytes = zip(itt, itt, itt)
#pprint(imgbytes)
print('='*10)
print('Going in')

result = _laplacian.ppm_laplacian(im.size, raw_data)

f = open('cresult.ppm','wb')
f.write(header)
f.write(result)


d = open('t2_end.ppm').read()
itt = iter((ord(i) for i in d[11:]))
imgbytes = zip(itt, itt, itt)
pprint(imgbytes)



#_laplacian.ppm_laplacian(w, h) # raw_data)


