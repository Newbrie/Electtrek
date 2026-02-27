def get_L4area(children, point):
    for child in children:
        if child.geometry.contains(point).item():
            return child.value
    return "Unknown"
