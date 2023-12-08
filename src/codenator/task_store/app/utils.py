import math
from numpy import dot
from numpy.linalg import norm

def Euclidean_distance(v1, v2):
    distance = math.dist(v1, v2)
    return distance

def cosine_similarity(v1, v2):
    similarity = dot(v1, v2)/(norm(v1)*norm(v2))
    return (1 - similarity)
