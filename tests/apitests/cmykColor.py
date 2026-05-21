size(240, 180)

cmykLinearGradient(
    (0, 0),
    (240, 180),
    [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0.2)],
    [0, 0.35, 0.7, 1],
)
rect(0, 0, 240, 180)

cmykShadow((8, -8), 12, (0, 0, 0, 0.6, 0.45))
cmykFill(0, 1, 1, 0)
rect(22, 28, 58, 58)

cmykFill(1, 0, 1, 0, 0.85)
cmykStroke(1, 1, 0, 0)
strokeWidth(5)
oval(92, 26, 62, 62)

shadow(None)
cmykFill(0, 0, 0, 0)
cmykRadialGradient(
    startPoint=(192, 58),
    colors=[(0, 0, 0, 0), (0, 1, 1, 0), (0, 0, 0, 1)],
    locations=[0, 0.65, 1],
    endRadius=44,
)
rect(158, 24, 68, 68)

cmykFill(None)
cmykStroke(0, 0, 0, 0.85)
strokeWidth(3)
rect(18, 110, 204, 44)
