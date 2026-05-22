import os
from .gstate import (
    TextStyle,
    _cmykArgs,
    _colorArgs,
    _getName,
    _namedInstances,
    _normalizeWritingDirection,
)
from .shaping import getFeatures


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
        if "cmykStroke" in properties:
            properties["stroke"] = _cmykArgs(_asColorArgs(properties.pop("cmykStroke")))
        elif "stroke" in properties:
            properties["stroke"] = _colorArgs(_asColorArgs(properties["stroke"]))
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

    def fontNumber(self, fontNumber):
        self._properties["fontNumber"] = fontNumber

    def fallbackFont(self, fontNameOrPath, fontNumber=0):
        self._properties["fallbackFont"] = fontNameOrPath
        self._properties["fallbackFontNumber"] = fontNumber

    def fallbackFontNumber(self, fontNumber):
        self._properties["fallbackFontNumber"] = fontNumber

    def fontSize(self, size):
        self._properties["fontSize"] = size

    def lineHeight(self, value):
        self._properties["lineHeight"] = value

    def hyphenation(self, value):
        self._properties["hyphenation"] = value

    def tabs(self, *tabs):
        if len(tabs) == 1 and tabs[0] is None:
            tabs = None
        self._properties["tabs"] = tabs

    def fill(self, *args):
        self._properties["fill"] = _colorArgs(args)

    def cmykFill(self, *args):
        self._properties["fill"] = _cmykArgs(args)

    def stroke(self, *args):
        self._properties["stroke"] = _colorArgs(args)

    def cmykStroke(self, *args):
        self._properties["stroke"] = _cmykArgs(args)

    def strokeWidth(self, strokeWidth):
        self._properties["strokeWidth"] = strokeWidth

    def align(self, align):
        self._properties["align"] = align

    def tracking(self, tracking):
        self._properties["tracking"] = tracking

    def baselineShift(self, baselineShift):
        self._properties["baselineShift"] = baselineShift

    def indent(self, indent):
        self._properties["indent"] = indent

    def tailIndent(self, indent):
        self._properties["tailIndent"] = indent

    def firstLineIndent(self, indent):
        self._properties["firstLineIndent"] = indent

    def paragraphTopSpacing(self, value):
        self._properties["paragraphTopSpacing"] = value

    def paragraphBottomSpacing(self, value):
        self._properties["paragraphBottomSpacing"] = value

    def underline(self, underline):
        self._properties["underline"] = underline

    def strikethrough(self, strikethrough):
        self._properties["strikethrough"] = strikethrough

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

    def writingDirection(self, direction):
        self._properties["direction"] = _normalizeWritingDirection(direction)

    def size(self):
        from .drawing import Drawing

        return Drawing().textSize(self)

    def fontContainsCharacters(self, characters):
        cmaps = [self._ttFont().getBestCmap() or {}]
        fallbackFont = self.textProperties().get("fallbackFont")
        if fallbackFont is not None:
            cmaps.append(self._textStyleForFont(fallbackFont).ttFont.getBestCmap() or {})
        return all(
            any(ord(character) in cmap for cmap in cmaps) for character in characters
        )

    def fontContainsGlyph(self, glyphName):
        return glyphName in self._ttFont().getGlyphOrder()

    def fontFilePath(self):
        font = self.textProperties().get("font")
        if font is not None and os.path.exists(os.fspath(font)):
            return os.fspath(font)
        return None

    def fontFileFontNumber(self):
        return self.textProperties().get("fontNumber", 0)

    def listFontGlyphNames(self):
        return list(self._ttFont().getGlyphOrder())

    def fontAscender(self):
        return self._fontUnitsToPoints(self._ttFont()["hhea"].ascent)

    def fontDescender(self):
        return self._fontUnitsToPoints(self._ttFont()["hhea"].descent)

    def fontXHeight(self):
        ttFont = self._ttFont()
        value = getattr(ttFont.get("OS/2"), "sxHeight", 0)
        return self._fontUnitsToPoints(value)

    def fontCapHeight(self):
        ttFont = self._ttFont()
        value = getattr(ttFont.get("OS/2"), "sCapHeight", 0)
        return self._fontUnitsToPoints(value)

    def fontLeading(self):
        return self._fontUnitsToPoints(self._ttFont()["hhea"].lineGap)

    def fontLineHeight(self):
        return self._textStyle().getLineHeight()

    def listOpenTypeFeatures(self, fontNameOrPath=None, fontNumber=0):
        textStyle = self._textStyleForFont(fontNameOrPath)
        features = set()
        for tableTag in ("GSUB", "GPOS"):
            features.update(getFeatures(textStyle.hbFont.face, tableTag))
        return sorted(features)

    def listFontVariations(self, fontNameOrPath=None, fontNumber=0):
        ttFont = self._textStyleForFont(fontNameOrPath).ttFont
        variations = {}
        if "fvar" in ttFont:
            nameTable = ttFont["name"]
            for axis in ttFont["fvar"].axes:
                axisName = _getName(nameTable, axis.axisNameID)
                variations[axis.axisTag] = dict(
                    name=axisName,
                    minValue=axis.minValue,
                    defaultValue=axis.defaultValue,
                    maxValue=axis.maxValue,
                )
        return variations

    def listNamedInstances(self, fontNameOrPath=None, fontNumber=0):
        return _namedInstances(self._textStyleForFont(fontNameOrPath).ttFont)

    def fontNamedInstance(self, name, fontNameOrPath=None):
        instances = self.listNamedInstances(fontNameOrPath)
        try:
            variations = dict(instances[name])
        except KeyError:
            raise KeyError(name) from None
        if fontNameOrPath is not None:
            self.font(fontNameOrPath)
        self._variations.clear()
        self._variations.update(variations)
        return dict(self._variations)

    def appendGlyph(self, *glyphNames):
        cmap = self._ttFont().getBestCmap() or {}
        glyphToCharacter = {
            glyphName: chr(codePoint) for codePoint, glyphName in cmap.items()
        }
        glyphOrder = self._ttFont().getGlyphOrder()
        chars = []
        for glyphName in glyphNames:
            if isinstance(glyphName, int):
                try:
                    glyphName = glyphOrder[glyphName]
                except IndexError:
                    raise KeyError(glyphName) from None
            if glyphName not in glyphToCharacter:
                raise KeyError(glyphName)
            chars.append(glyphToCharacter[glyphName])
        self.append("".join(chars))

    def _textStyle(self):
        properties = self.textProperties()
        textProperties = {
            name: properties[name]
            for name in (
                "font",
                "fontSize",
                "lineHeight",
                "features",
                "variations",
                "language",
                "direction",
                "tabs",
                "hyphenation",
            )
            if name in properties
        }
        return TextStyle(**textProperties)

    def _textStyleForFont(self, fontNameOrPath):
        if fontNameOrPath is None:
            return self._textStyle()
        return self._textStyle().copy(font=fontNameOrPath)

    def _ttFont(self):
        return self._textStyle().ttFont

    def _fontUnitsToPoints(self, value):
        ttFont = self._ttFont()
        return value * self._textStyle().fontSize / ttFont["head"].unitsPerEm

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
    if isinstance(color, (list, tuple)):
        return tuple(color)
    return (color,)
