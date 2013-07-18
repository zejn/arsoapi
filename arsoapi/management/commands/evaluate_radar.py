
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
    def handle(self, *args, **options):
        import datetime
        import json
        import os
        import time

        from PIL import Image
        import numpy as np
        from arsoapi.radar import pic2rawdata, has_rain, vreme_transform
        from StringIO import StringIO

        join = os.path.join
        PTH = args[0]
        GIFDIR = args[1]
        
        count = 0
        for f in sorted(os.listdir(PTH)):
            fn = join(PTH, f)
            print fn
            d = json.load(open(fn))
            for item in d:
                t1 = time.time()
                outfn = join(GIFDIR, 'radar_%s.png' % item['last_modified'].replace('T', '_').replace(':', ''))
                #print fn
                if os.path.exists(outfn):
                    continue
                data = item['picdata'].decode('base64')
                
                s = StringIO(data)
                img = Image.open(s)
                
                t11 = time.time()
                rain = has_rain(img)
                t12 = time.time()
                print 'rain', rain, t12-t11
                
                if not rain:
                    continue
                
                p = pic2rawdata(img)
                
                inverse = np.ones(p.shape, dtype=np.uint8)*255 - p
                if sum(sum(inverse.astype(np.uint32))) == 0:
                    # empty image
                    pass
                else:
                    # save image
                    p2 = Image.fromarray(p)
                    p2.save(outfn)
                    ts = int(datetime.datetime.strptime(item['last_modified'], '%Y-%m-%dT%H:%M:%S').strftime('%s'))
                    os.utime(outfn, (ts, ts))

                
                t2 = time.time()
                print t2-t1, outfn
                count += 1
                #if count == 100:
                    #raise ValueError
                    
