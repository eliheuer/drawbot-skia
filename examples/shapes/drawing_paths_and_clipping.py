size(620, 400)

fill(0.96)
rect(0, 0, width(), height())

clip = BezierPath()
clip.oval(78, 78, 232, 232)
clip.rect(194, 78, 232, 232)

save()
clipPath(clip)
for index in range(14):
    fill(0.06 + index * 0.045, 0.22, 0.72 - index * 0.035)
    rect(42 + index * 38, 64, 24, 270)
restore()

stroke(0.06, 0.16, 0.28)
strokeWidth(7)
fill(None)
drawPath(clip)

newPath()
moveTo((98, 330))
lineTo((188, 356))
qCurveTo((282, 298), (372, 344))
curveTo((438, 388), (520, 302), (560, 350))
stroke(0.94, 0.32, 0.16)
strokeWidth(5)
fill(None)
drawPath()

fill(0.08)
stroke(None)
fontSize(18)
text("newPath, moveTo, lineTo, qCurveTo, curveTo, clipPath", (58, 36))
