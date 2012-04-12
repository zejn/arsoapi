
import Image
import os, sys
import glob
import datetime


# onetime scripts

def generate_rotateds():
	"generates 360 deg wind flags for use with correlation"
	import aggdraw
	import math
	def angle2coords(deg, linelen=16):
		a = math.cos(2*math.pi/360*deg) * linelen
		b = math.sin(2*math.pi/360*deg) * linelen
		return (int(a),int(b))

	img = Image.new('RGB', (360*45, 45), (255,255,255))
	d = aggdraw.Draw(img)
	pen = aggdraw.Pen((0,0,0), width=1.0)
	off = 22.5
	for deg in xrange(0, 360):
		#print deg
		a, b = angle2coords(deg)
		d.line(((2*off*deg)+off, off, (2*off*deg)+off+a, off+b), pen)
	
	d.flush()
	img.save('wind_rotations.png')

#generate_rotateds()


def make_veter_mask():
	"""
	One time use, more or less
	"""
	images = {}
	for fn in sorted(glob.glob('tests/veter/*.png')):
		print fn
		im = Image.open(fn).convert('RGB')
		size = im.size
		images[fn] = im.load()
	
	initial_color = (0xff, 0x00, 0xcc)
	mask = Image.new('RGB', size, initial_color)
	mask_pixels = mask.load()
	
	gray_threshold = 2
	for x in xrange(size[0]):
		print x
		for y in xrange(size[1]):
			this_color = {}
			for a in images.values():
				pixel = a[(x,y)]
				if not any([filter_red(pixel), filter_viola(pixel), filter_cyan(pixel), filter_blue(pixel)]):
					count = this_color.setdefault(pixel, 0)
					this_color[pixel] = count + 1
			candidates = sorted([(v, k) for k,v in this_color.items()], reverse=True)
			if candidates:
				cand = candidates[0][1]
				
				if cand[0] - cand[1] < gray_threshold and cand[0] - cand[2] < gray_threshold:
					mask_pixels[(x,y)] = cand
		
	mask.save('vetermask.png')

