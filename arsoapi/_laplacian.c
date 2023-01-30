#include "Python.h"
#include "stdlib.h"
#include "stdio.h"
#include <time.h>

#define RAND() ((float)rand())/RAND_MAX
#define not_inside(au, x, y) (x<0 || x>=au->W || y<0 || y>=au->H)
typedef unsigned char bool;
#define true 1
#define false 0
// #define DEBUG


#ifdef DEBUG
#define dfree(x) fprintf(stderr, "%s:%d free called\n", __FILE__, __LINE__); fflush(stderr); free(x)
#define dprint(x, ...) fprintf(stderr, "%s:%d " x "\n", __FILE__, __LINE__, ##__VA_ARGS__); fflush(stderr)

#else
#define dfree(x) free(x)
#define dprint(...)

#endif

/********************************
 Stolen from GIMP
********************************/

#define MIN(a,b) (((a)<(b))?(a):(b))
#define MAX(a,b) (((a)>(b))?(a):(b))


static void
laplace_prepare_row (unsigned char *pixel_rgn,
                 unsigned char       *data,
                 int          x,
                 int          y,
                 int          w,
		 int height)
{
  int bpp = 3;
  int b;

  if (y < 0)
    {
      //data = pixel_rgn + x + (y + 1)*w;
      memcpy(data, pixel_rgn + (y+1)*w*bpp, w*bpp);
    }
  else if (y == height)
    {
      // data = pixel_rgn + x + (y-1)*w;
      memcpy(data, pixel_rgn + (y-1)*w*bpp, w*bpp);
    }
  else
    {
      //data = pixel_rgn + x + y*w;
      memcpy(data, pixel_rgn + y*w*bpp, w*bpp);
    }

  /*  Fill in edge pixels  */
  for (b = 0; b < bpp; b++)
    {
      data[b - bpp] = data[b];
      data[w * bpp + b] = data[(w - 1) * bpp + b];
    }
}

#define BLACK_REGION(val) ((val) > 128)
#define WHITE_REGION(val) ((val) <= 128)

static void
minmax  (int  x1,
       int  x2,
       int  x3,
       int  x4,
       int  x5,
       int *min_result,
       int *max_result)
{
  int min1, min2, max1, max2;

  if (x1 > x2)
    {
      max1 = x1;
      min1 = x2;
    }
  else
    {
      max1 = x2;
      min1 = x1;
    }

  if (x3 > x4)
    {
      max2 = x3;
      min2 = x4;
    }
  else
    {
      max2 = x4;
      min2 = x3;
    }

  if (min1 < min2)
    *min_result = MIN (min1, x5);
  else
    *min_result = MIN (min2, x5);

  if (max1 > max2)
    *max_result = MAX (max1, x5);
  else
    *max_result = MAX (max2, x5);
}

static void
laplace (int width, int height, unsigned char *srcPR, unsigned char *destPR)
{
  int         bytes;
  int         current;
  int         gradient;
  unsigned char      *dest, *d;
  unsigned char      *prev_row, *pr;
  unsigned char      *cur_row, *cr;
  unsigned char      *next_row, *nr;
  unsigned char      *tmp;
  int         row, col;
  int         minval, maxval;

  /* image area */

  /* Get the size of the input image. (This will/must be the same
   *  as the size of the output image.
   */
  bytes  = 3;

  /*  allocate row buffers  */
  prev_row = malloc((width + 2) * bytes);
  cur_row  = malloc((width + 2) * bytes);
  next_row = malloc((width + 2) * bytes);
  dest     = malloc(width * bytes);

  pr = prev_row + bytes;
  cr = cur_row + bytes;
  nr = next_row + bytes;

  laplace_prepare_row(srcPR, pr, 0, -1, width, height);
  laplace_prepare_row(srcPR, cr, 0, 0, width, height);

  /*  loop through the rows, applying the laplace convolution  */
  for (row = 0; row < height; row++)
    {
      /*  prepare the next row  */
      laplace_prepare_row (srcPR, nr, 0, row + 1, width, height);
      // dprint("nr %d %d %d", nr[0], nr[1], nr[2]);

      d = dest;

      for (col = 0; col < width * bytes; col++)
        {
          minmax (pr[col], cr[col - bytes], cr[col], cr[col + bytes],
                nr[col], &minval, &maxval); /* four-neighbourhood */

          gradient = (0.5 * MAX ((maxval - cr [col]), (cr[col]- minval)));

          *d++ = (((  pr[col - bytes] + pr[col]       + pr[col + bytes] +
                      cr[col - bytes] - (8 * cr[col]) + cr[col + bytes] +
                      nr[col - bytes] + nr[col]       + nr[col + bytes]) > 0) ?
                    gradient : (128 + gradient));

      /*  store the dest  */
        }
      memcpy(destPR + width*bytes*row, dest, width*bytes);

      /*  shuffle the row pointers  */
      tmp = pr;
      pr = cr;
      cr = nr;
      nr = tmp;
    }


  /* now clean up: leave only edges, but keep gradient value */

  memcpy(srcPR, destPR, width*height*bytes);

  pr = prev_row + bytes;
  cr = cur_row + bytes;
  nr = next_row + bytes;

  laplace_prepare_row (srcPR, pr, 0, -1, width, height);
  laplace_prepare_row (srcPR, cr, 0, 0, width, height);

  /*  loop through the rows, applying the laplace convolution  */
  for (row = 0; row < height; row++)
    {
      /*  prepare the next row  */
      laplace_prepare_row (srcPR, nr, 0, row + 1, width, height);

      d = dest;
      for (col = 0; col < width * bytes; col++)
        {
          current = cr[col];
          current = ((WHITE_REGION (current) &&
                      (BLACK_REGION (pr[col - bytes]) ||
                       BLACK_REGION (pr[col])         ||
                       BLACK_REGION (pr[col + bytes]) ||
                       BLACK_REGION (cr[col - bytes]) ||
                       BLACK_REGION (cr[col + bytes]) ||
                       BLACK_REGION (nr[col - bytes]) ||
                       BLACK_REGION (nr[col])         ||
                       BLACK_REGION (nr[col + bytes]))) ?
                     ((current >= 128) ? (current - 128) : current) : 0);

          *d++ = current;
          if (col % bytes == 2) {
            if (*(d-1) < 15 && *(d-2) < 15 && *(d-3) < 15) {
              *(d-1) = 255;
              *(d-2) = 255;
              *(d-3) = 255;
            }
          }
        }

      /*  store the dest  */
      memcpy(destPR + width*bytes*row, dest, width*bytes);

      /*  shuffle the row pointers  */
      tmp = pr;
      pr = cr;
      cr = nr;
      nr = tmp;

    }

  /*  update the laplaced region  */

  free (prev_row);
  free (cur_row);
  free (next_row);
  free (dest);
}



/************************************
 End gimp code 
 *************************************/

PyObject * ppm_laplacian(PyObject *self, PyObject * args)
{
	int width, height;
	char *buffer;
	unsigned char *data;
	unsigned char *srcPR, *destPR;
	Py_ssize_t datasize;
	PyObject *py_data, *result;
	
	dprint("Starting");
	if (!PyArg_ParseTuple(args, "(ii)S", &width, &height, &py_data))
		return NULL;
	dprint("Parsing data");
	PyBytes_AsStringAndSize(py_data, &buffer, &datasize);
	data = (unsigned char *)(buffer);
	
	dprint("width=%d", width);
	dprint("height=%d", height);
	dprint("datasize=%d", datasize);
	if (width*height*3 != datasize) {
		PyErr_SetString(PyExc_ValueError, "data size does not match 24bit");
		return NULL;
	}
	
	destPR = malloc(datasize);
	srcPR = malloc(datasize);
	memcpy(srcPR, data, datasize);

	dprint("calling laplace");
	laplace(width, height, srcPR, destPR);

	dprint("building result");
	result = Py_BuildValue("y#", destPR, datasize);

	dprint("returning laplace result");
	return result;
}

void init_data(int x, int y, unsigned char * data)
{
	int datasize, i;
	
	datasize = 3*x*y;
	data = malloc(datasize);
	if (!data)
		return;
	
	for (i=0; i<datasize; i++)
		data[i] = '\0';
}


/******************* 
 * functions 
 *******************/
static PyMethodDef laplacian_methods[] = {
	{"ppm_laplacian", (PyCFunction)ppm_laplacian, METH_VARARGS,
	 "Calculate second degree laplacian edge detection on ppm."  },
	{ NULL, NULL}
};


static struct PyModuleDef laplacian_module = {
    PyModuleDef_HEAD_INIT,
    "laplacian",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    laplacian_methods
};


PyMODINIT_FUNC PyInit__laplacian(void)
{
	// Py_InitModule3("_laplacian", _functions, "Second degree Laplacian edge detection accelerator module.");
    return PyModule_Create(&laplacian_module);
}
