
all:
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.6 -c _laplacian.c -o _laplacian.o
	gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions _laplacian.o -o _laplacian.so
	python testlaplacian.py
