from enum import IntEnum


class StoneColor(IntEnum):
    """
        Provides IntEnum definition for Black and White stones

        >>> repr(StoneColor.BLACK)
        '<StoneColor.BLACK: 1>'
        >>> str(StoneColor.BLACK)
        'StoneColor.BLACK'
        >>> type(StoneColor.BLACK)
        <enum 'StoneColor'>
        >>> type(StoneColor.BLACK.value)
        <class 'int'>
        >>> StoneColor.BLACK.value
        1
    """

    BLACK = 1
    WHITE = 2
    NONE = 0


# --------------------------------------------------


def color_char(stone_color):
    """
    Returns a text character to be used to represent an empty space, black stone, or white stone
    :param stone_color: StoneColor to be represented by a text character
    :return:
    :raises TypeError: If stone_color is not type StoneColor
    :raises ValueError: if stone_color is unknown value
    """
    if not isinstance(stone_color, StoneColor):
        raise TypeError(f'StoneColor.color_char() - Expecting type StoneColor')
    if stone_color == StoneColor.NONE:
        return '.'
    elif stone_color == StoneColor.BLACK:
        return 'X'
    elif stone_color == StoneColor.WHITE:
        return 'O'
    else:
        raise ValueError(f'StoneColor.color_char(): unknown value {stone_color}')


# --------------------------------------------------


def invert_color(stone_color):
    """
        Returns the inverted stone color using the following rules:
            BLACK -> WHITE
            WHITE -> BLACK
            NONE ->  NONE
    :param stone_color: StoneColor to invert
    :return: The inverse StoneColor of the input stone_color
    :raises TypeError: If stone_color is not type StoneColor
    :raises ValueError: if stone_color is unknown value
    """
    if not isinstance(stone_color, StoneColor):
        raise TypeError(f'{__file__}:StoneColor.invert_color() - Expecting type StoneColor')
    if stone_color == StoneColor.BLACK:
        return StoneColor.WHITE
    elif stone_color == StoneColor.WHITE:
        return StoneColor.BLACK
    elif stone_color == StoneColor.NONE:
        return StoneColor.NONE
    else:
        raise ValueError(f'{__file__}:StoneColor.invert_color() - Unknown color')
