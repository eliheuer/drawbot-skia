size(220, 180)

fill(1, 0.85, 0.2)
stroke(0)
strokeWidth(3)

newPath()
moveTo((22, 24))
lineTo((22, 146))
curveTo((78, 176), (142, 126), (196, 154))
qCurveTo((166, 82), (198, 26))
lineTo((114, 48))
arc((80, 74), 38, 20, 205, False)
closePath()
drawPath()

with savedState():
    newPath()
    moveTo((44, 54))
    lineTo((176, 54))
    lineTo((112, 136))
    closePath()
    clipPath()

    fill(0, 0.2, 1, 0.6)
    stroke(None)
    oval(38, 34, 144, 120)
