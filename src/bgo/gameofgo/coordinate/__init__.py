from recordclass import dataobject


"""

    coordinate: Defines three types of coordinate systems used by BGo

    Name        Example     Description
    Flat        360         Integer value 0 to 360
    Alpha       'ss'        String of two characters 'a' to 's', 'tt' pass is not a valid coordinate
    Cartesian   (18,18)     Two element tuple 0 to 18
    
"""


# Transform to generate list of neighbors
TRANSFORM_NEIGHBORS = ((-1, 0), (1, 0), (0, -1), (0, 1))

# -----------------------------------------------------------------------------


def is_valid(coord):
    """
    Wraps a coord.is_valid() call in case coord is not type Alpha or Cart.
    :param coord:  Alpha or Cart coordinate to test
    :return: True or False
    """
    try:
        if not coord.is_valid():
            return False
    except AttributeError:
        return False
    return True


def to_alpha(coord):
    """
    Wraps a coord.to_alpha() call in case coord is not type Alpha or Cart.
    :param coord: Coordinate to convert
    :return: Alpha coordinate
    """
    try:
        return coord.to_alpha()
    except AttributeError:
        return Alpha('')


def to_cart(coord):
    """
    Wraps a coord.to_alpha() call in case coord is not type Alpha or Cart.
    :param coord: Coordinate to convert
    :return: Cart coordinate
    """
    try:
        return coord.to_cart()
    except AttributeError:
        return Cart(None, None)


# -----------------------------------------------------------------------------

class Alpha(dataobject):
    """
    A coordinate with x and y values between 'a' and 's'.
    The coordinate 'tt' is used in game records as a pass and is considered an invalid coordinate.
    Can be constructed with one or two arguments: Alpha('aa') or Alpha('a', 'a')
    The property 'xy' combines the x and y into a single string.
    If is_valid() returns False, the x and y values should not be used.
    """
    x: str
    y: str
    __options__ = dict(readonly=True, fast_new=True, gc=True)

    def __new__(cls, x_or_xy, y=None):
        try:
            if x_or_xy == y == None:
                ux = uy = None
            elif y is not None:
                if len(x_or_xy) == 1 and len(y) == 1:
                    ux = x_or_xy
                    uy = y
                else:
                    ux = uy = None
            elif len(x_or_xy) == 2:
                ux, uy = x_or_xy
            else:
                ux = uy = None
        except TypeError:
            ux = uy = None
        return super(Alpha, cls).__new__(cls, ux, uy)

    def is_valid(self):
        try:
            if 'a' <= self.x <= 's' and 'a' <= self.y <= 's':
                return True
            else:
                return False
        except TypeError:
            return False

    @property
    def xy(self):
        try:
            return self.x + self.y
        except TypeError:
            return None

    def to_alpha(self):
        return self

    def to_cart(self):
        if not self.is_valid():
            return Cart(None, None)
        else:
            try:
                return Cart(ord(self.x) - 97, ord(self.y) - 97)
            except TypeError:
                return Cart(None, None)

# -----------------------------------------------------------------------------


class Cart(dataobject):
    """
    A coordinate with x and y values between 0 and 18.
    If is_valid() returns False, the x and y values should not be used.
    """
    x: int
    y: int
    __options__ = dict(readonly=True, fast_new=True, gc=True)

    def __new__(cls, x, y):
        return super(Cart, cls).__new__(cls, x, y)
    
    @property
    def xy(self):
        return self.x, self.y

    def is_valid(self):
        try:
            if 0 <= self.x <= 18 and 0 <= self.y <= 18:
                return True
            else:
                return False
        except TypeError:
            return False

    def to_alpha(self):
        if not self.is_valid():
            return Alpha('')
        else:
            try:
                return Alpha(chr(self.x + 97), chr(self.y + 97))
            except TypeError:
                return Alpha('')

    def to_cart(self):
        return self


# -----------------------------------------------------------------------------


# For speed, calculate and cache the entire boards neighbor list on the first call
pre_neighbors = None

def neighbor_list(cart_coord):
    """
    Returns a set of coordinates that are neighbors of cart_coord.
    :param cart_coord: Source coordinate
    :return: Set of neighboring coordinates
    """
    global pre_neighbors
    if pre_neighbors is None:
        pre_neighbors = {}
        for x in range(19):
            for y in range(19):
                co = Cart(x=x, y=y)
                neighbors = set()
                for nx, ny in TRANSFORM_NEIGHBORS:
                    new_coord = Cart(x=co.x + nx, y=co.y + ny)
                    if 0 <= new_coord.x <= 18 and 0 <= new_coord.y <= 18:
                        neighbors.add(new_coord)
                pre_neighbors[co] = neighbors
    try:
        return pre_neighbors[cart_coord]
    except KeyError:
        return set()

# -----------------------------------------------------------------------------


"""
    The transform matrix describes how to transform coordinates into 8 different transforms.
    Transform #0 is the identity transform, which yields the original coordinate.
    
    Each row of the transformation matrix has two operations
        ( (transform x coordinate to...), (transform y coordinate to ...) )
    Each individual operation sets a coordinate to either +/- X or +/- Y.
        ( 1,  0)  ->  x    ->   set value to x
        (-1,  0)  ->  18-x ->   set value to -x 
        ( 0,  1)  ->  y    ->   set value to y
        ( 0, -1)  ->  18-y ->   set value to -y
    So the transform operation ((-1,0), (0,1)) sets a coordinate to (-x, y), inverting the x value
    
    The inverse transform list is used to reverse a transformation.
    If a coordinate has been transformed to TRANSFORM_MATRIX[i], then transforming the new 
    coordinate by TRANSFORM_MATRIX[INVERSE_TRANSFORM[i]] yields the original coordinate.
"""

TRANSFORM_MATRIX = (     # N  Inv  Operation
    ((1, 0), (0, 1)),    # 0   0    Identity                (x,y)       (X, Y)
    ((-1, 0), (0, 1)),   # 1   1    Flip left-right         (18-x, y)   (-X, Y)
    ((1, 0), (0, -1)),   # 2   2    Flip top-bottom         (x, 18-y)   (X, -Y)
    ((0, 1), (-1, 0)),   # 3   5    Rotate 90 CCW           (y, 18-x)   (Y, -X)
    ((-1, 0), (0, -1)),  # 4   4    Rotate 180 CCW          (18-x,18-y) (-X, -Y)
    ((0, -1), (1, 0)),   # 5   3    Rotate 270 CCW          (18-y, x)   (-Y, X)
    ((0, 1), (1, 0)),    # 6   6    Rotate 90 CCW, FlipLR   (y, x)      (Y, X)
    ((0, -1), (-1, 0)),  # 7   7    Rotate 270 CCW, FlipTB  (18-y,18-x) (-Y, -X)
)

TRANSFORMATION_NAMES = (
    'identity',
    'flip left-right',
    'flip top-bottom',
    'rotate 90 ccw',
    'rotate 180 ccw',
    'rotate 270 ccw',
    'rotate 90 ccw, flip top-bottom',
    'rotate 270 ccw, flip top-bottom',
)

INVERSE_TRANSFORM = (0, 1, 2, 5, 4, 3, 6, 7)


# -----------------------------------------------------------------------------


def transform(cart_coord, transform_number, invert=False):
    """
    If invert is True:
        cart_coord has previously been transformed from identity to transform_number
        perform the inverse operation to transform cart_coord back to identity
    If invert is False:
        transforms cart_coord to the passed transform number

    :param cart_coord: Valid Cart coordinate
    :param transform_number: 0 to 7
    :param invert: True or False if the inverse transform should be used
    :return: Transformed valid Cart coordinate
    :raises ValueError: If cart_coord !is_valid or transform_number is not an int or out of range
    """
    if not is_valid(cart_coord):
        raise ValueError(f'Coordinate.transform(): invalid coordinate [{cart_coord}]')
    try:
        if not 0 <= transform_number <= 7:
            raise ValueError(f'Coordinate.transform(): to_rotation must be between 0 and 7, passed [{transform_number}]')
    except TypeError:
        raise ValueError(f'Coordinate.transform(): invalid to_rotation [{transform_number}]')
    use_tn = INVERSE_TRANSFORM[transform_number] if invert else transform_number
    x, y = cart_coord.xy
    try:
        return Cart(x=(TRANSFORM_MATRIX[use_tn][0][0] * (x - 9)) + (TRANSFORM_MATRIX[use_tn][0][1] * (y - 9)) + 9,
                    y=(TRANSFORM_MATRIX[use_tn][1][0] * (x - 9)) + (TRANSFORM_MATRIX[use_tn][1][1] * (y - 9)) + 9)
    except TypeError:
        raise ValueError(f'Coordinate.transform(): invalid coordinate [{cart_coord}]')


def which_transform_to_move_to_upper_right(cart_coord):
    """
    Given a coordinate, return which transform number is needed to move the coordinate to the upper right
    quad of the board.
    :param coord: A valid coordinate of any type
    :return: Integer transform number between 0-7
    :raises ValueError: Invalid coordinate passed
    """
    if not is_valid(cart_coord):
        raise ValueError(f'Coordinate.which_transform_to_move_to_upper_right(): passed invalid coordinate')
    x, y = cart_coord.xy
    if x < 9:
        if y < 9:
            return 1    # Upper Left: Flip left to right
        elif y > 9:
            return 4    # Lower Left: Rotate 180
        else:
            return 1    # Center Left: Flip left to right
    elif x > 9:
        if y < 9:
            return 0    # Upper Right: Identity, no rotation
        elif y > 9:
            return 2    # Lower Right: Flip top to bottom
        else:
            return 0    # Center Right: Identity, no rotation
    else:
        if y < 9:
            return 5    # Center Top: Rotate 270 CCW
        elif y > 9:
            return 3    # Center Bottom: Rotate 90 CCW
        else:
            return 0    # Center Point (Tengen): Identity, no rotation


def bias_coord_for_merge(coord1, coord2, transform_number):
    """
    Given two coordinates, pick one based on predefined preferences and return it.
    The two coordinates passed have a board symmetry between them which makes them equivalent.
    Transform number is the transform needed to convert coord1 to coord2.
    # TODO merge_rotation == 3? ever seen?   1 and 3 should both have left/right symmetry and be the same?
    :param coord1:
    :param coord2:
    :param transform_number: Transform number to transform coord1 to coord2
    :return: A coordinate that is equal to coord1 or coord2 based on predefined preferences.
    """
    if not is_valid(coord1) or not is_valid(coord2):
        raise ValueError(f'Coordinate.bias_coord_for_merge(): passed invalid coordinates [{coord1}] [{coord2}]')
    if transform_number == 2:
        # 2: Top and bottom symmetry, prefer bottom (larger y) coordinate
        return coord1 if coord1.y > coord2.y else coord2
    elif transform_number == 1:
        # 1: Left and right symmetry, prefer right (larger x) coordinate
        return coord1 if coord1.x > coord2.x else coord2
    elif transform_number == 7:
        return coord1 if coord1.y > coord2.y else coord2
    elif transform_number == 6:
        return coord1 if coord1.x > coord2.x else coord2
    elif transform_number == 4:
        # 4: Rotate 180 ccw, diagonal , prefer right side or larger x coordinate
        return coord1 if coord1.x > coord2.x else coord2
    elif transform_number == 5:
        # 5: Prefer larger Y
        return coord1 if coord1.y > coord2.y else coord2
    else:
        raise ValueError(f'Coordinate.bias_coord_for_merge(): unknown transform_number {transform_number}')

