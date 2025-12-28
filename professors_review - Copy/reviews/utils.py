def get_star_rating(rating):
    """
    Convert a numerical rating to a star representation.

    Args:
        rating (float): A numerical rating (e.g., 4.2).

    Returns:
        str: An HTML string representing the star rating.
    """
    full_stars = int(rating)
    half_star = rating - full_stars >= 0.5
    empty_stars = 5 - full_stars - half_star

    star_html = ''
    for _ in range(full_stars):
        star_html += '<span class="fa fa-star checked"></span>'  # Full star

    if half_star:
        star_html += '<span class="fa fa-star-half-o checked"></span>'  # Half star

    for _ in range(int(empty_stars)):
        star_html += '<span class="fa fa-star-o"></span>'  # Empty star

    return star_html
