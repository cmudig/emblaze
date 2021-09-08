"""
A helper module to compute HSV colors for each frame in an animated DR plot.
The colors are chosen such that the perceptual distance between colors
corresponds to the difference between the frames, with respect to some set of
points of interest.
"""
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from colormath.color_objects import LabColor, HSLColor
from colormath.color_conversions import convert_color
import itertools
from numba.typed import List
from .utils import Field, inverse_intersection

def _clustered_ordering(distances):
    """
    Returns an ordering of the items whose pairwise distances are given.
    """
    clusterer = AgglomerativeClustering(n_clusters=len(distances), affinity='precomputed', linkage='average')
    clusterer.fit(distances)

    def walk_tree(children):
        ii = itertools.count(len(distances))
        children_dict = {next(ii): [x[0], x[1]] for x in children}
        ii = itertools.count(len(distances))
        children_list = [(next(ii), x[0], x[1]) for x in children]
        stack = [children_list[-1][0]]

        ordering = []
        while stack:
            last = stack.pop()
            if last in children_dict:
                l, r = children_dict[last]
                if l not in children_dict:
                    ordering.append(l)
                else:
                    stack.append(l)
                if r not in children_dict:
                    ordering.append(r)
                else:
                    stack.append(r)               
            else:
                ordering.append(last)
        return ordering

    return walk_tree(clusterer.children_)

def _arrange_around_circle(distances, offset, ordering):
    """
    Arrange the points represented by the given distance matrix around a circle.
    The radius of the circle is a rough measure of 'clusteredness' of the data,
    as measured by the average deviation from the mean normalized by the max
    distance.
    
    Args:
        distances: An n x n distance matrix.
        ordering: List of n indexes determining which order to lay the points in.
        
    Returns:
        An n x 2 array representing locations around a circle.
    """
    # Find thetas first
    thetas = [0.0]
    theta_distances = distances ** 2
    
    for i in range(1, len(ordering)):
        thetas.append(thetas[-1] + theta_distances[ordering[i],ordering[i - 1]])

    last_theta = thetas[-1] + theta_distances[ordering[-1], ordering[0]]
    thetas = np.array(thetas) * 2 * np.pi / last_theta # scale around the circle
    thetas += offset
    # thetas += np.random.uniform(0.0, 2.0 * np.pi) # random offset
    
    # Determine radius
    # R = np.abs(theta_distances - np.mean(theta_distances)).mean() / np.max(theta_distances)
    # absolute distance-based measure
    # R = (distances.sum() / (len(distances.flatten()) - len(distances))) / max_dist
    R = np.max([distances[i,j] for i in range(distances.shape[0]) for j in range(distances.shape[1]) if i != j])
    R = 0.5 * np.log10(1 + 19 * R)
    
    # Create the points
    reduced = np.zeros((len(ordering), 2))
    for index, theta in zip(ordering, thetas):
        reduced[index] = [R * np.cos(theta), R * np.sin(theta)]
    
    return reduced

def compute_colors(frames, ids_of_interest=None, scale_factor=1.0):
    """
    Computes HSV colors for each frame.
    
    Args:
        frames: A list of Embeddings.
        ids_of_interest: A list of IDs to limit distance calculation to. If
            None, uses the full contents of each frame.
        scale_factor: Amount by which to scale the color wheel. Values larger
            than 1 effectively make the colors more saturated and appear more
            different.
            
    Returns:
        A list of HSV colors, expressed as tuples of (hue, saturation, value).
    """

    distance_sample = ids_of_interest or frames[0].ids.tolist()
    if len(distance_sample) > 1000:
        distance_sample = np.random.choice(distance_sample, size=1000, replace=False).tolist()
        
    # First compute a distance matrix for the IDs for each frame
    outer_jaccard_distances = np.zeros((len(frames), len(frames)))
    inner_jaccard_distances = np.zeros((len(frames), len(frames)))
    for i in range(len(frames)):
        frame_1_neighbors = frames[i].field(Field.NEIGHBORS, distance_sample)
        for j in range(len(frames)):
            frame_2_neighbors = frames[j].field(Field.NEIGHBORS, distance_sample)
            # If the id set is the entire frame, there will be no outer neighbors
            # so we can just leave this at zero
            if ids_of_interest is not None and len(ids_of_interest):
                outer_jaccard_distances[i,j] = np.mean(inverse_intersection(frame_1_neighbors,
                                                                            frame_2_neighbors,
                                                                            List(distance_sample),
                                                                            True))
            inner_jaccard_distances[i,j] = np.mean(inverse_intersection(frame_1_neighbors,
                                                                        frame_2_neighbors,
                                                                        List(distance_sample),
                                                                        False))

    if ids_of_interest is not None and len(ids_of_interest):
        if len(ids_of_interest) == 1:
            distances = outer_jaccard_distances
        else:
            distances = 0.5 * (outer_jaccard_distances + inner_jaccard_distances)
    else:
        distances = inner_jaccard_distances
    
    # Compute clusteredness in each frame (only used to determine offset of colors)
    neighbor_dists = [np.log(1 + frame.distances(distance_sample, distance_sample).flatten()) for frame in frames]
    clusteredness = np.array([np.abs(ndists - np.mean(ndists)).mean() / np.maximum(np.max(ndists), 1e-3)
                            for ndists in neighbor_dists])

    # Compute an ordering using hierarchical clustering
    ordering_indexes = _clustered_ordering(distances)
    # Put the most cluster-y embedding first
    first_index = np.argmax(clusteredness)
    ordering_position = np.argmax(ordering_indexes == first_index)
    ordering_indexes = np.concatenate([ordering_indexes[ordering_position:], ordering_indexes[:ordering_position]]).astype(int)

    # Arrange the colors around a color wheel in the L*a*b* color space.
    offset = clusteredness[first_index]
    reduced = _arrange_around_circle(distances, offset, ordering_indexes) #, max_dist=np.array(neighbor_dists).mean())

    # Generate colors in L*a*b* space and convert to HSL/HSV
    colors = []
    for point in reduced:
        scaled_point = np.array([point[0] * 100.0 * scale_factor,
                                point[1] * 100.0 * scale_factor])
        lab = LabColor(70.0, scaled_point[1], scaled_point[0])
        rgb = convert_color(lab, HSLColor)
        colors.append((int(rgb.hsl_h), int(rgb.hsl_s * 100.0), int(rgb.hsl_l * 100.0)))

    return colors