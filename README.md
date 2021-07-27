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
1. `01_detect_segments.py` Runs inference using custom YOLOv5 weights and 
extracts the detected objects in each image for each street segment.
2. `02_create_representation_vectors.py` Generates representation vectors using
four types of aggregations: counts, confidence-weighted counts, bounding box image
coverage-weighted counts, confidence and bounding box image coverage-weighted 
counts. Street segments with missing imagery can be dropped or have their length
adjusted prior to vector normalization. Vectors are also generating by selecting
a minimum confidence level for detections.
3. `03_create_segment_indices.py` Indices for vectors from a specific
aggregation type, missing imagery handling and confidence level combination are
generated via sums, weighted sums and extracting each element of the vector (class-
wise indices). The log versions of each index are also generated.
4. `04_indices_in_time.py` Computes relative and absolute changes of indices 
from the same location.
5. `05_visualize_urban_quality.py`
