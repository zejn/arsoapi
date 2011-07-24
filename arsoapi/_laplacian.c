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
  unsigned char *storelocation;
  int         row, col;
  int         minval, maxval;
  int i;

  dprint("laplace starting");
  /* image area */

  /* Get the size of the input image. (This will/must be the same
   *  as the size of the output image.
   */
  bytes  = 3;

  /*  allocate row buffers  */
  dprint("mallocing");
  prev_row = malloc((width + 2) * bytes);
  cur_row  = malloc((width + 2) * bytes);
  next_row = malloc((width + 2) * bytes);
  dest     = malloc(width * bytes);

  pr = prev_row + bytes;
  cr = cur_row + bytes;
  nr = next_row + bytes;

  dprint("preparing rows");
  laplace_prepare_row(srcPR, pr, 0, -1, width, height);
  laplace_prepare_row(srcPR, cr, 0, 0, width, height);

  dprint("height=%d", height);
  dprint("width=%d", width);

  for (i=0;i<width*height*3;i=i+3)
    dprint("(%d, %d) = (%d, %d, %d)", i/bytes/width, i/bytes%width, srcPR[i], srcPR[i+1], srcPR[i+2]);


  /*  loop through the rows, applying the laplace convolution  */
  for (row = 0; row < height; row++)
    {
      /*  prepare the next row  */
      laplace_prepare_row (srcPR, nr, 0, row + 1, width, height);
      // dprint("nr %d %d %d", nr[0], nr[1], nr[2]);
      if (col == 0 && row == 0) {
	for (i=0;i<width*3;i=i+3)
	  dprint("(%d, %d) = (%d, %d, %d)", i/3/width, i/3%width, nr[i], nr[i+1], nr[i+2]);
	
      }

      d = dest;

      for (col = 0; col < width * bytes; col++)
        {
          minmax (pr[col], cr[col - bytes], cr[col], cr[col + bytes],
                nr[col], &minval, &maxval); /* four-neighbourhood */
	  if (col == 0 && row == 0) {
	    dprint("00 %d %d %d %d %d", pr[col], cr[col - bytes], cr[col], cr[col + bytes], nr[col]);
	    dprint("00 min %d max %d", minval, maxval);
	  }

          gradient = (0.5 * MAX ((maxval - cr [col]), (cr[col]- minval)));
	  if (col == 0 && row == 0)
	    dprint("grad %d", gradient);

          *d++ = (((  pr[col - bytes] + pr[col]       + pr[col + bytes] +
                      cr[col - bytes] - (8 * cr[col]) + cr[col + bytes] +
                      nr[col - bytes] + nr[col]       + nr[col + bytes]) > 0) ?
                    gradient : (128 + gradient));

      /*  store the dest  */
      if (col == 0 && row == 0) {
	dprint("FML %d %d %d", dest[0], dest[1], dest[2]);
      }
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
  dprint("middle");
  for (i=0;i<width*height*3;i=i+3)
    dprint("(%d, %d) = (%d, %d, %d)", i/3/width, i/3%width, srcPR[i], srcPR[i+1], srcPR[i+2]);

  pr = prev_row + bytes;
  cr = cur_row + bytes;
  nr = next_row + bytes;

  dprint("preparing rows 2");
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
          //dprint("cur %d %d %d", row, col / bytes, current);

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
  // gimp_drawable_flush (drawable);
  // gimp_drawable_merge_shadow (drawable->drawable_id, TRUE);

  free (prev_row);
  free (cur_row);
  free (next_row);
  free (dest);
  //dprint("End");
  //for (i=0;i<width*height*3;i=i+3)
  //  dprint("(%d, %d) = (%d, %d, %d)", i/3/width, i/3%width, destPR[i], destPR[i+1], destPR[i+2]);
}



/************************************
 End gimp code 
 *************************************/

PyObject * ppm_laplacian(PyObject *self, PyObject * args)
{
	int width, height;
	unsigned char * data;
	unsigned char *srcPR, *destPR;
	Py_ssize_t datasize;
	PyObject *py_data, *result;
	
	dprint("Starting");
	//if (!PyArg_ParseTuple(args, "(ii)S", &width, &height, &py_data))
	if (!PyArg_ParseTuple(args, "(ii)S", &width, &height, &py_data))
		return NULL;
	dprint("Parsing data");
	PyString_AsStringAndSize(py_data, &data, &datasize);
	
	dprint("width=%d", width);
	dprint("height=%d", height);
	dprint("datasize=%d", datasize);
	if (width*height*3 != datasize) {
		PyErr_SetString(PyExc_ValueError, "data size does not match 24bit");
		return -1;
	}
	
	destPR = malloc(datasize);
	srcPR = malloc(datasize);
	//dprint("first three: %d %d %d", data[0], data[1], data[2]);
	memcpy(srcPR, data, datasize);
	//dprint("first three: %d %d %d", srcPR[0], srcPR[1], srcPR[2]);
	
	laplace(width, height, srcPR, destPR);
	
	//free(srcPR);
	
	result = Py_BuildValue("s#", destPR, datasize);
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
static PyMethodDef _functions[] = {
	{"ppm_laplacian", (PyCFunction)ppm_laplacian, METH_VARARGS,
	 "Calculate second degree laplacian edge detection on ppm."  },
	{ NULL, NULL}
};


/* module init */

#ifndef PyMODINIT_FUNC
#ifdef WIN32
#define PyMODINIT_FUNC void __declspec(dllexport)
#else
#define PyMODINIT_FUNC
#endif
#endif

PyMODINIT_FUNC init_laplacian(void)
{
	PyObject * m;
	m = Py_InitModule3("_laplacian", _functions, "Second degree Laplacian edge detection accelerator module.");

}
