from DataScripts.object_classes import CLASSES_TO_LABEL


# Aggregation Parameters
# Length rate (meters): Utilized when normalizing the vectors for the segment
# length. It specifies the rate to use for counting objects.
# E.g. a value of 100 indicates we are reporting objects counted per 100 meters.
# This does not alter the relative values of the representation vectors and is
# only for readability and to minimize floating point imprecision.
LENGTH_RATE = 100
MISSING_IMAGE_NORMALIZATION = ['mark_missing', 'length_adjustment']
PANORAMA_COVERAGE = 2  # (average meters covered by each panorama view)


def generate_full_agg_dictionary(agg_series):
    """
    Generates a dictionary including all object classes from a pd.Series
    :param agg_series: (pd.Series) representing object instance counts or
    weighted counts for each type of class
    :return: (dict)
    """
    agg_dict = {}
    for obj_class in CLASSES_TO_LABEL.keys():
        agg_dict[obj_class] = agg_series.get(key=obj_class, default=0)
    return agg_dict


# Normalization functions
def adjust_length_with_missings(length, num_missing_images,
                                missing_img_normalization):
    """
    Modifies the street segment length to account for missing images.
    :param length: (float) length of the street segment (meters)
    :param num_missing_images: (int) number of panoramas that were missing
    when collecting the imagery for the street segment
    :param missing_img_normalization: Equal to 'length_adjustment' if computing
    a representation vector for a segment that includes missing images
    :return:
    """
    if missing_img_normalization != 'length_adjustment' and num_missing_images > 0:
        raise Exception('[ERROR] Missing image normalization should be set'
                        'to length_adjustment if computing vector representations'
                        'for segments with missing images')
    # Compute an estimate of the number of missing meters
    missing_meters = num_missing_images * PANORAMA_COVERAGE

    # Reduce street length. The 1/2 factor is included to reflect that a single
    # missing image refers to a single view of the street; that is, if a
    # panorama is missing, it will be double counted as we query it twice (one
    # time for each heading)
    adj_length = length - missing_meters / 2

    if adj_length <= 0:
        print('[WARNING] Non-positive segment length resulting from segment'
              'length missing image adjustment')
        adj_length = 0.00001  # Temporary fix to avoid division by zero

    return adj_length


# Aggregation functions
def aggregate_count(df, img_size, length, num_missing_images,
                    missing_img_normalization):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: Not used. Added for convenience as it is required by other
    aggregation functions.
    :param length: (float) length of the street segment (meters)
    :param num_missing_images: (int) number of panoramas that were missing
    when collecting the imagery for the street segment
    :param missing_img_normalization: Equal to 'length_adjustment' if computing
    a representation vector for a segment that includes missing images
    :return: (dict) of counts for each class
    """
    counts = df[['img_id', 'class']].groupby(['class']).count()

    # Normalize by street length
    adj_length = adjust_length_with_missings(
        length, num_missing_images, missing_img_normalization)
    counts = counts / adj_length * LENGTH_RATE

    # Generate complete dictionary
    counts = generate_full_agg_dictionary(counts['img_id'])
    return counts


def aggregate_confidence_weighted(df, img_size, length, num_missing_images,
                                  missing_img_normalization):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class,
    weighted by the confidence of each instance's prediction.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: Not used. Added for convenience as it is required by other
    aggregation functions.
    :param length: (float) length of the street segment (meters)
    :param num_missing_images: (int) number of panoramas that were missing
    when collecting the imagery for the street segment
    :param missing_img_normalization: Equal to 'length_adjustment' if computing
    a representation vector for a segment that includes missing images
    :return: (dict) of confidence-weighted counts for each class
    """
    # Weight counts
    weighted_counts = df[['confidence', 'class']].groupby(['class']).sum()

    # Normalize by street length
    adj_length = adjust_length_with_missings(
        length, num_missing_images, missing_img_normalization)
    weighted_counts = weighted_counts / adj_length * LENGTH_RATE

    # Generate complete dictionary
    weighted_counts = generate_full_agg_dictionary(weighted_counts['confidence'])
    return weighted_counts


def aggregate_bbox_weighted(df, img_size, length, num_missing_images,
                            missing_img_normalization):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class,
    weighted by the bounding box coverage of the image of each instance's prediction.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: (int) the size of the image (e.g. 640)
    :param length: (float) length of the street segment (meters)
    :param num_missing_images: (int) number of panoramas that were missing
    when collecting the imagery for the street segment
    :param missing_img_normalization: Equal to 'length_adjustment' if computing
    a representation vector for a segment that includes missing images
    :return: (dict) of bounding box-weighted counts for each class
    """
    # Normalize bounding boxes to percentage of the image
    df['normalized_bbox'] = df['bbox_size'] / (img_size * img_size) * 100

    weighted_counts = \
        df[['normalized_bbox', 'class']].groupby(['class']).sum()

    # Normalize by street length
    adj_length = adjust_length_with_missings(
        length, num_missing_images, missing_img_normalization)
    weighted_counts = weighted_counts / adj_length * LENGTH_RATE

    # Generate complete dictionary
    weighted_counts = generate_full_agg_dictionary(weighted_counts['normalized_bbox'])
    return weighted_counts


def aggregate_confxbbox_weighted(df, img_size, length, num_missing_images,
                                 missing_img_normalization):
    """
    Aggregates a DataFrame representing the object instances observed in a
    particular street segment by counting the number of objects in each class,
    weighted by the bounding box coverage of the image of each instance's
    prediction and its confidence.
    :param df: (pd.DataFrame) containing rows for a particular segment_id, and
    the columns: img_id, confidence, bbox_size and class. Each row represents
    the instance of an object observed in an image associated to the street segment.
    :param img_size: (int) the size of the image (e.g. 640)
    :param length: (float) length of the street segment (meters)
    :param num_missing_images: (int) number of panoramas that were missing
    when collecting the imagery for the street segment
    :param missing_img_normalization: Equal to 'length_adjustment' if computing
    a representation vector for a segment that includes missing images
    :return: (dict) of bounding box, confidence-weighted counts for each class
    """
    # Normalize bounding boxes to percentage of the image
    df['normalized_bbox'] = df['bbox_size'] / (img_size * img_size) * 100

    # Weight by confidence
    df['conf_normalized_bbox'] = df['normalized_bbox'] * df['confidence']

    weighted_counts = \
        df[['conf_normalized_bbox', 'class']].groupby(['class']).sum()

    # Normalize by street length
    adj_length = adjust_length_with_missings(
        length, num_missing_images, missing_img_normalization)
    weighted_counts = weighted_counts / adj_length * LENGTH_RATE

    # Generate complete dictionary
    weighted_counts = generate_full_agg_dictionary(weighted_counts['conf_normalized_bbox'])
    return weighted_counts


# Define aggregation types
AGGREGATIONS = {'count': aggregate_count,
                'Conf_weighted': aggregate_confidence_weighted,
                'Bbox_weighted': aggregate_bbox_weighted,
                'ConfxBbox_weighted': aggregate_confxbbox_weighted}