#!/usr/bin/python

import Image
import ImageFilter
import ImageOps

edge1 = ImageFilter.Kernel((3,3), [1,1,1, 1,-8,1, 1,1,1])
edge2 = ImageFilter.Kernel((3,3), [1,4,1, 4,-20,4, 1,4,1])
edge3 = ImageFilter.Kernel((3,3), [0,1,0, 1,-4,1, 0,1,0])

im = Image.open('aladin1_21.png').convert('RGB')
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
		pix2[i,j] = tuple(new_pix)
		

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

im2.save('ba/foobar.png')

