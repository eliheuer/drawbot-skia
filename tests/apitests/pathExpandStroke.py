size(320, 220)
fill(1)
rect(0, 0, width(), height())

path = BezierPath()
path.moveTo((50, 70))
path.curveTo((95, 170), (160, 20), (230, 140))

stroke(0.8)
strokeWidth(2)
fill(None)
drawPath(path)

expanded = path.expandStroke(22, lineCap="round", lineJoin="round")
fill(1, 0, 0, 0.45)
stroke(0)
strokeWidth(1)
drawPath(expanded)
