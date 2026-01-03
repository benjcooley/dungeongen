Paint
classPaint
Paint controls options applied when drawing.

Paint collects all options outside of the Canvas clip and Canvas matrix.

Various options apply to strokes and fills, and images.

Paint collects effects and filters that describe single-pass and multiple-pass algorithms that alter the drawing geometry, color, and transparency. For instance, Paint does not directly implement dashing or blur, but contains the objects that do so.

Example:

paint = skia.Paint(
    Alphaf=1.0,
    AntiAlias=True,
    Color=skia.ColorBLUE,
    StrokeWidth=2,
    Style=skia.Paint.kStroke_Style,
    )
Paint is implicitly convertible from python dict. It is possible to replace Paint with dict where required:

canvas.drawPaint({'Color': 0xFFFFFFFF})
canvas.drawLine((0, 0), (1, 1), {'Color': 0xFF0000FF})
Classes

Cap

Members:

Join

Members:

Style

Members:

Methods

__init__

Overloaded function.

canComputeFastBounds

(to be made private) Returns true if Paint does not include elements requiring extensive computation to compute BaseDevice bounds of drawn geometry.

computeFastBounds

(to be made private) Only call this if canComputeFastBounds() returned true.

computeFastStrokeBounds

(to be made private)

doComputeFastBounds

(to be made private) Computes the bounds, overriding the Paint Paint.Style.

getAlpha

getAlphaf

Retrieves alpha from the color used when stroking and filling.

getBlendMode

Returns BlendMode.

getColor

Retrieves alpha and RGB, unpremultiplied, packed into 32 bits.

getColor4f

Retrieves alpha and RGB, unpremultiplied, as four floating point values.

getColorFilter

Returns ColorFilter if set, or nullptr.

getFillPath

Returns the filled equivalent of the stroked path.

getImageFilter

Returns ImageFilter if set, or nullptr.

getMaskFilter

Returns MaskFilter if set, or nullptr.

getPathEffect

Returns PathEffect if set, or nullptr.

getShader

Returns optional colors used when filling a path, such as a gradient.

getStrokeCap

Returns the geometry drawn at the beginning and end of strokes.

getStrokeJoin

Returns the geometry drawn at the corners of strokes.

getStrokeMiter

Returns the limit at which a sharp corner is drawn beveled.

getStrokeWidth

Returns the thickness of the pen used by SkPaint to outline the shape.

getStyle

Returns whether the geometry is filled, stroked, or filled and stroked.

isAntiAlias

Returns true if pixels on the active edges of Path may be drawn with partial transparency.

isDither

Returns true if color error may be distributed to smooth color transition.

isSrcOver

Returns true if BlendMode is BlendMode.kSrcOver, the default.

nothingToDraw

Returns true if Paint prevents all drawing; otherwise, the Paint may or may not allow drawing.

refColorFilter

Returns ColorFilter if set, or nullptr.

refImageFilter

Returns ImageFilter if set, or nullptr.

refMaskFilter

Returns MaskFilter if set, or nullptr.

refPathEffect

Returns PathEffect if set, or nullptr.

refShader

Returns optional colors used when filling a path, such as a gradient.

reset

Sets all Paint contents to their initial values.

setARGB

Sets color used when drawing solid fills.

setAlpha

setAlphaf

Replaces alpha, leaving RGB unchanged.

setAntiAlias

Requests, but does not require, that edge pixels draw opaque or with partial transparency.

setBlendMode

Sets BlendMode to mode.

setColor

Sets alpha and RGB used when stroking and filling.

setColor4f

Sets alpha and RGB used when stroking and filling.

setColorFilter

Sets ColorFilter to filter, decreasing RefCnt of the previous ColorFilter.

setDither

Requests, but does not require, to distribute color error.

setImageFilter

Sets ImageFilter to imageFilter, decreasing RefCnt of the previous ImageFilter.

setMaskFilter

Sets MaskFilter to maskFilter, decreasing RefCnt of the previous MaskFilter.

setPathEffect

Sets PathEffect to pathEffect, decreasing RefCnt of the previous PathEffect.

setShader

Sets optional colors used when filling a path, such as a gradient.

setStrokeCap

Sets the geometry drawn at the beginning and end of strokes.

setStrokeJoin

Sets the geometry drawn at the corners of strokes.

setStrokeMiter

Sets the limit at which a sharp corner is drawn beveled.

setStrokeWidth

Sets the thickness of the pen used by the paint to outline the shape.

setStyle

Sets whether the geometry is filled, stroked, or filled and stroked.

Attributes

kBevel_Join

kButt_Cap

kCapCount

kDefault_Cap

kDefault_Join

kFill_Style

kJoinCount

kLast_Cap

kLast_Join

kMiter_Join

kRound_Cap

kRound_Join

kSquare_Cap

kStrokeAndFill_Style

kStroke_Style

kStyleCount

Methods
Paint.__init__(*args, **kwargs)
Overloaded function.

__init__(self: skia.Paint) -> None

Constructs Paint with default values.

__init__(self: skia.Paint, color: skia.Color4f, colorSpace: skia.ColorSpace = None) -> None

Constructs Paint with default values and the given color.

Sets alpha and RGB used when stroking and filling. The color is four floating point values, unpremultiplied. The color values are interpreted as being in the colorSpace. If colorSpace is nullptr, then color is assumed to be in the sRGB color space.

color
:
unpremultiplied RGBA

colorSpace
:
ColorSpace describing the encoding of color

__init__(self: skia.Paint, paint: skia.Paint) -> None

Makes a shallow copy of Paint.

PathEffect, Shader, MaskFilter, ColorFilter, and ImageFilter are shared between the original paint and the copy. Objects containing RefCnt increment their references by one.

The referenced objects PathEffect, Shader, MaskFilter, ColorFilter, and ImageFilter cannot be modified after they are created. This prevents objects with RefCnt from being modified once Paint refers to them.

paint
:
original to copy

__init__(self: skia.Paint, **kwargs) -> None

Constructs Paint with keyword arguments. See setXXX methods for required signatures.

Example:

paint = skia.Paint(
    Alpha=255,
    Alphaf=1.0,
    AntiAlias=True,
    Color=0xFFFFFFFF,
    Color4f=skia.Color4f.FromColor(0xFF00FF00),
    ColorFilter=skia.LumaColorFilter.Make(),
    Dither=False,
    FilterQuality=skia.kMedium_FilterQuality,
    ImageFilter=skia.ImageFilters.Blur(1.0, 1.0),
    MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.),
    PathEffect=skia.DashPathEffect.Make([2., 1.], 0),
    Shader=skia.Shaders.Empty(),
    StrokeCap=skia.Paint.kButt_Cap,
    StrokeJoin=skia.Paint.kMiter_Join,
    StrokeMiter=0,
    StrokeWidth=2,
    Style=skia.Paint.kStroke_Style,
    )
__init__(self: skia.Paint, d: dict) -> None

Constructs Paint from python dict:

d = {
    'Alpha': 255,
    'Alphaf': 1.0,
    'AntiAlias': True,
    'Color': 0xFFFFFFFF,
    'Color4f': skia.Color4f.FromColor(0xFF00FF00),
    'ColorFilter': skia.LumaColorFilter.Make(),
    'Dither': False,
    'FilterQuality': skia.kMedium_FilterQuality,
    'ImageFilter': skia.ImageFilters.Blur(1.0, 1.0),
    'MaskFilter': skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.),
    'PathEffect': skia.DashPathEffect.Make([2., 1.], 0),
    'Shader': skia.Shaders.Empty(),
    'StrokeCap': skia.Paint.kButt_Cap,
    'StrokeJoin': skia.Paint.kMiter_Join,
    'StrokeMiter': 0,
    'StrokeWidth': 2,
    'Style': skia.Paint.kStroke_Style,
}
paint = skia.Paint(d)
Paint.canComputeFastBounds(self: skia.Paint)→ bool
(to be made private) Returns true if Paint does not include elements requiring extensive computation to compute BaseDevice bounds of drawn geometry.

For instance, Paint with PathEffect always returns false.

Returns
:
true if Paint allows for fast computation of bounds

Paint.computeFastBounds(self: skia.Paint, orig: skia.Rect)→ skia.Rect
(to be made private) Only call this if canComputeFastBounds() returned true.

This takes a raw rectangle (the raw bounds of a shape), and adjusts it for stylistic effects in the paint (e.g. stroking). It returns the adjusted bounds that can then be used for Canvas.quickReject() tests.

Parameters
:
orig – geometry modified by Paint when drawn

Returns
:
fast computed bounds

Paint.computeFastStrokeBounds(self: skia.Paint, orig: skia.Rect)→ skia.Rect
(to be made private)

Parameters
:
orig – geometry modified by SkPaint when drawn

Returns
:
fast computed bounds

Paint.doComputeFastBounds(self: skia.Paint, orig: skia.Rect, style: skia.Paint.Style)→ skia.Rect
(to be made private) Computes the bounds, overriding the Paint Paint.Style.

This can be used to account for additional width required by stroking orig, without altering Paint.Style set to fill.

Parameters
:
orig – geometry modified by Paint when drawn

style – overrides Paint.Style

Returns
:
fast computed bounds

Paint.getAlpha(self: skia.Paint)→ int
Paint.getAlphaf(self: skia.Paint)→ float
Retrieves alpha from the color used when stroking and filling.

Returns
:
alpha ranging from zero, fully transparent, to 255, fully opaque

Paint.getBlendMode(self: skia.Paint)→ skia.BlendMode
Returns BlendMode.

By default, returns BlendMode.kSrcOver.

Returns
:
mode used to combine source color with destination color

Paint.getColor(self: skia.Paint)→ int
Retrieves alpha and RGB, unpremultiplied, packed into 32 bits.

Use helpers ColorGetA(), ColorGetR(), ColorGetG(), and ColorGetB() to extract a color component.

Returns
:
unpremultiplied ARGB

Paint.getColor4f(self: skia.Paint)→ skia.Color4f
Retrieves alpha and RGB, unpremultiplied, as four floating point values.

RGB are are extended sRGB values (sRGB gamut, and encoded with the sRGB transfer function).

Returns
:
unpremultiplied RGBA

Paint.getColorFilter(self: skia.Paint)→ SkColorFilter
Returns ColorFilter if set, or nullptr.

Does not alter ColorFilter RefCnt.

Returns
:
ColorFilter if previously set, nullptr otherwise

Paint.getFillPath(self: skia.Paint, src: SkPath, dst: SkPath, cullRect: skia.Rect = None, resScale: float = 1)→ bool
Returns the filled equivalent of the stroked path.

Parameters
:
src – Path read to create a filled version

dst – resulting Path; may be the same as src, but may not be nullptr

cullRect – optional limit passed to PathEffect

resScale – if > 1, increase precision, else if (0 < resScale < 1) reduce precision to favor speed and size

Returns
:
true if the path represents style fill, or false if it represents hairline

Paint.getImageFilter(self: skia.Paint)→ SkImageFilter
Returns ImageFilter if set, or nullptr.

Does not alter ImageFilter RefCnt.

Returns
:
ImageFilter if previously set, nullptr otherwise

Paint.getMaskFilter(self: skia.Paint)→ SkMaskFilter
Returns MaskFilter if set, or nullptr.

Does not alter MaskFilter RefCnt.

Returns
:
MaskFilter if previously set, nullptr otherwise

Paint.getPathEffect(self: skia.Paint)→ SkPathEffect
Returns PathEffect if set, or nullptr.

Does not alter PathEffect RefCnt.

Returns
:
PathEffect if previously set, nullptr otherwise

Paint.getShader(self: skia.Paint)→ SkShader
Returns optional colors used when filling a path, such as a gradient.

Does not alter Shader RefCnt.

Returns
:
Shader if previously set, nullptr otherwise

Paint.getStrokeCap(self: skia.Paint)→ skia.Paint.Cap
Returns the geometry drawn at the beginning and end of strokes.

Paint.getStrokeJoin(self: skia.Paint)→ skia.Paint.Join
Returns the geometry drawn at the corners of strokes.

Paint.getStrokeMiter(self: skia.Paint)→ float
Returns the limit at which a sharp corner is drawn beveled.

Returns
:
zero and greater miter limit

Paint.getStrokeWidth(self: skia.Paint)→ float
Returns the thickness of the pen used by SkPaint to outline the shape.

Returns
:
zero for hairline, greater than zero for pen thickness

Paint.getStyle(self: skia.Paint)→ skia.Paint.Style
Returns whether the geometry is filled, stroked, or filled and stroked.

Paint.isAntiAlias(self: skia.Paint)→ bool
Returns true if pixels on the active edges of Path may be drawn with partial transparency.

Returns
:
antialiasing state

Paint.isDither(self: skia.Paint)→ bool
Returns true if color error may be distributed to smooth color transition.

Returns
:
dithering state

Paint.isSrcOver(self: skia.Paint)→ bool
Returns true if BlendMode is BlendMode.kSrcOver, the default.

Returns
:
true if BlendMode is BlendMode.kSrcOver

Paint.nothingToDraw(self: skia.Paint)→ bool
Returns true if Paint prevents all drawing; otherwise, the Paint may or may not allow drawing.

Returns true if, for example, BlendMode combined with alpha computes a new alpha of zero.

Returns
:
true if Paint prevents all drawing

Paint.refColorFilter(self: skia.Paint)→ SkColorFilter
Returns ColorFilter if set, or nullptr.

Increases ColorFilter RefCnt by one.

Returns
:
ColorFilter if set, or nullptr

Paint.refImageFilter(self: skia.Paint)→ SkImageFilter
Returns ImageFilter if set, or nullptr.

Increases ImageFilter RefCnt by one.

Returns
:
ImageFilter if previously set, nullptr otherwise

Paint.refMaskFilter(self: skia.Paint)→ SkMaskFilter
Returns MaskFilter if set, or nullptr.

Increases MaskFilter RefCnt by one.

Returns
:
MaskFilter if previously set, nullptr otherwise

Paint.refPathEffect(self: skia.Paint)→ SkPathEffect
Returns PathEffect if set, or nullptr.

Increases PathEffect RefCnt by one.

Returns
:
PathEffect if previously set, nullptr otherwise

Paint.refShader(self: skia.Paint)→ SkShader
Returns optional colors used when filling a path, such as a gradient.

Increases Shader RefCnt by one.

Returns
:
Shader if previously set, nullptr otherwise

Paint.reset(self: skia.Paint)→ None
Sets all Paint contents to their initial values.

This is equivalent to replacing Paint with the result of __init__() without arguments.

Paint.setARGB(self: skia.Paint, a: int, r: int, g: int, b: int)→ None
Sets color used when drawing solid fills.

The color components range from 0 to 255. The color is unpremultiplied; alpha sets the transparency independent of RGB.

Parameters
:
a (int) – amount of alpha, from fully transparent (0) to fully opaque (255)

r (int) – amount of red, from no red (0) to full red (255)

g (int) – amount of green, from no green (0) to full green (255)

b (int) – amount of blue, from no blue (0) to full blue (255)

Paint.setAlpha(self: skia.Paint, a: int)→ None
Paint.setAlphaf(self: skia.Paint, a: float)→ None
Replaces alpha, leaving RGB unchanged.

An out of range value triggers an assert in the debug build. a is a value from 0.0 to 1.0. a set to zero makes color fully transparent; a set to 1.0 makes color fully opaque.

Parameters
:
a (float) – alpha component of color

Paint.setAntiAlias(self: skia.Paint, aa: bool)→ None
Requests, but does not require, that edge pixels draw opaque or with partial transparency.

Parameters
:
aa (bool) – setting for antialiasing

Paint.setBlendMode(self: skia.Paint, mode: skia.BlendMode)→ None
Sets BlendMode to mode.

Does not check for valid input.

Parameters
:
mode (skia.BlendMode) – BlendMode used to combine source color and destination

Paint.setColor(self: skia.Paint, color: int)→ None
Sets alpha and RGB used when stroking and filling.

The color is a 32-bit value, unpremultiplied, packing 8-bit components for alpha, red, blue, and green.

Parameters
:
color (int) – unpremultiplied ARGB

Paint.setColor4f(self: skia.Paint, color: skia.Color4f, colorSpace: skia.ColorSpace = None)→ None
Sets alpha and RGB used when stroking and filling.

The color is four floating point values, unpremultiplied. The color values are interpreted as being in the colorSpace. If colorSpace is nullptr, then color is assumed to be in the sRGB color space.

Parameters
:
color (skia.Color4f) – unpremultiplied RGBA

colorSpace (skia.ColorSpace) – ColorSpace describing the encoding of color

Paint.setColorFilter(self: skia.Paint, colorFilter: SkColorFilter)→ None
Sets ColorFilter to filter, decreasing RefCnt of the previous ColorFilter.

Pass nullptr to clear ColorFilter.

Increments filter RefCnt by one.

Parameters
:
colorFilter (skia.ColorFilter) – ColorFilter to apply to subsequent draw

Paint.setDither(self: skia.Paint, dither: bool)→ None
Requests, but does not require, to distribute color error.

Parameters
:
dither (bool) – dither setting for ditering

Paint.setImageFilter(self: skia.Paint, imageFilter: SkImageFilter)→ None
Sets ImageFilter to imageFilter, decreasing RefCnt of the previous ImageFilter.

Pass nullptr to clear ImageFilter, and remove ImageFilter effect on drawing.

Increments imageFilter RefCnt by one.

Parameters
:
imageFilter (skia.ImageFilter) – how Image is sampled when transformed

Paint.setMaskFilter(self: skia.Paint, maskFilter: SkMaskFilter)→ None
Sets MaskFilter to maskFilter, decreasing RefCnt of the previous MaskFilter.

Pass nullptr to clear MaskFilter and leave MaskFilter effect on mask alpha unaltered.

Increments maskFilter RefCnt by one.

Parameters
:
maskFilter (skia.MaskFilter) – modifies clipping mask generated from drawn geometry

Paint.setPathEffect(self: skia.Paint, pathEffect: SkPathEffect)→ None
Sets PathEffect to pathEffect, decreasing RefCnt of the previous PathEffect.

Pass nullptr to leave the path geometry unaltered.

Increments pathEffect RefCnt by one.

Parameters
:
pathEffect (skia.PathEffect) – replace Path with a modification when drawn

Paint.setShader(self: skia.Paint, shader: SkShader)→ None
Sets optional colors used when filling a path, such as a gradient.

Sets Shader to shader, decreasing RefCnt of the previous Shader. Increments shader RefCnt by one.

Parameters
:
shader (skia.Shader) – how geometry is filled with color; if nullptr, color is used instead

Paint.setStrokeCap(self: skia.Paint, cap: skia.Paint.Cap)→ None
Sets the geometry drawn at the beginning and end of strokes.

Paint.setStrokeJoin(self: skia.Paint, join: skia.Paint.Join)→ None
Sets the geometry drawn at the corners of strokes.

Paint.setStrokeMiter(self: skia.Paint, miter: float)→ None
Sets the limit at which a sharp corner is drawn beveled.

Valid values are zero and greater. Has no effect if miter is less than zero.

Parameters
:
miter (float) – zero and greater miter limit

Paint.setStrokeWidth(self: skia.Paint, width: float)→ None
Sets the thickness of the pen used by the paint to outline the shape.

Has no effect if width is less than zero.

Parameters
:
width (float) – zero thickness for hairline; greater than zero for pen thickness

Paint.setStyle(self: skia.Paint, style: skia.Paint.Style)→ None
Sets whether the geometry is filled, stroked, or filled and stroked.

Has no effect if style is not a legal Paint.Style value.

Attributes
Paint.kBevel_Join= <Join.kBevel_Join: 2>
Paint.kButt_Cap= <Cap.kButt_Cap: 0>
Paint.kCapCount= 3
Paint.kDefault_Cap= <Cap.kButt_Cap: 0>
Paint.kDefault_Join= <Join.kMiter_Join: 0>
Paint.kFill_Style= <Style.kFill_Style: 0>
Paint.kJoinCount= 3
Paint.kLast_Cap= <Cap.kSquare_Cap: 2>
Paint.kLast_Join= <Join.kBevel_Join: 2>
Paint.kMiter_Join= <Join.kMiter_Join: 0>
Paint.kRound_Cap= <Cap.kRound_Cap: 1>
Paint.kRound_Join= <Join.kRound_Join: 1>
Paint.kSquare_Cap= <Cap.kSquare_Cap: 2>
Paint.kStrokeAndFill_Style= <Style.kStrokeAndFill_Style: 2>
Paint.kStroke_Style= <Style.kStroke_Style: 1>
Paint.kStyleCount= 3