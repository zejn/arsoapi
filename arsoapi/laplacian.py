
# Second degree Laplacian edge detection, copied from Gimp

__all__ = ['laplacian']

def _py_laplacian(im):
	im = im.convert('RGB')
	pix = im.load()
	orig_im = im.copy()
	
	im2 = im.copy()
	pix2 = im2.load()
	
	for i in range(1, im.size[0]-1):
		for j in range(1, im.size[1]-1):
			neigh4 = (
				pix[i-1,j],
				pix[i+1,j],
				pix[i,j],
				pix[i,j-1],
				pix[i,j+1]
				)
			by_color4 = zip(*neigh4)
			minv = [min(a) for a in by_color4]
			maxv = [max(a) for a in by_color4]
			p = pix[i,j]
			grad = tuple([0.5 * max(maxv[n]-p[n], p[n]-minv[n]) for n in range(3)])
			
			neigh8 = (
				pix[i-1, j-1],
				pix[  i, j-1],
				pix[i+1, j-1],
				pix[i-1,   j],
				# pix[i+1, j-1], 
				pix[i+1,   j],
				pix[i-1, j+1],
				pix[  i, j+1],
				pix[i+1, j+1]
				)
			
			by_color8 = zip(*neigh8)
			new_pix = []
			for x in range(3):
				if (sum(by_color8[x]) - 8*p[x]) > 0:
					new_pix.append(grad[x])
				else:
					new_pix.append(128 + grad[x])
			pix2[i,j] = tuple((int(a) for a in new_pix))
	
	im = im2
	pix = pix2
	im2 = im.copy()
	pix2 = im2.load()
	
	for i in range(1, im.size[0]-1):
		for j in range(1, im.size[1]-1):
			
			neigh8 = (
				pix[i-1, j-1],
				pix[  i, j-1],
				pix[i+1, j-1],
				pix[i-1,   j],
				# pix[i+1, j-1], 
				pix[i+1,   j],
				pix[i-1, j+1],
				pix[  i, j+1],
				pix[i+1, j+1]
				)
			
			by_color8 = zip(*neigh8)
			p = pix[i,j]
			
			new_p = []
			
			for x in range(3):
				
				if (p[x] <= 128) and any((n > 128 for n in by_color8[x])):
					if p[x] >= 128:
						new_p.append(p[x] - 128)
					else:
						new_p.append(p[x])
				else:
					new_p.append(0)
			
			if any((a > 15 for a in new_p)):
				pix2[i,j] = tuple(new_p)
			else:
				pix2[i,j] = (255, 255, 255)
	return im2


try:
	from arsoapi import _laplacian
	_laplacian.ppm_laplacian # this is foo!

except (ImportError, AttributeError) as e:
	print(e)
	_laplacian = None

if _laplacian is None:
	laplacian = _py_laplacian
else:
	#print 'Using C laplacian'
	from io import BytesIO
	import re
	from PIL import Image
	
	def laplacian(im):
		s = BytesIO()
		im.save(s, 'ppm')
		ppm = s.getvalue()
		del s

		identifier, sep, remains = ppm.partition(b'\n')
		dimensions, sep, remains = remains.partition(b'\n')
		depth, sep, raw_data = remains.partition(b'\n')

		header = identifier + b'\n' + dimensions + b'\n' + depth + b'\n'

		#header_match = re.match('^P6\n(\d+)\s(\d+)\n(\d+)\n', ppm, re.M)
		#header, raw_data = ppm[:header_match.end()], ppm[header_match.end():]

		result = _laplacian.ppm_laplacian(im.size, raw_data)

		s = BytesIO()
		s.write(header)
		s.write(result)
		s.seek(0)
		im = Image.open(s)
		im.load()
		del s
		return im

