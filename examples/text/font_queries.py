size(700, 430)

font_path = "../../tests/fonts/MutatorSans.ttf"
features = listOpenTypeFeatures(font_path)
variations = listFontVariations(font_path)

fill(0.98)
rect(0, 0, width(), height())

fill(0.08)
font("Helvetica")
fontSize(32)
text("Font queries", (56, 344))

fontSize(16)
text("listOpenTypeFeatures()", (56, 284))
text(", ".join(features), (56, 258))

text("listFontVariations()", (56, 206))
y = 176
for tag, data in sorted(variations.items()):
    text(
        f"{tag}: {data['name']} {int(data['minValue'])}-{int(data['maxValue'])}",
        (56, y),
    )
    y -= 26

fontSize(15)
text(f"fontContainsCharacters('ABC'): {fontContainsCharacters('ABC')}", (56, 84))

font(font_path)
fontSize(64)
fontVariations(wght=900, wdth=850)
fill(0.12, 0.2, 0.34)
text("ABC", (428, 176))
