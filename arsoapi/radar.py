import numpy as np
from PIL import Image, ImageDraw
import math
from arsoapi.models import filter_radar
import time
import collections

red = (0xfa, 0x00, 0x00)
orange = (0xfa, 0x7d, 0x00)
yellow = (0xfa, 0xe1, 0x00)
green = (0x19, 0xb9, 0x00)
gray = (0x90, 0x90, 0x90)
white = (0xff, 0xff, 0xff)

remap = {
    red: 0,
    orange: 50,
    yellow: 100,
    green: 150,
    gray: 200,
    white: 255
    }

COLORS = remap.values()


def score_xor(arr_a, arr_b):
    err = np.bitwise_xor(arr_a, arr_b)
    score = err.sum()
    return score

def score_square_xor(arr_a, arr_b):
    err = np.bitwise_xor(arr_a, arr_b)
    score = (err * err).sum()
    return score


def vreme_estimate(img1, img2, BS=16, score_func=score_square_xor, max_dist=None):
    """
    In current implementation, max_dist should be at least BS/2
    """
    assert img1.shape == img2.shape
    if max_dist is None:
        max_dist = BS
    DS = max_dist
    
    mask = np.ones(img1.shape, np.uint8) * 255
    
    img1 = mask - img1
    img2 = mask - img2
    
    dimx, dimy = img1.shape
    print dimx, dimy
    
    blocks = []
    # score adjustment punishes large vectors more severely
    score_adj = [1/((math.e ** (1.0/ (i-DS-1)))/(math.e ** (1.0/ (-DS-1)))) for i in xrange(0, DS+1)]
    #print score_adj
    
    for x in xrange(1, dimx/DS-1): # was dimx/DS-1
        for y in xrange(1, dimy/DS-2): # was dimy/DS-2
            #print x*DS-DS, x*DS+DS+BS, y*DS-DS, y*DS+DS+BS
            prev = img1[x*DS-DS:x*DS+DS+BS, y*DS-DS:y*DS+DS+BS]
            nxt = img2[x*DS-DS:x*DS+DS+BS, y*DS-DS:y*DS+DS+BS]
            
            block = prev[DS:DS+BS, DS:DS+BS]

            if block.sum() == 0:
                # skip blank blocks
                #print 'skipping blank block'
                continue
            
            if len(np.unique(block)) == 1:
                # skip blocks that are not diverse enough to carry information
                # because we can't determine where to fit best
                #print 'too small patch:', (x, y)
                continue
        
            if np.where(block!=0,1,0).sum() < DS+DS:
                #print 'too small block'
                continue
            
            scores = []
            
            for dx in xrange(0, DS+DS):
                for dy in xrange(0, DS+DS):
                    if abs(dx-DS)+abs(dy-DS) > DS:
                        # use maximum as manhattan distance so dont allow both 
                        # coordinates to go to the max
                        continue
                    nnxt = nxt[dx:dx+BS, dy:dy+BS]

                    score = score_func(block, nnxt)
                    score = score * score_adj[abs(dx-DS)] * score_adj[abs(dy-DS)]
                    
                    scores.append((score, (dx-DS, dy-DS)))
            candidates = list(sorted(scores))
            pos = candidates[0][1]
            #print (x,y), block.sum(), candidates
            
            if (x,y) == (111, 3,1):
                print 'WOO'
                print prev
                print 'WOOW'
                print nxt
                print 'seeking'
                print block
                print 'found at', pos
                print nxt[BS+pos[0]:BS+pos[0]+BS,BS+pos[1]:BS+pos[1]+BS]
            
            blocks.append((
                (x,y),
                #(x*DS, y*DS),
                pos
                ))
    return blocks

def draw_motion(vectors, size, BS=16):
    
    im = Image.new('L', size, 255)
    draw = ImageDraw.Draw(im)
    for b, v in vectors:
        #print b, v
        pt_from = (BS*b[0]+BS/2, BS*b[1]+BS/2)
        pt_to = (pt_from[0]+v[0], pt_from[1]+v[1])
        draw.line((pt_from, pt_to), fill=0)

    del draw
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im = im.transpose(Image.ROTATE_90)
    #im = im.resize((im.size[0]*4, im.size[1]*4), Image.BILINEAR)
    im.save('motion.png')

# format vektorjev:
# ((blok-y, blok-x), (motion-y, motion-x))

def vreme_transform(im1, im2):

    bs = BS/2
    
    imc = im1.convert('RGB')
    vec = {}
    for v in d:
        vec[v[0]] = v[1]
    
    quads = []
    for bx in xrange(1, 10):
        for by in xrange(1, 7):
            ty, tx = vec.get( (by, bx), (0, 0) )
            # FIXME utezi spremembe z okoliskimi 
            q = (
                (bs*bx, bs*by, bs*(bx+1), bs*(by+1)),
                (bs*bx-tx, bs*by-ty, bs*bx-tx, bs*(by+1)-ty, bs*(bx+1)-tx, bs*(by+1)-ty, bs*(bx+1)-tx, bs*by-ty)
            )
            #print q
            quads.append(q)

    imc = imc.transform(im1.size, Image.MESH, quads)
    return imc

def has_rain(img):
    img = img.convert('RGB')
    img = img.crop((9,48,809,648))
    pixdata = img.load()
    siz = img.size
    
    img.save('tmp_test01.png')
    
    for x in xrange(0, siz[0], 3):
        for y in xrange(0, siz[1], 3):
            if pixdata[(x,y)] == green:
                return True
    return False

def pic2rawdata(img):
    filtered = filter_radar(img)
    
    cropped = filtered.crop((9,48,809,648))
    
    # FIXME testing correlation
    #cropped = cropped.crop((384, 320, 384+320, 320+192))
    
    
    pixdata = cropped.load()
    siz = cropped.size

    # remove light gray area
    for x in xrange(siz[0]):
        for y in xrange(siz[1]):
            if pixdata[(x,y)] == (0xd7, 0xd7, 0xd7):
                pixdata[(x,y)] = (0xff, 0xff, 0xff)
    
    """
    d = {}
    for x in xrange(siz[0]):
        for y in xrange(siz[1]):
            d.setdefault(pixdata[(x,y)], 1)
    """
    #print fn, d.keys()
    
    #cropped.save('foobar.png')
    
    imgdata = np.empty(siz, np.uint8)
    
    new = Image.new('L', siz, 0xff)
    newpix = new.load()
    for x in xrange(siz[0]):
        for y in xrange(siz[1]):
            nx = x
            if x == 0:
                nx = 1
            ny = y
            if ny == 0:
                ny = 1
            
            newpix[(x,y)] = remap[pixdata[(nx,ny)]]
            imgdata[x,y] = remap[pixdata[(nx,ny)]]
    
    colors = remap.values()
    def nearest(c):
        n = list(sorted([(abs(i-c), i) for i in colors]))
        return n[0][1]

    imgdata2 = np.empty((siz[0]/4, siz[1]/4), np.uint8)
    
    for x in xrange(0, siz[0], 4):
        for y in xrange(0, siz[1], 4):
            
            color = imgdata[x:x+4,y:y+4].sum()/16.0
            #print x, y, color, nearest(color)
            imgdata2[x/4,y/4] = nearest(color)
    
    
    return imgdata2.T
    
    #new.save('processed_' + fn + '.png')
    #misc.imsave('search_' + fn + '.png', imgdata2.T)
    #np.save(open('processed_' + fn + '.npy', 'wb'), imgdata)
    #np.save(open('search_' + fn + '.npy', 'wb'), imgdata2.T)