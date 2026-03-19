"""互卦 (Hu Gua) Calculation Module.

Mutual hexagram calculation - derives an "inner" hexagram from the original.

Algorithm:
- Lower trigram (内卦): yao positions 2, 3, 4 (indices 1, 2, 3)
- Upper trigram (外卦): yao positions 3, 4, 5 (indices 2, 3, 4)
- Combine to form new hexagram ID

Trigram mapping (binary, 0=yin, 1=yang):
    000 -> 0 (坤 trigram)
    001 -> 1 (震 trigram)
    010 -> 2 (坎 trigram)
    011 -> 3 (兑 trigram)
    100 -> 4 (巽 trigram)
    101 -> 5 (离 trigram)
    110 -> 6 (艮 trigram)
    111 -> 7 (乾 trigram)

Hexagram ID: (7-lower) * 8 + (7-upper) + 1
    (1=乾为天, 64=坤为地 in standard ordering)
"""


def calculate_trigram_value(yao: list) -> int:
    """Convert 3 yao to trigram index (0-7).

    Args:
        yao: List of 3 integers (0=yin, 1=yang), from bottom to top.

    Returns:
        Trigram index 0-7 where 0=坤, 7=乾.
    """
    return yao[2] * 4 + yao[1] * 2 + yao[0]


def calculate_hu_gua(hexagram_id: int, lines: list) -> int:
    """Calculate the mutual hexagram (互卦) from original hexagram.

    The mutual hexagram is derived by combining:
    - Lower trigram: yao positions 2, 3, 4 (二三四爻)
    - Upper trigram: yao positions 3, 4, 5 (三四五爻)

    Args:
        hexagram_id: Original hexagram ID (1-64), not used in calculation
                    but kept for API consistency.
        lines: List of 6 integers (0=yin, 1=yang), from bottom to top.
               lines[0] = 初爻 (position 1)
               lines[1] = 二爻 (position 2)
               lines[2] = 三爻 (position 3)
               lines[3] = 四爻 (position 4)
               lines[4] = 五爻 (position 5)
               lines[5] = 上爻 (position 6)

    Returns:
        Mutual hexagram ID (1-64).

    Note:
        hexagram_id parameter is kept for API consistency but not used
        in calculation since mutual hexagram is derived solely from lines.

    Example:
        >>> calculate_hu_gua(1, [1,1,1,1,1,1])  # 乾为天
        1

        >>> calculate_hu_gua(1, [0,0,0,0,0,0])  # 坤为地
        64
    """
    # Extract yao for lower trigram (二三四爻 = indices 1,2,3)
    lower_yao = [lines[1], lines[2], lines[3]]

    # Extract yao for upper trigram (三四五爻 = indices 2,3,4)
    upper_yao = [lines[2], lines[3], lines[4]]

    # Convert to trigram indices
    lower_trigram = calculate_trigram_value(lower_yao)
    upper_trigram = calculate_trigram_value(upper_yao)

    # Calculate hexagram ID: invert trigram positions (1=乾, 64=坤)
    hu_gua_id = (7 - lower_trigram) * 8 + (7 - upper_trigram) + 1

    return hu_gua_id
