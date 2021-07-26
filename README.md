# Measuring Urban Quality and Change Through the Detection of Physical Attributes of Decay


**We develop an index of urban quality and urban change based on Google Street 
View images of cities over time.** We train a
 [YOLOv5](https://github.com/ultralytics/yolov5) model to detect features of
urban decay including graffiti, garbage, facade discoloration and damage, 
weeds, broken and covered windows, and potholes. We create vector representations
and indices at the street segment level by aggregating the incidence of each
object class and visualize these over time to identify dynamics of urban
change such as gentrification and neighborhood decay.

## Structure
The repo is organized into the following directories. 

### ObjectDetection
Pipeline to prepare the object detection dataset to be fed to the YOLOv5 model.
1. `01_merge_OD_datasets.py`
2. `02_generate_street_test_set.py`
3. `03_MissionDistrict_TestSet.py`

### SFStreetView
Pipeline to generate the street segments for a selected location, visualize
its available Google Street View imagery in time and collect the images for 
each street segment.
1. `01_generate_street_segments.py`
2. `02_collect_street_segment_images.py`
3. `03_explore_GSV_time_availability.py`
4. `04_explore_GSV_steps.py`
5. `05_visualize_GSV_period_availability.py`

### Postprocessing
Pipeline to run inference using the YOLOv5 model and generate the representation
vectors and urban quality indices for each street segment in a location. 
1. `01_detect_segments.py`
2. `02_create_representation_vectors.py`
3. `03_create_segment_indices.py`
4. `04_indices_in_time.py`
5. `05_visualize_urban_quality.py`
