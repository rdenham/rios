
"""
This module contains the ReaderInfo class
which holds information about the area being
read and info on the current block

"""

import math
from . import imageio
from . import rat

class StatisticsCache(object):
    """
    Allows global statistics for all the files used to be cached
    Statistics are stored here associated with the filename
    so if there are multiple calls to global_stats for one
    file the statistics will only get calculated once. 
    """
    def __init__(self):
        self.stats = {}

    def getStats(self,fname,band,ignore):
        """
        Returns tuple with (min,max,mean,stddev) if 
        previously cached, None otherwise.
        """
        if ignore is None:
            key = '%s %d' % (fname,band)
        else:
            key = '%s %d %f' % (fname,band,ignore)
        if key in self.stats:
            return self.stats[key]
        else:
            return None

    def setStats(self,fname,band,ignore,stats):
        """
        Sets tuple with (min,max,mean,stddev) in cache
        """
        if ignore is None:
            key = '%s %d' % (fname,band)
        else:
            key = '%s %d %f' % (fname,band,ignore)
        self.stats[key] = stats

class AttributeTableCache(object):
    """
    Allows attribute columns to be cached. This means
    that an attribute column can be requested for each
    block through the image, but the actual column data
    will only be read the first time and cached for 
    subsequent calls.
    """
    def __init__(self):
        self.rats = {}

    def getColumn(self, fname, band, colName):
        """
        Returns the column if previously cached, otherwise
        None.
        """
        key = '%s %d %s' % (fname, band, colName)
        if key in self.rats:
            return self.rats[key]
        else:
            return None

    def setColumn(self, fname, band, colName, column):
        """
        Puts the column into the cache
        """
        key = '%s %d %s' % (fname, band, colName)
        self.rats[key] = column


class ReaderInfo(object):
    """
    ReaderInfo class. Holds information about the area being
    read and info on the current block
    
    """
    def __init__(self, workingGrid, statscache, ratcache, 
                    windowxsize, windowysize,
                    overlap, loggingstream):
                    
        self.loggingstream = loggingstream
        # grab the working grid
        self.workingGrid = workingGrid
        
        # save the window size and overlap
        self.windowxsize = windowxsize
        self.windowysize = windowysize
        self.overlap = overlap
        
        # work out the area being read
        self.xsize = int(round((self.workingGrid.xMax - 
                        self.workingGrid.xMin) / self.workingGrid.xRes))
        self.ysize = int(round((self.workingGrid.yMax - 
                        self.workingGrid.yMin) / self.workingGrid.yRes))
        
        # total number of blocks
        self.xtotalblocks = int(math.ceil(float(self.xsize) / self.windowxsize))
        self.ytotalblocks = int(math.ceil(float(self.ysize) / self.windowysize))
        
        # save the statistics cache. 
        self.statscache = statscache

        # save the RAT cache
        self.ratcache = ratcache
        
        # The feilds below apply to a particular block
        # and are filled in after this object is copied 
        # to make it specific fir each block
        self.blockwidth = None
        self.blockheight = None
        
        self.blocktl = None
        self.blockbr = None
        
        self.xblock = None
        self.yblock = None
        
        # dictionary keyed by id() of the number array
        # value is a tuple with the GDAL dataset object 
        # that corresponds to it, and the original filename
        self.blocklookup = {}
        
    def setBlockDataset(self,block,dataset,filename):
        """
        Saves a match between the numpy block read
        and it's GDAL dataset. So we can look up the
        dataset later given a block.
        """
        self.blocklookup[id(block)] = (dataset,filename)
        
    def getWindowSize(self):
        """
        Returns the size of the current window
        """
        return (self.windowxsize, self.windowysize)
        
    def getOverlapSize(self):
        """
        Returns the size of the pixel overlap between
        each window
        """
        return self.overlap
        
    def getTotalSize(self):
        """
        Returns the total size (in pixels) of the dataset
        being processed
        """
        return (self.xsize,self.ysize)
        
    def getTransform(self):
        """
        Return the current transform between world
        and pixel coords
        """
        return self.workingGrid.makeGeoTransform()
        
    def getProjection(self):
        """
        Return the WKT describing the current
        projection system
        """
        return self.workingGrid.projection

    def getTotalBlocks(self):
        """
        Returns the total number of blocks the dataset
        has been split up into for processing
        """
        return (self.xtotalblocks,self.ytotalblocks)

    def setBlockSize(self,blockwidth,blockheight):
        """
        Sets the size of the current block
        """
        self.blockwidth = blockwidth
        self.blockheight = blockheight

    def getBlockSize(self):
        """
        Get the size of the current block
        """
        return (self.blockwidth,self.blockheight)

    def setBlockBounds(self,blocktl,blockbr):
        """
        Sets the coordinate boulds of the current block
        """
        self.blocktl = blocktl
        self.blockbr = blockbr

    def getBlockBounds(self):
        """
        Gets the coordinate bounds of the current block
        """
        return (self.blocktl,self.blockbr)
        
    def setBlockCount(self,xblock,yblock):
        """
        Sets the count of the current block
        """
        self.xblock = xblock
        self.yblock = yblock

    def getBlockCount(self):
        """
        Gets the count of the current block
        """
        return (self.xblock,self.yblock)
    
    def getPixelSize(self):
        """
        Gets the current pixel size and returns it as a tuple (x and y)
        """
        return (self.workingGrid.xRes,self.workingGrid.yRes)
    
    def getPixColRow(self,x,y):
        """
        Get the image Row and Column for the nominated block x and y
        """
        col = self.xblock * self.windowxsize + x
        row = self.yblock * self.windowysize + y
        return (col,row)
    
    def getPixCoord(self,x,y):
        """
        Get the image coordinate for the nominated block x and y
        """
        (col,row) = self.getPixColRow(x,y)
        coord = imageio.pix2wld(self.workingGrid.makeGeoTransform(),col,row)
        return (coord.x,coord.y)

    def isFirstBlock(self):
        """
        Returns True if this is the first block to be processed
        """
        return self.xblock == 0 and self.yblock == 0

    def isLastBlock(self):
        """
        Returns True if this is the last block to be processed
        """
        xtotalblocksminus1 = self.xtotalblocks - 1
        ytotalblocksminus1 = self.ytotalblocks - 1
        return self.xblock == xtotalblocksminus1 and self.yblock == ytotalblocksminus1

    def getFilenameFor(self,block):
        """
        Get the input filename of a dataset
        """
        # can't use ds.GetDescription() as may have been resampled
        (ds,fname) = self.blocklookup[id(block)]
        return fname


    def getGDALDatasetFor(self,block):
        """
        Get the underlying GDAL handle of a dataset
        """
        (ds,fname) = self.blocklookup[id(block)]
        return ds

    def getGDALBandFor(self,block,band):
        """
        Get the underlying GDAL handle for a band of a dataset
        """
        ds = self.getGDALDatasetFor(block)
        return ds.GetRasterBand(band)

    def getNoDataValueFor(self,block,band=1):
        """
        Returns the 'no data' value for the dataset
        underlying the block. This should be the
        same as what was set for the stats ignore value
        when that dataset was created. 
        Note: actually returns the no data value for
        the first band by default. The assumption is that the dataset
        was created using PyModeller hence the same for all bands.
        """
        ds = self.getGDALDatasetFor(block)
        band = ds.GetRasterBand(band)
        return band.GetNoDataValue()
        
    def getPercent(self):
        """
        Returns the percent complete. 
        """
        percent = int(float(self.yblock * self.xtotalblocks + self.xblock) / 
                    float(self.xtotalblocks * self.ytotalblocks) * 100)
        return percent

    def getAttributeColumn(self, block, colName, band=1):
        """
        Gets the attribute for the given block and column name
        Caches columns so only first call actually extracts data
        """
        (ds,fname) = self.blocklookup[id(block)]

        column = self.ratcache.getColumn(fname, band, colName)
        if column is None:
            column = rat.readColumn(ds, colName, band)
            self.ratcache.setColumn(fname, band, colName, column)
        
        return column
        
    def global_stats(self,block,band=1,ignore=None):
        """
        Returns the (min,max,mean,stddev) for the whole band
        """
        fname = self.getFilenameFor(block)
        
        # see if we have the stats in our cache
        values = self.statscache.getStats(fname,band,ignore)
        
        if values is None:
            # no, get the gdal band
            bandhandle = self.getGDALBandFor(block,band)
            
            # set ignore value if specified so that 
            # GDAL ignores it when calculating stats
            if ignore is not None:
                bandhandle.SetNoDataValue(ignore)
                
            self.loggingstream.write("Calculating global statistics...\n")
                
            # get GDAL to calc the stats
            values = bandhandle.GetStatistics(False,True)
            
            # set it back in our cache for next time
            self.statscache.setStats(fname,band,ignore,values)
            
        return values

    def global_min(self,block,band=1,ignore=None):
        """
        Returns the min for the whole band
        """
        return self.global_stats(block,band,ignore)[0]

    def global_max(self,block,band=1,ignore=None):
        """
        Returns the max for the whole band
        """
        return self.global_stats(block,band,ignore)[1]

    def global_mean(self,block,band=1,ignore=None):
        """
        Returns the mean for the whole band
        """
        return self.global_stats(block,band,ignore)[2]

    def global_stddev(self,block,band=1,ignore=None):
        """
        Returns the stddev for the whole band
        """
        return self.global_stats(block,band,ignore)[3]
