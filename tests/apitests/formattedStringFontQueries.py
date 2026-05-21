size(460, 190)

fill(1)
rect(0, 0, width(), height())

sourceSerif = "../fonts/SourceSerifPro-Regular.otf"
mutatorSans = "../fonts/MutatorSans.ttf"

t = FormattedString(font=sourceSerif, fontSize=18)
features = t.listOpenTypeFeatures()
assert "smcp" in features
assert "kern" in features

t = FormattedString(font=mutatorSans, fontSize=18)
variations = t.listFontVariations()
instances = t.listNamedInstances()
assert set(variations) == {"wdth", "wght"}
assert "MutatorMathTest-BoldWide" in instances

fill(0)
text("Source Serif features: " + ", ".join(features[:8]), (24, 130))
text("Mutator Sans axes: " + ", ".join(sorted(variations)), (24, 96))
text("Named instances: " + str(len(instances)), (24, 62))
