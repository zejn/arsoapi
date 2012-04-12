
import Image
import os, sys
import glob
import datetime
import numpy


########### VETER

def color_invert(a):
	return tuple([0xff - i for i in a])

def convolve(a, b):
	assert a.size == b.size
	n = 0
	pixa = a.load()
	pixb = b.load()
	for x in xrange(a.size[0]):
		for y in xrange(a.size[1]):
			n += sum([i*j for i, j in
				zip(
					color_invert(pixa[(x,y)]),
					color_invert(pixb[(x,y)])
				)])
	return n

def find_direction(img):
	rotations = Image.open(datafile('wind_rotations.png'))
	off = 45
	sums = []
	for n in xrange(0, 360):
		mask = rotations.crop((n*off, 0, n*off+off, off))
		sums.append(convolve(mask, img))
	result = sorted([(i, n) for n, i in enumerate(sums)], reverse=True)
	
	# returns score, deg
	return result[0]

def flags2directions(img):
	orig = img.convert('L')
	off = 45
	nangles = 360
	oneimg = off*off
	n_invert = numpy.ones(off*off, dtype=numpy.uint32) * 0xff
	maskimg = Image.open('data/wind_rotations_vert.png').convert('L')
	n_mask = numpy.array(maskimg.getdata()).astype(numpy.uint32)
	n_mask_inverted = numpy.tile(n_invert, nangles) - n_mask
	wind = []
	for point in get_wind_points():
		x, y = point
		vetrovnica = orig.crop((x-23, y-23, x+22, y+22))
		v = n_invert - numpy.array(vetrovnica.getdata()).astype(numpy.uint32)
		vconvo = numpy.multiply(n_mask_inverted, numpy.tile(v, nangles))
		
		thiswind = []
		for n in xrange(nangles):
			thiswind.append((vconvo[n*oneimg:(n+1)*oneimg].sum(), n))
		
		wind.append((point, sorted(thiswind, reverse=True)[0]))
	return wind

def get_wind_points():
	off = 22
	for x in xrange(22+off, 640-off, 22):
		for y in xrange(22+off, 480-off, 22):
			yield (x, int(y / 22 * 21.7777777777777))

