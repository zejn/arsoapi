
from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
    def handle(self, *args, **options):
        import datetime
        import json
        import os
        import time

        import Image
        import numpy as np
        from arsoapi.radar import pic2rawdata, vreme_transform
        from StringIO import StringIO

        join = os.path.join
        PTH = args[0]
        GIFDIR = args[1]

        for f in os.listdir(PTH):
            fn = join(PTH, f)
            print fn
            d = json.load(open(fn))
            for item in d:
                t1 = time.time()
                outfn = join(GIFDIR, 'radar_%s.png' % item['last_modified'].replace('T', '_').replace(':', ''))
                #print fn
                data = item['picdata'].decode('base64')
                
                s = StringIO(data)
                img = Image.open(s)
                
                p = pic2rawdata(img)
                
                inverse = np.ones(p.shape, dtype=np.uint8)*255 - p
                if sum(sum(inverse.astype(np.uint32))) == 0:
                    # empty image
                    pass
                else:
                    # save image
                    p2 = Image.fromarray(p)
                    p2.save(outfn)
                
                t2 = time.time()
                print t2-t1, outfn

            
