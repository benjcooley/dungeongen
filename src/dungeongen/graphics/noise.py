"""Noise functions for procedural generation.

Provides Perlin noise, fractional Brownian motion (fBM), Gaussian basins,
and field processing utilities (blur, normalization).
"""

import numpy as np
from typing import Tuple, Optional


# ============================================================================
# Perlin Noise
# ============================================================================

def _fade(t):
    """Perlin fade function: 6t^5 - 15t^4 + 10t^3"""
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a, b, t):
    """Linear interpolation."""
    return a + t * (b - a)


def _grad(h, x, y):
    """Gradient function for 2D Perlin noise."""
    h = h & 7
    u = np.where(h < 4, x, y)
    v = np.where(h < 4, y, x)
    u = np.where((h & 1) == 0, u, -u)
    v = np.where((h & 2) == 0, v, -v)
    return u + v


class Perlin2D:
    """2D Perlin noise generator."""
    
    def __init__(self, seed: int = 0):
        rng = np.random.default_rng(seed)
        p = np.arange(256, dtype=np.int32)
        rng.shuffle(p)
        self.perm = np.concatenate([p, p]).astype(np.int32)
    
    def noise(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Sample Perlin noise at (x, y) coordinates.
        
        Args:
            x: X coordinates (can be scalar or array)
            y: Y coordinates (can be scalar or array)
            
        Returns:
            Noise values in approximately [-1, 1] range
        """
        x = np.asarray(x, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)
        
        xi = np.floor(x).astype(np.int32) & 255
        yi = np.floor(y).astype(np.int32) & 255
        xf = x - np.floor(x)
        yf = y - np.floor(y)
        
        u = _fade(xf)
        v = _fade(yf)
        
        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]
        
        x1 = _lerp(_grad(aa, xf, yf), _grad(ba, xf - 1, yf), u)
        x2 = _lerp(_grad(ab, xf, yf - 1), _grad(bb, xf - 1, yf - 1), u)
        
        return _lerp(x1, x2, v).astype(np.float32)


# ============================================================================
# Fractional Brownian Motion (fBM)
# ============================================================================

def fbm(
    perlin: Perlin2D,
    x: np.ndarray,
    y: np.ndarray,
    octaves: int = 5,
    lacunarity: float = 2.0,
    gain: float = 0.55
) -> np.ndarray:
    """Fractional Brownian motion - layered Perlin noise.
    
    Args:
        perlin: Perlin2D noise generator
        x, y: Coordinate arrays
        octaves: Number of noise layers
        lacunarity: Frequency multiplier per octave
        gain: Amplitude multiplier per octave (persistence)
        
    Returns:
        fBM noise values, normalized to sum of amplitudes
    """
    amp, freq = 1.0, 1.0
    result = np.zeros_like(x, dtype=np.float32)
    norm = 0.0
    
    for _ in range(octaves):
        result += amp * perlin.noise(x * freq, y * freq)
        norm += amp
        amp *= gain
        freq *= lacunarity
    
    return result / max(norm, 1e-8)


# ============================================================================
# Gaussian Basins Field
# ============================================================================

def gaussian_basins(
    width: int,
    height: int,
    seed: int = 0,
    num_basins: int = 10,
    sigma_range: Tuple[float, float] = (65, 150),
    weight_range: Tuple[float, float] = (0.8, 1.2)
) -> np.ndarray:
    """Generate a field with Gaussian basin minima.
    
    Creates random Gaussian "dips" that serve as natural pool centers.
    Lower values = deeper basins = more likely to be water.
    
    Args:
        width, height: Field dimensions in pixels
        seed: Random seed
        num_basins: Number of Gaussian centers (k)
        sigma_range: (min, max) radius of basins in pixels
        weight_range: (min, max) weight multiplier for each basin
        
    Returns:
        Field in [0, 1] where lower values are basin centers
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    
    field = np.zeros((height, width), dtype=np.float32)
    
    # Random basin centers, sizes, and weights
    centers = rng.uniform([0, 0], [width, height], size=(num_basins, 2)).astype(np.float32)
    sigmas = rng.uniform(sigma_range[0], sigma_range[1], size=(num_basins,)).astype(np.float32)
    weights = rng.uniform(weight_range[0], weight_range[1], size=(num_basins,)).astype(np.float32)
    
    for (cx, cy), sigma, weight in zip(centers, sigmas, weights):
        dx = xx - cx
        dy = yy - cy
        field += weight * np.exp(-(dx * dx + dy * dy) / (2.0 * sigma * sigma))
    
    # Invert and normalize: high Gaussian values become low basin values
    return 1.0 - normalize(field)


# ============================================================================
# Field Processing Utilities
# ============================================================================

def normalize(field: np.ndarray) -> np.ndarray:
    """Normalize field to [0, 1] range."""
    field = field.astype(np.float32)
    fmin, fmax = field.min(), field.max()
    if fmax - fmin < 1e-8:
        return np.zeros_like(field)
    return (field - fmin) / (fmax - fmin)


def box_blur(
    field: np.ndarray,
    radius: int = 2,
    passes: int = 1
) -> np.ndarray:
    """Apply box blur to a 2D field.
    
    Multiple passes of box blur approximate Gaussian blur.
    
    Args:
        field: 2D array to blur
        radius: Blur radius in pixels
        passes: Number of blur passes (more = smoother)
        
    Returns:
        Blurred field
    """
    if radius <= 0:
        return field.astype(np.float32)
    
    out = field.astype(np.float32)
    k = 2 * radius + 1
    
    for _ in range(passes):
        # Horizontal pass
        c = np.cumsum(out, axis=1, dtype=np.float32)
        left = np.concatenate([np.zeros((out.shape[0], 1), np.float32), c[:, :-k]], axis=1)
        right = c[:, k-1:]
        out = (right - left) / k
        
        # Pad edges
        pad_l = np.repeat(out[:, :1], radius, axis=1)
        pad_r = np.repeat(out[:, -1:], radius, axis=1)
        out = np.concatenate([pad_l, out, pad_r], axis=1)
        
        # Vertical pass
        c = np.cumsum(out, axis=0, dtype=np.float32)
        top = np.concatenate([np.zeros((1, out.shape[1]), np.float32), c[:-k, :]], axis=0)
        bot = c[k-1:, :]
        out = (bot - top) / k
        
        # Pad edges
        pad_t = np.repeat(out[:1, :], radius, axis=0)
        pad_b = np.repeat(out[-1:, :], radius, axis=0)
        out = np.concatenate([pad_t, out, pad_b], axis=0)
    
    return out


def apply_gamma(field: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """Apply gamma correction to field values.
    
    Args:
        field: Field values in [0, 1]
        gamma: Gamma value (>1 darkens midtones, <1 brightens)
        
    Returns:
        Gamma-corrected field
    """
    return np.clip(field, 0, 1) ** gamma

