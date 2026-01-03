import numpy as np
import matplotlib.pyplot as plt

# ---- Rebuild minimal functions ----
def _fade(t): return t*t*t*(t*(t*6 - 15) + 10)
def _lerp(a, b, t): return a + t*(b-a)
def _grad(h, x, y):
    h = h & 7
    u = np.where(h < 4, x, y)
    v = np.where(h < 4, y, x)
    u = np.where((h & 1) == 0, u, -u)
    v = np.where((h & 2) == 0, v, -v)
    return u + v

class Perlin2D:
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        p = np.arange(256, dtype=np.int32)
        rng.shuffle(p)
        self.perm = np.concatenate([p, p]).astype(np.int32)
    def noise(self, x, y):
        xi = np.floor(x).astype(np.int32) & 255
        yi = np.floor(y).astype(np.int32) & 255
        xf = x - np.floor(x)
        yf = y - np.floor(y)
        u = _fade(xf); v = _fade(yf)
        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]
        x1 = _lerp(_grad(aa, xf, yf),     _grad(ba, xf-1, yf),   u)
        x2 = _lerp(_grad(ab, xf, yf-1),   _grad(bb, xf-1, yf-1), u)
        return _lerp(x1, x2, v).astype(np.float32)

def fbm(perlin, x, y, octaves=5, lacunarity=2.0, gain=0.55):
    amp, freq = 1.0, 1.0
    s = np.zeros_like(x, dtype=np.float32)
    norm = 0.0
    for _ in range(octaves):
        s += amp * perlin.noise(x*freq, y*freq)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return s / max(norm, 1e-8)

def norm01(a):
    a = a.astype(np.float32)
    return (a - a.min()) / (a.max() - a.min() + 1e-8)

def box_blur(a, radius=2, passes=1):
    if radius <= 0: return a.astype(np.float32)
    out = a.astype(np.float32)
    k = 2*radius + 1
    for _ in range(passes):
        # horizontal
        c = np.cumsum(out, axis=1, dtype=np.float32)
        left = np.concatenate([np.zeros((out.shape[0],1), np.float32), c[:, :-k]], axis=1)
        right = c[:, k-1:]
        out = (right - left) / k
        padL = np.repeat(out[:, :1], radius, axis=1)
        padR = np.repeat(out[:, -1:], radius, axis=1)
        out = np.concatenate([padL, out, padR], axis=1)
        # vertical
        c = np.cumsum(out, axis=0, dtype=np.float32)
        top = np.concatenate([np.zeros((1,out.shape[1]), np.float32), c[:-k, :]], axis=0)
        bot = c[k-1:, :]
        out = (bot - top) / k
        padT = np.repeat(out[:1, :], radius, axis=0)
        padB = np.repeat(out[-1:, :], radius, axis=0)
        out = np.concatenate([padT, out, padB], axis=0)
    return out

def gaussian_basins(W, H, seed=0, k=10, sigma_px=(65, 150)):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    field = np.zeros((H, W), dtype=np.float32)
    centers = rng.uniform([0,0],[W,H], size=(k,2)).astype(np.float32)
    sigmas = rng.uniform(sigma_px[0], sigma_px[1], size=(k,)).astype(np.float32)
    weights = rng.uniform(0.8, 1.2, size=(k,)).astype(np.float32)
    for (cx, cy), s, w in zip(centers, sigmas, weights):
        dx = xx - cx
        dy = yy - cy
        field += w * np.exp(-(dx*dx + dy*dy) / (2.0*s*s))
    return 1.0 - norm01(field)

def make_C(W, H, seed, basins_k=10, sigma=(65,150), mix_w=0.60, lf_scale=0.0090, lf_oct=5, lf_blur=(5,2), post_blur=(2,1), gamma=1.20):
    per = Perlin2D(seed=seed)
    base = gaussian_basins(W, H, seed=seed+101, k=basins_k, sigma_px=sigma)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = xx * lf_scale
    y = yy * lf_scale
    lf = norm01(fbm(per, x, y, octaves=lf_oct, gain=0.55))
    lf = box_blur(lf, radius=lf_blur[0], passes=lf_blur[1])
    lf = norm01(lf)
    field = norm01(base*mix_w + lf*(1.0-mix_w))
    field = box_blur(field, radius=post_blur[0], passes=post_blur[1])
    field = norm01(field)
    field = np.clip(field, 0, 1) ** gamma
    return field

def bw(field, depth):
    return (field < depth).astype(np.uint8)

# --- Generate depth sweep d=0..1 for the chosen params ---
W, H = 560, 320
seed = 9
params = dict(basins_k=10, sigma=(65,150), mix_w=0.60, lf_scale=0.0090, lf_oct=5, lf_blur=(5,2), post_blur=(2,1), gamma=1.20)
field = make_C(W, H, seed=seed, **params)

depths = np.linspace(0.0, 1.0, 11)
fig, axes = plt.subplots(2, 6, figsize=(18, 6))
axes = axes.flatten()
for idx, d in enumerate(depths):
    ax = axes[idx]
    ax.imshow(bw(field, d), cmap="gray", interpolation="nearest")
    ax.set_title(f"d={d:.1f}")
    ax.axis("off")

# last panel: show grayscale field
axes[-1].imshow(field, cmap="gray", interpolation="nearest")
axes[-1].set_title("field (grayscale)")
axes[-1].axis("off")

plt.suptitle("Depth sweep (d=0..1) for Pipeline C: w=0.60, lf_scale=0.0090")
plt.tight_layout(rect=[0,0,1,0.92])
plt.show()

# --- Write a concise text file (no f-string braces issues) ---
template = """\
Whatabou-style water field (Pipeline C)
======================================

Goal
----
Generate "water" as an isocontour/threshold of a continuous scalar field H(x,y).
A depth slider simply changes the threshold d in [0..1]:
  water(x,y) = (H(x,y) < d)

This produces globally consistent expansion/contraction and natural merging of pools.

Chosen parameter set (from experiments)
--------------------------------------
- Canvas/grid size: W={W}, H={H}
- RNG seed: {seed}
- Base "basins" field:
    k = {basins_k} Gaussians (random centers)
    sigma_px = {sigma}  # typical basin radius in pixels
- Low-frequency fBM field:
    noise = classic Perlin (can be swapped to Simplex)
    lf_scale = {lf_scale}  # sample coords = pixel * lf_scale
    octaves = {lf_oct}
    lacunarity = 2.0
    gain = 0.55
    blur lf: radius={lf_blur_r}, passes={lf_blur_p}
- Mix:
    H = normalize( basins * mix_w + lf_fbm * (1-mix_w) )
    mix_w = {mix_w}  # lower => more fBM influence => more emergent pools
- Post blur:
    blur H: radius={post_blur_r}, passes={post_blur_p}
- Tone curve:
    H = H ** gamma, gamma = {gamma}

Why this works
--------------
- The "basins" term creates a small number of meaningful minima (3–10-ish),
  so pools appear, grow, and merge (no constant 'puddle fringe').
- The low-frequency fBM adds extra saddle structure so new pools can emerge
  as d increases, but heavy blurring keeps it from creating tiny speckle lakes.

Implementation sketch (language-agnostic)
----------------------------------------
1) Build basins field B in [0..1]:
    B(x,y) = 1 - normalize( sum_{i=1..k} w_i * exp(-dist^2/(2*sigma_i^2)) )
   where centers, sigma_i in pixels, and w_i are random.

2) Build low-frequency fBM field F in [0..1]:
    For each octave:
      F += amp * perlin(x*freq, y*freq)
      amp *= gain; freq *= lacunarity
    normalize(F) to [0..1]
    Blur heavily (radius~5, passes~2) and renormalize.

3) Mix + smooth:
    H = normalize( mix_w*B + (1-mix_w)*F )
    Blur lightly (radius~2, passes~1) and renormalize.
    Apply gamma: H = H**gamma

4) Depth slider -> mask:
    waterMask = (H < d)  # d in [0..1]

Notes / knobs
-------------
- More emergent pools: decrease mix_w (e.g. 0.60 -> 0.55)
- Fewer pools: reduce k or increase sigma_px.
- Avoid 'puddle fringe': keep ALL contributing fields band-limited / blurred.
- If you still get tiny isolated lakes at some depths, add a post-threshold
  min-area filter (remove connected components smaller than N pixels).
- Shoreline "goop" can be added later in contour/polygon space (smoothing/jitter)
  instead of adding higher-frequency noise into H (which creates speckle lakes).
"""

content = template.format(
    W=W, H=H, seed=seed,
    basins_k=params["basins_k"], sigma=params["sigma"],
    lf_scale=params["lf_scale"], lf_oct=params["lf_oct"],
    lf_blur_r=params["lf_blur"][0], lf_blur_p=params["lf_blur"][1],
    mix_w=params["mix_w"],
    post_blur_r=params["post_blur"][0], post_blur_p=params["post_blur"][1],
    gamma=params["gamma"]
)

out_path = "/mnt/data/whatabou_water_field_pipeline_C.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(content)

out_path
