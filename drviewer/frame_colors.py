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

def _arrange_around_circle(distances, ordering):
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
    thetas += np.random.uniform(0.0, 2 * np.pi) # random offset
    
    # Determine radius
    R = np.abs(theta_distances - np.mean(theta_distances)).mean() / np.max(theta_distances)
    
    # Create the points
    reduced = np.zeros((len(ordering), 2))
    for index, theta in zip(ordering, thetas):
        reduced[index] = [R * np.cos(theta), R * np.sin(theta)]
    
    return reduced

def compute_colors(frames, ids_of_interest=None, peripheral_points=None, scale_factor=1.0):
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
    
    # First compute a distance matrix for the IDs for each frame
    neighbor_dists = [np.log(1 + frame.distances(ids_of_interest, peripheral_points).flatten()) for frame in frames]

    distances = np.zeros((len(frames), len(frames)))
    for i in range(len(frames)):
        for j in range(len(frames)):
            distances[i, j] = np.sqrt(np.mean((neighbor_dists[i] - neighbor_dists[j]) ** 2))

    # Compute an ordering using hierarchical clustering
    ordering_indexes = _clustered_ordering(distances)

    # Arrange the colors around a color wheel in the L*a*b* color space.
    reduced = _arrange_around_circle(distances, ordering_indexes)

    # Generate colors in L*a*b* space and convert to HSL/HSV
    colors = []
    offset = np.random.uniform(-25.0, 25.0, 2)
    for point in reduced:
        scaled_point = np.array([point[0] * 100.0 * scale_factor + offset[0],
                                point[1] * 100.0 * scale_factor + offset[1]])
        lab = LabColor(70.0, scaled_point[1], scaled_point[0])
        rgb = convert_color(lab, HSLColor)
        colors.append((int(rgb.hsl_h), int(rgb.hsl_s * 100.0), int(rgb.hsl_l * 100.0)))

    return colors