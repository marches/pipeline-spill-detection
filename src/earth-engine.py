def getSentinalS2_S1Image(lon, lat, sze, filename, dateMin = '2020-04-01', dateMax = '2020-04-30', vmin = 0, vmax = 3500, satellites = ['S2','S1'], 
                          bands=['B2','B3','B4','B5','B6','B7','B8','B8A','B9','B11','B12'], scale=10):
    '''    
    download image from the Sentinal S2 and S1 satellites, at the given coordinates
    
    lon : central longitude in degrees
    lat : central latitude in degrees
    sze : size of the edge of the box in degrees
    dateMin : minimum date to use for image search in year-month-day (e.g., 2020-08-01)
    dateMax : maximum date to use for image search in year-month-day (e.g., 2020-08-31)
    vMin : minimum value to select in the Sentinal image pixels (I think this should be close to 0)
    vMax : maximum value to select in the Sentinal image pixels (I think this should be close to 3000)
    filename : output filename for the GeoTIFF image
    
    Note: it's possible that the vMin and vMax values should be different for each band to make the image look nicer
    
    https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR
    https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD
    '''


    print('Sentinel-2 MSI: MultiSpectral Instrument, Level-2A... ')
    
    # define the area of interest, using the Earth Engines geometry object
    coords = [
         [lon - sze/2., lat - sze/2.],
         [lon + sze/2., lat - sze/2.],
         [lon + sze/2., lat + sze/2.],
         [lon - sze/2., lat + sze/2.],
         [lon - sze/2., lat - sze/2.]
    ]
    print(f"Coordinates: ", coords)
    aoi = ee.Geometry.Polygon(coords)
    if 'S2' in satellites:
      # get the image using Google's Earth Engine
      db = ee.Image(ee.ImageCollection('COPERNICUS/S2_SR')\
                        .filterBounds(aoi)\
                        .filterDate(ee.Date(dateMin), ee.Date(dateMax))\
                        .sort('CLOUDY_PIXEL_PERCENTAGE')\
                        .first())
      
      # add the latitude and longitude
      db = db.addBands(ee.Image.pixelLonLat())

      # define the S2 bands to download.
      '''
      B1 - 60m pixel size - mentioned in paper, but not used in modeling... 

      B2 - 10m pixel size
      B3 - 10m pixel size
      B4 - 10m pixel size
      B8 - 10m pixel size

      B5 - 20m pixel size (red edge 1)
      B6 - 20m pixel size (red edge 2)
      B7 - 20m pixel size (red edge 3)
      B8A - 20m pixel size (red edge 4)
      B11 - 20m pixel size (SWIR1)
      B12 - 20m pixel size (SWIR2)

      '''
      bands = bands

      # export geotiff images, these go to Drive and then are downloaded locally
      for selection in bands:
          task = ee.batch.Export.image.toDrive(image=db.select(selection),
                                      description=selection,
                                      scale=scale,
                                      region=aoi,
                                      fileNamePrefix=selection,
                                      crs='EPSG:4326',
                                      fileFormat='GeoTIFF')
          task.start()

          url = db.select(selection).getDownloadURL({
              'scale': scale, # ADJUST THIS TO ACTUAL BAND MINIMUM 
              'crs': 'EPSG:4326',
              'fileFormat': 'GeoTIFF',
              'region': aoi})
      
          r = requests.get(url, stream=True)

          filenameZip = selection+'.zip'
          filenameTif = selection+'.tif'

          # unzip and write the tif file, then remove the original zip file
          with open(filenameZip, "wb") as fd:
              for chunk in r.iter_content(chunk_size=1024):
                  fd.write(chunk)

          zipdata = zipfile.ZipFile(filenameZip)
          zipinfos = zipdata.infolist()

          # iterate through each file (there should be only one)
          for zipinfo in zipinfos:
              zipinfo.filename = filenameTif
              zipdata.extract(zipinfo)
      
          zipdata.close()
          
      # create a combined RGB geotiff image, https://gis.stackexchange.com/questions/341809/merging-sentinel-2-rgb-bands-with-rasterio
      print('Creating 3-band GeoTIFF image ... ')
      
      # Define which bands are to be displayed.
      B2 = rasterio.open('B2.tif')
      B3 = rasterio.open('B3.tif')
      B4 = rasterio.open('B4.tif')
      x, y = B4.read(1).shape # this is for final np.array.

      # get the scaling
      image = np.array([B2.read(1), B3.read(1), B4.read(1)]).transpose(1,2,0)
      p2, p98 = np.percentile(image, (2,98))

      # use the B2 image as a starting point so that I keep the same parameters
      B2_geo = B2.profile
      B2_geo.update({'count': 3})

      with rasterio.open(filename, 'w', **B2_geo) as dest:
          dest.write( (np.clip(B4.read(1), p2, p98) - p2)/(p98 - p2)*255, 1)
          dest.write( (np.clip(B3.read(1), p2, p98) - p2)/(p98 - p2)*255, 2)
          dest.write( (np.clip(B2.read(1), p2, p98) - p2)/(p98 - p2)*255, 3)

      B2.close()
      B3.close()
      B4.close()
      
      # update here to output np.array, https://rasterio.readthedocs.io/en/latest/topics/reading.html
      img_spectra = np.zeros((x,y))
      for band in bands:
        img = rasterio.open(band +'.tif')
        img_spectra = np.dstack((img_spectra,np.array(img.read(1))))

      # remove the intermediate files
      for selection in bands:
          os.remove(selection + '.tif')
          os.remove(selection + '.zip')


    if 'S1' in satellites:
      print('Downloading Sentinel-1 SAR GRD: C-band Synthetic Aperture Radar Ground Range Detected, log scaling... ')
      # get the image using Google's Earth Engine
      db = ee.Image(ee.ImageCollection('COPERNICUS/S1_GRD')\
                        .filterBounds(aoi)\
                        .filterDate(ee.Date(dateMin), ee.Date(dateMax))\
                        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))\
                        .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                        .first())
      
      # add the latitude and longitude
      db = db.addBands(ee.Image.pixelLonLat())

      # See paper, only need these two bands.
      # https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD#bands
      bands_S1 = ['VV','VH']

      # export geotiff images, these go to Drive and then are downloaded locally
      for selection in bands_S1:
          task = ee.batch.Export.image.toDrive(image=db.select(selection),
                                      description=selection,
                                      scale=scale,
                                      region=aoi,
                                      fileNamePrefix=selection,
                                      crs='EPSG:4326',
                                      fileFormat='GeoTIFF')
          task.start()

          url = db.select(selection).getDownloadURL({
              'scale': scale, #ADJUST THIS TO ACTUAL BAND MINIMUM
              'crs': 'EPSG:4326',
              'fileFormat': 'GeoTIFF',
              'region': aoi})
      
          r = requests.get(url, stream=True)

          filenameZip = selection+'.zip'
          filenameTif = selection+'.tif'

          # unzip and write the tif file, then remove the original zip file
          with open(filenameZip, "wb") as fd:
              for chunk in r.iter_content(chunk_size=1024):
                  fd.write(chunk)

          zipdata = zipfile.ZipFile(filenameZip)
          zipinfos = zipdata.infolist()

          # iterate through each file (there should be only one)
          for zipinfo in zipinfos:
              zipinfo.filename = filenameTif
              zipdata.extract(zipinfo)
      
          zipdata.close()

      # Open relevant images.
      VV = rasterio.open('VV.tif')
      VH = rasterio.open('VH.tif')
      x,y = VH.read(1).shape # this is for final np.array.
      
      # create relevant numpy array.
      for band in bands_S1:
        img = rasterio.open(band +'.tif')
        img_spectra = np.dstack((img_spectra,np.array(img.read(1))))
        bands.append(band)

      # remove the intermediate files
      for selection in bands_S1:
          os.remove(selection + '.tif')
          os.remove(selection + '.zip')
      

    return bands, img_spectra[:,:,1:] # remove the first dimension of zeros.