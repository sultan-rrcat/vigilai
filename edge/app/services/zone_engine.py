import logging

logger = logging.getLogger(__name__)

def get_normalized_anchor(bbox: list, frame_width: int, frame_height: int) -> tuple:
    """
    Calculates the bottom-center anchor point of a bounding box 
    and normalizes it to the [0.0, 1.0] range.
    bbox format: [x1, y1, x2, y2]
    """
    x1, y1, x2, y2 = bbox
    
    anchor_x = (x1 + x2) / 2.0
    anchor_y = float(y2)  # Bottom of the bounding box
    
    norm_x = anchor_x / frame_width
    norm_y = anchor_y / frame_height
    
    return norm_x, norm_y

def is_point_in_polygon(point: tuple, polygon: list) -> bool:
    """
    Standard Ray-Casting algorithm to determine if a normalized (x,y) point 
    is inside a normalized polygon array [[x1, y1], [x2, y2], ...].
    """
    x, y = point
    inside = False
    n = len(polygon)
    
    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        # Check if the ray crosses the polygon edge
        if (yi > y) != (yj > y):
            # Calculate the x-coordinate of the intersection
            intersect_x = (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi
            if x < intersect_x:
                inside = not inside
        j = i
        
    return inside

def get_tripwire_cross_product(point: tuple, line: list) -> float:
    """
    Calculates which side of a line segment a point is on using the cross product.
    line: [[P1x, P1y], [P2x, P2y]]
    
    Returns:
    > 0 if point is on Side B (Right of the line vector)
    < 0 if point is on Side A (Left of the line vector)
    0 if exactly on the line
    """
    p1x, p1y = line[0]
    p2x, p2y = line[1]
    qx, qy = point
    
    dx = p2x - p1x
    dy = p2y - p1y
    
    # Cross product formula defined in CONVENTIONS.md
    return dx * (qy - p1y) - dy * (qx - p1x)