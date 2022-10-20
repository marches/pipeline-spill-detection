'''
Calculations of spectral indices from https://www.researchgate.net/publication/353755860_Terrestrial_oil_spill_mapping_using_satellite_earth_observation_and_machine_learning_A_case_study_in_South_Sudan

'''



def ndvi(arr):
  return (arr[:,:,6]-arr[:,:,2])/(arr[:,:,6]+arr[:,:,2])


def ndwi(arr):
  return (arr[:,:,1]-arr[:,:,6])/(arr[:,:,1]+arr[:,:,6])

def rendvi(arr):
  return (arr[:,:,6]-arr[:,:,3])/(arr[:,:,6]+arr[:,:,3])

def gndvi(arr):
  return (arr[:,:,6]-arr[:,:,1])/(arr[:,:,6]+arr[:,:,1])