from .gstate import _cmykArgs, _colorArgs


class FormattedString:
    def __init__(self, txt=None, **properties):
        self._runs = []
        self._properties = {}
        self._features = {}
        self._variations = {}
        self._properties.update(self._normalizedProperties(properties))
        if txt:
            self.append(txt)

    def append(self, txt, **properties):
        properties = self._normalizedProperties(properties)
        runProperties = self._currentProperties()
        runProperties.update(properties)
        self._runs.append((str(txt), runProperties))

    def _normalizedProperties(self, properties):
        properties = dict(properties)
        if "font" in properties and properties["font"] is None:
            del properties["font"]
        if "cmykFill" in properties:
            properties["fill"] = _cmykArgs(_asColorArgs(properties.pop("cmykFill")))
        elif "fill" in properties:
            properties["fill"] = _colorArgs(_asColorArgs(properties["fill"]))
        return properties

    def _currentProperties(self):
        properties = dict(self._properties)
        properties["features"] = dict(self._features)
        properties["variations"] = dict(self._variations)
        return properties

    def textProperties(self):
        return self._currentProperties()

    def clear(self):
        self._runs.clear()

    def font(self, fontNameOrPath, fontSize=None):
        self._properties["font"] = fontNameOrPath
        if fontSize is not None:
            self._properties["fontSize"] = fontSize

    def fontSize(self, size):
        self._properties["fontSize"] = size

    def lineHeight(self, value):
        self._properties["lineHeight"] = value

    def fill(self, *args):
        self._properties["fill"] = _colorArgs(args)

    def cmykFill(self, *args):
        self._properties["fill"] = _cmykArgs(args)

    def align(self, align):
        self._properties["align"] = align

    def openTypeFeatures(self, *, resetFeatures=False, **features):
        if resetFeatures:
            self._features.clear()
        self._features.update(features)
        return dict(self._features)

    def fontVariations(self, *, resetVariations=False, **variations):
        if resetVariations:
            self._variations.clear()
        self._variations.update(variations)
        return dict(self._variations)

    def language(self, language):
        self._properties["language"] = language

    def size(self):
        from .drawing import Drawing

        return Drawing().textSize(self)

    def __iadd__(self, txt):
        self.append(txt)
        return self

    def __add__(self, txt):
        result = self.copy()
        result += txt
        return result

    def copy(self):
        result = FormattedString()
        result._runs = [(txt, dict(properties)) for txt, properties in self._runs]
        result._properties = dict(self._properties)
        result._features = dict(self._features)
        result._variations = dict(self._variations)
        return result

    def __str__(self):
        return "".join(txt for txt, properties in self._runs)

    def __len__(self):
        return sum(len(txt) for txt, properties in self._runs)

    def _iterRuns(self):
        return iter(self._runs)


def _asColorArgs(color):
    if isinstance(color, tuple):
        return color
    return (color,)
