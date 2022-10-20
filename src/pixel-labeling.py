'''
Methods for pixel labeling for model validation
'''

def scale_for_png(sentinel_arr):
    '''
    Create png that can be downloaded for labling
    '''
    red = sentinel_arr[:,:,2]/np.amax(sentinel_arr[:,:,2])*255
    green = sentinel_arr[:,:,1]/np.amax(sentinel_arr[:,:,1])*255
    blue = sentinel_arr[:,:,0]/np.amax(sentinel_arr[:,:,0])*255

    im = np.dstack([red, green, blue])

    im = Image.fromarray(im.astype(np.uint8))

    return im

def base64_2_mask(s):
    '''
    Convert mask from supervise.ly labeling to pixel-wise bitmask
    '''
    z = zlib.decompress(base64.b64decode(s))
    n = np.fromstring(z, np.uint8)
    mask = cv2.imdecode(n, cv2.IMREAD_UNCHANGED)[:, :, 3].astype(bool)
    
    return mask

def create_bitmask(img, pixels, origin):
    '''
    Add bitmask to ground truth dimensions to create full ground truth labeled bitmask
    '''
    mask = np.full((img.shape[0], img.shape[1]), False)
    x0 = origin[0]
    x1 = origin[0] + pixels.shape[0]

    y0 = origin[1]
    y1 = origin[1] + pixels.shape[1]

    mask[x0:x1, y0:y1] = pixels
   
    return mask