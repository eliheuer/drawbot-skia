size(520, 360)

fill(0.98)
rect(0, 0, width(), height())

fill(0.08)
fontSize(20)
text(f"canvas: {int(width())} x {int(height())}", (48, 304))

fill(0.2, 0.45, 0.8)
stroke(None)
rect(70, 96, 120, 120)

save()
translate(318, 156)
rotate(24)
fill(0.95, 0.48, 0.16)
rect(-60, -60, 120, 120)
restore()

save()
translate(392, 120)
scale(1.25, 0.7)
fill(0.15, 0.6, 0.42)
oval(-54, -54, 108, 108)
restore()

fill(0.08)
fontSize(18)
text("save / translate / rotate / scale / restore", (48, 48))
