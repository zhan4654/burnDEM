'''
This script burns stream into DEM

(1) Rasterizing the stream vector/shapefile is pre-required before running this code
(2) Make sure the rastarized stream is exactly the same spatial extends and resolution as the DEM raster

DEPENDENCIES: numpy, osgeo (gdal)
LIBRARIES REQUIRED: gdal, saga-gis 
'''

def burnstream(inputDEM, inputRiver, outputDEM): 
	'''
	Args:
		inputDEM: input raster file of original DEM, possibly with flat river channel issue
		inputRiver: input vector file of river center line, with RiveLine attribute = 1
		outputDEM: output rater file of DEM with stream DEM = -500 meters
		outputRiver: output river raster with exactly the same extend and pixel size with input DEM
	'''
	# import dependencies 
	import os
	import numpy
	from osgeo import gdal 

	gdal.AllRegister()

	# get file name and extention from orignal DEM and define output DEM file name
	(DEMRoot, DEMExt) = os.path.splitext(inputDEM)
	outFileName = DEMRoot + "_streamburn1" + DEMExt

	# read DEM raster
	DEM_ds = gdal.Open(inputDEM)
	DEM_band = DEM_ds.GetRasterBand(1)
	DEM_arr = DEM_band.ReadAsArray()
	[rows1,cols1] = DEM_arr.shape
	# get parameters from original DEM
	geotransform = DEM_ds.GetGeoTransform()
	spatialreference = DEM_ds.GetProjection()
	pixelsizeX = geotransform[1]
	pixelsizeY = -geotransform[5]
	minx = geotransform[0]
	miny = geotransform[3] + DEM_ds.RasterXSize*geotransform[4] + DEM_ds.RasterYSize*geotransform[5]
	maxx = geotransform[0] + DEM_ds.RasterXSize*geotransform[1] + DEM_ds.RasterYSize*geotransform[2]
	maxy = geotransform[3]
	
	# stats1 = DEM_band.GetStatistics(True, True)
	# print "***"
	# print "statistics of input DEM"
	# print "[ STATS ] =  Minimum=%.3f, Maximum=%.3f, Mean=%.3f, StdDev=%.3f" % (stats1[0], stats1[1], stats1[2], stats1[3])
	# get no data value
	DEM_nan = DEM_band.GetNoDataValue()
	# replace no data value into numpy nan
	DEM_arr[DEM_arr==DEM_nan]=numpy.nan

	(RiverRoot, RiverExt) = os.path.splitext(inputRiver)
	outputRiver = RiverRoot + ".tif"
	# read river raster 
	river_ds = gdal.Open(inputRiver)
	river_band = river_ds.GetRasterBand(1)
	river_arr = river_band.ReadAsArray()
	[rows,cols] = river_arr.shape
	

	# print out stats
	# stats = river_band.GetStatistics(True, True)
	# print "***"
	# print "statistics of input River"
	# print "[ STATS ] =  Minimum=%.3f, Maximum=%.3f, Mean=%.3f, StdDev=%.3f" % (stats[0], stats[1], stats[2], stats[3])
	# print ("River info loaded !")
	
	'''
	Step 1. rasterize river vector into raster with exact the same extend and pixel size as input DEM
	  dependency for this step: gdal-bin
	'''
	os.system('gdal_rasterize -a RiverLine -tr ' + str(pixelsizeX) + ' ' + str(pixelsizeY) + \
		' -te ' + str(minx) + ' ' + str(miny) + ' ' + str(maxx) + ' ' + str(maxy) + \
		' -l ' + RiverRoot + ' ' + inputRiver + ' ' + outputRiver)

	'''
	Step 2. calculate the euclidian distance within a buffer distance from all NoData cells to the nearest valid neighbour 
	  in a source grid. 
	  dependency for this step: saga-gis 
	  Usage: saga_cmd grid_tools 10 [-SOURCE <str>] [-DISTANCE <str>] [-ALLOC <str>] [-BUFFER <str>] [-DIST <str>] [-IVAL <num>]
  	  -SOURCE:<str>  	Source Grid
	    Grid (input)
	  -DISTANCE:<str>	Distance Grid
	    Grid (output)
	  -ALLOC:<str>   	Allocation Grid
		Grid (output)
	  -BUFFER:<str>  	Buffer Grid
		Grid (output)
	  -DIST:<str>    	Buffer distance
		Floating point
		Default: 500.000000
	  -IVAL:<num>    	Equidistance
		Integer
	    Default: 100
	''' 
	os.system('saga_cmd grid_tools 10 -SOURCE ' + outputRiver + ' -DISTANCE ' + RiverRoot + '_dist.tif'\
		+ ' -ALLOC ' + RiverRoot + '_alloc.tif' + ' -BUFFER ' + RiverRoot + '_buf.tif')

	'''
	Step 3. convert saga .sdat files into compressed tif file
	'''
	os.system('gdal_translate -of "GTIFF" -co "COMPRESS=LZW" ' + RiverRoot + '_buf.sdat ' +  RiverRoot + '_buf.tif')
	os.system('gdal_translate -of "GTIFF" -co "COMPRESS=LZW" ' + RiverRoot + '_dist.sdat ' +  RiverRoot + '_dist.tif')
	os.system('gdal_translate -of "GTIFF" -co "COMPRESS=LZW" ' + RiverRoot + '_alloc.sdat ' +  RiverRoot + '_alloc.tif') 

	exit()



	# get DEM raster data type
	dtype = gdal.GetDataTypeName(DEM_band.DataType)
	# get destination data type through a lookup dictionary
    datatypes = {'Byte':gdal.GDT_Byte,\
    			'Int16':gdal.GDT_Int16, \
    			'UInt16':gdal.GDT_UInt16,\
    			'UInt32':gdal.GDT_UInt32, \
    			'Int32':gdal.GDT_Int32,\
    			'Float32':gdal.GDT_Float32,\
    			'Float64':gdal.GDT_Float64}

	'''
	NP2GDAL_CONVERSION = {
	  "uint8": 1,
	  "int8": 1,
	  "uint16": 2,
	  "int16": 3,
	  "uint32": 4,
	  "int32": 5,
	  "float32": 6,
	  "float64": 7,
	  "complex64": 10,
	  "complex128": 11,
	}

	'''
	DEM_type = datatypes[dtype]
	print("DEM info loaded !")

	DEM_arr_out = numpy.where((river_arr > 0), -500, DEM_arr)
	DEM_arr_out[numpy.isnan(DEM_arr_out)] = DEM_nan
	print("stream burned in !")

	driver = gdal.GetDriverByName("GTiff")
	outdata = driver.Create(outFileName, cols, rows, 1, DEM_dtype, options = ['BigTIFF=YES']) 
	outdata.GetRasterBand(1).WriteArray(DEM_arr_out)
	# map the geo information to the output data
	outdata.SetGeoTransform(geotransform)
	outdata.SetProjection(spatialreference)
	#########
	outdata.GetRasterBand(1).SetNoDataValue(DEM_nan)
	outdata = None
	print("new DEM with stream burned in finished !")


'''
inputRiver = "/Users/yuzhang/Google Drive/FloodConcern/DEM_issues/Iowa_test/NHDriverRaster.tif"
inputDEM = "/Users/yuzhang/Google Drive/FloodConcern/DEM_issues/Iowa_test/IA_merged_UTM15-002.tif"

## additional 
## check the output of DEM with stream burnin
new = "/Users/yuzhang/Google Drive/FloodConcern/DEM_issues/Iowa_test/IA_merged_UTM15-002_streamburn.tif"
new_ds = gdal.Open(new)
new_band = new_ds.GetRasterBand(1)
new_arr = new_band.ReadAsArray()
[rows, cols] = new_arr.shape
stats2 = new_band.GetStatistics(True, True)
print "[ STATS ] =  Minimum=%.3f, Maximum=%.3f, Mean=%.3f, StdDev=%.3f" % (stats2[0], stats2[1], stats2[2], stats2[3])
'''
