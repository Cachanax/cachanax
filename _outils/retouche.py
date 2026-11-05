"""
Retouche automatique des photos de la galerie Cachanax.

  vignette(photo, choix) : prépare la 1re photo dans le passe-partout rose
  autre_photo(photo)     : corrige couleurs et lumière des photos suivantes

  choix : auto, detoure, corrige ou origine (ligne « vignette: » de infos.txt)
  Les photos d'origine ne sont jamais modifiées.
"""

import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageOps
from rembg import new_session, remove

TAILLE = 1200                 # côté de la vignette, en pixels
TAILLE_TRAVAIL = 3000         # plus grand côté utilisé pour le détourage
PLACE_BIJOU = 0.70            # part du cadre occupée par le bijou détouré
CREME = np.array([250, 245, 242.0])
ROSE_PALE = np.array([249, 214, 227.0])
ROSE = np.array([212, 83, 126.0])
BORDEAUX = (75, 21, 40)

_session = None
_fond = None


def _masque(im):
    global _session
    if _session is None:
        _session = new_session("isnet-general-use")
    return np.asarray(remove(im, session=_session, only_mask=True))


def _balance(a, al):
    px = a[al < 40]
    if len(px) < 500:
        return np.ones(3)
    m = np.median(px, 0)
    if (m.max() - m.min()) / max(m.max(), 1) > 0.22:
        return np.ones(3)          # fond coloré ou peau : on ne touche pas aux couleurs
    return np.clip(m.mean() / np.maximum(m, 1), 0.88, 1.14)


def _lumiere(a, al, cible=150):
    px = a[al > 128]
    if len(px) < 200:
        return a
    y = np.median(px.mean(1))
    g = np.clip(np.log(cible / 255) / np.log(max(y, 20) / 255), 0.85, 1.18)
    return 255 * (a / 255) ** g


def _corrige(im, al):
    a = np.asarray(im).astype(float)
    a = np.clip(a * _balance(a, al), 0, 255)
    return np.clip(_lumiere(a, al), 0, 255).astype(np.uint8)


def _renforce(rgb, al):
    """Sur fond uni, récupère les parties fines oubliées par le détourage."""
    h, w = al.shape
    b = max(8, min(h, w) // 14)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    bord = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3),
                           lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    if np.percentile(bord[:, 0], 90) - np.percentile(bord[:, 0], 10) > 38:
        return al
    s = max(24, min(h, w) // 18)
    libre = (cv2.dilate((al > 25).astype(np.uint8), np.ones((15, 15))) == 0).astype(np.float32)
    if libre.mean() < 0.2:
        return al
    den = cv2.GaussianBlur(libre, (0, 0), s) + 1e-4
    fond = cv2.GaussianBlur(lab * libre[..., None], (0, 0), s) / den[..., None]
    d = lab - fond
    c = ((np.hypot(d[..., 1], d[..., 2]) > 13) | (np.abs(d[..., 0]) > 42)).astype(np.uint8)
    c = cv2.morphologyEx(c, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    nb, etq, st, _ = cv2.connectedComponentsWithStats(c, 8)
    garde = np.zeros_like(c)
    for i in range(1, nb):
        x, y, lg, ht, aire = st[i]
        if aire >= h * w * 0.00025 and x > 2 and y > 2 and x + lg < w - 2 and y + ht < h - 2:
            garde[etq == i] = 1
    res = np.maximum(al.astype(np.float32), cv2.GaussianBlur(garde.astype(np.float32) * 255, (0, 0), 0.8))
    gain = ((res > 128).sum() - (al > 128).sum()) / max((al > 128).sum(), 1)
    return res.astype(np.uint8) if gain < 1.2 else al


def _nettoie(al):
    """Retire les restes isolés : taches pâles ou petits points loin du bijou."""
    al = al.copy()
    al[al < 30] = 0
    nb, etq, st, _ = cv2.connectedComponentsWithStats((al > 128).astype(np.uint8), 8)
    if nb > 1:
        grand = st[1:, 4].max()
        for i in range(1, nb):
            if st[i, 4] < max(30, grand * 0.002):
                al[etq == i] = 0
    nb, etq, st, _ = cv2.connectedComponentsWithStats((al > 30).astype(np.uint8), 8)
    if nb < 3:
        return al
    grand = st[1:, 4].max()
    corps = np.isin(etq, [i for i in range(1, nb) if st[i, 4] >= grand * 0.005]).astype(np.uint8)
    r = max(3, int(max(al.shape) * 0.03))
    pres = cv2.dilate(corps, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    for i in range(1, nb):
        m = etq == i
        if al[m].max() < 175 or (st[i, 4] < grand * 0.005 and not pres[m].any()):
            al[m] = 0
    return al


def _peau(rgb):
    y = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
    return (y[..., 1] > 135) & (y[..., 1] < 172) & (y[..., 2] > 85) & (y[..., 2] < 128) & (y[..., 0] > 60)


def _detourage_fiable(rgb, al):
    o = al > 128
    if o.sum() <= 500:
        return False
    part = float(o.mean())
    flou = float(((al > 30) & (al < 220)).sum() / o.sum())
    bord = float(np.concatenate([o[0], o[-1], o[:, 0], o[:, -1]]).mean())
    return 0.02 < part < 0.72 and flou < 0.55 and bord < 0.10 and float(_peau(rgb).mean()) < 0.28


def _cadre():
    global _fond
    if _fond is None:
        N = TAILLE
        flou = lambda m, s: cv2.GaussianBlur(m.astype(np.float32), (0, 0), s)
        q, q2, ep = int(N * 0.055), int(N * 0.08), max(2, round(N / 450))
        pp = np.zeros((N, N), np.uint8)
        cv2.rectangle(pp, (q, q), (N - q, N - q), 1, -1)
        fond = ROSE_PALE + (CREME - ROSE_PALE) * flou(pp, 2.5)[..., None]
        filet = np.zeros((N, N), np.uint8)
        cv2.rectangle(filet, (q2, q2), (N - q2, N - q2), 1, ep)
        f = flou(filet, 0.9)[..., None] * 0.75
        _fond = Image.fromarray((fond * (1 - f) + ROSE * f).astype(np.uint8))
    return _fond.copy()


def _interieur():
    return TAILLE - 2 * (int(TAILLE * 0.08) + int(TAILLE * 0.014))


def _ombre(c, al, pos, dx, dy, flou, force):
    s = Image.new("L", c.size, 0)
    s.paste(al, (pos[0] + dx, pos[1] + dy))
    s = s.filter(ImageFilter.GaussianBlur(flou)).point(lambda v: int(v * force))
    c.paste(Image.new("RGB", c.size, BORDEAUX), (0, 0), s)


def _modele(im, force=0.55):
    lab = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0]
    for rayon, k in ((10, force), (2.2, force * 0.45)):
        L = L + k * (L - cv2.GaussianBlur(L, (0, 0), rayon))
    lab[..., 0] = np.clip(L, 0, 255)
    return Image.fromarray(cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB))


def _en_detoure(rgb, al):
    ys, xs = np.where(al > 60)
    zone = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    bijou, alpha = Image.fromarray(rgb).crop(zone), Image.fromarray(al).crop(zone)
    k = TAILLE * PLACE_BIJOU / max(bijou.size)
    t = (max(1, round(bijou.width * k)), max(1, round(bijou.height * k)))
    bijou, alpha = bijou.resize(t, Image.LANCZOS), alpha.resize(t, Image.LANCZOS)
    pos = ((TAILLE - t[0]) // 2, (TAILLE - t[1]) // 2)
    c = _cadre()
    _ombre(c, alpha, pos, 26, 38, 24, 0.34)
    _ombre(c, alpha, pos, 6, 9, 6, 0.42)
    c.paste(_modele(bijou), pos, alpha)
    return c


def _en_photo(im, al=None):
    """Photo dans le cadre : carré autour du bijou s'il y tient, sinon photo entière."""
    if al is not None:
        h, w = al.shape
        m = min(h, w)
        ys, xs = np.where(al > 128)
        if len(xs) and max(xs.max() - xs.min(), ys.max() - ys.min()) <= m * 0.97:
            g = int(np.clip((xs.min() + xs.max()) / 2 - m / 2, 0, w - m))
            t = int(np.clip((ys.min() + ys.max()) / 2 - m / 2, 0, h - m))
            im = im.crop((g, t, g + m, t + m))
    k = _interieur() / max(im.size)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    c = _cadre()
    c.paste(im, ((TAILLE - im.width) // 2, (TAILLE - im.height) // 2))
    return c


def vignette(photo, choix="auto"):
    """Renvoie (image, version retenue) pour la 1re photo d'un bijou."""
    im = ImageOps.exif_transpose(photo).convert("RGB")
    im.thumbnail((TAILLE_TRAVAIL, TAILLE_TRAVAIL), Image.LANCZOS)
    if choix == "origine":
        return _en_photo(im), "origine"
    al0 = _masque(im)
    al = _nettoie(_renforce(np.asarray(im), al0))
    rgb = _corrige(im, al0)
    if choix == "corrige" or not (al > 128).any():
        return _en_photo(Image.fromarray(rgb), al), "corrige"
    if choix == "auto" and not _detourage_fiable(np.asarray(im), al):
        return _en_photo(Image.fromarray(rgb), al), "corrige"
    return _en_detoure(rgb, al), "detoure"


def autre_photo(photo, taille_max):
    """Corrige couleurs et lumière, sans changer le cadrage."""
    im = ImageOps.exif_transpose(photo).convert("RGB")
    im.thumbnail((taille_max, taille_max), Image.LANCZOS)
    return Image.fromarray(_corrige(im, _masque(im)))
