size(720, 430)

fill(0.97)
rect(0, 0, width(), height())

qr = ImageObject()
qr.QRCodeGenerator((150, 150), "drawbot-skia")

code = ImageObject()
code.code128BarcodeGenerator((300, 92), "DRAWBOT-SKIA", quietSpace=12, barcodeHeight=56)

pdf = ImageObject()
pdf.PDF417BarcodeGenerator(
    (300, 120),
    "drawbot-skia PDF417",
    minWidth=2,
    maxWidth=8,
    minHeight=3,
    maxHeight=12,
    dataColumns=0,
    rows=0,
    preferredAspectRatio=3,
    compactionMode=0,
    compactStyle=False,
    correctionLevel=2,
    alwaysSpecifyCompaction=False,
)

image(qr, (68, 156))
image(code, (286, 220))
image(pdf, (286, 88))

fill(0.08)
fontSize(31)
text("Barcode generators", (68, 346))
fontSize(16)
text("QRCodeGenerator", (68, 124))
text("code128BarcodeGenerator", (286, 194))
text("PDF417BarcodeGenerator", (286, 62))

fontSize(13)
text("Showcase: standards-oriented barcode output implemented in this fork.", (68, 36))
