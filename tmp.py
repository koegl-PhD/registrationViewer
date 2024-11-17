import numpy as np

x_1 = np.asarray([0.7, 0.3, 0.2])
x_2 = np.asarray([0.35, 0.15, 0.1])

def angle_between_vectors(v1, v2):
    # Compute the dot product
    dot_product = np.dot(v1, v2)
    # Compute the norms (magnitudes) of the vectors
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    # Calculate the cosine of the angle
    cos_theta = dot_product / (norm_v1 * norm_v2)
    # Ensure cos_theta is within the valid range [-1, 1]
    cos_theta = np.clip(cos_theta, -1, 1)
    # Calculate the angle in radians
    angle = np.arccos(cos_theta)
    # Convert the angle to degrees (optional)
    angle_degrees = np.degrees(angle)
    return angle, angle_degrees


# get the angle of vector x_1 to the origin
angle_1 = angle_between_vectors(x_1, np.array([1, 0, 0]))[1]
angle_2 = angle_between_vectors(x_2, np.array([1, 0, 0]))[1]


x_1_compliment = np.asarray([0.7, 0.3, 0.2, 0.3, 0.7, 0.8])

a = 0
