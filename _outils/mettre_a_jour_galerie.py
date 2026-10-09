"""
════════════════════════════════════════════════════════════════
  MISE À JOUR DE LA GALERIE CACHANAX

  Lit le dossier OneDrive « Photos » (une catégorie > un dossier
  par bijou) et régénère :
    - les photos du site (img/...), redimensionnées et allégées
    - js/bijoux.js   (le catalogue)
    - js/selection.js (le carrousel « mise en avant »)

  Dans chaque dossier de bijou, un fichier « infos.txt » contient
  le titre, la description, etc. Il est créé automatiquement
  la première fois : il suffit ensuite de le modifier.

  Lancement : double-clic sur « Mettre à jour la galerie.bat »
  Simulation (ne modifie rien) : python mettre_a_jour_galerie.py --test
════════════════════════════════════════════════════════════════
"""

import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Il manque la bibliothèque Pillow. Lancez : python -m pip install Pillow")
    input("Appuyez sur Entrée pour fermer...")
    sys.exit(1)

# ── Réglages ─────────────────────────────────────────────────────
DEPOT = Path(__file__).resolve().parent.parent           # ...\GitHub\Cachanax
PHOTOS = DEPOT.parent.parent / "Photos"                   # ...\Cachanax\Photos

# Catégories affichées, dans l'ordre des boutons de filtre
CATEGORIES = ["Colliers", "Bracelets", "Boucles d'oreilles", "Parures", "Divers"]
# Dossiers de Photos jamais publiés
EXCLUES = ["Expos", "Noël", "Montres"]

MAX_PHOTOS = 5          # photos par bijou
TAILLE_MAX = 1200       # plus grand côté, en pixels
QUALITE = 82            # qualité JPEG
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

FICHE = "infos.txt"
ETAT = Path(__file__).resolve().parent / "etat_galerie.json"
BIJOUX_JS = DEPOT / "js" / "bijoux.js"
SELECTION_JS = DEPOT / "js" / "selection.js"
IMG = DEPOT / "img"

TEST = "--test" in sys.argv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ── Outils ───────────────────────────────────────────────────────
def slug(texte):
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def tri_naturel(nom):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", nom)]


def titre_par_defaut(dossier):
    t = re.sub(r"^BO\s+", "", dossier.strip(), flags=re.I)
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:]


def oui(valeur):
    return str(valeur).strip().lower() in ("oui", "o", "yes", "x", "1", "true")


def lire_texte(chemin):
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return chemin.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return chemin.read_text(encoding="utf-8", errors="replace")


def lire_fiche(chemin):
    """titre / disponible / vedette / afficher sur une ligne chacun,
    puis « description: » suivie du texte (sur une ou plusieurs lignes)."""
    infos, desc, dans_desc = {}, [], False
    for ligne in lire_texte(chemin).splitlines():
        if dans_desc:
            desc.append(ligne)
            continue
        if ligne.strip().startswith("#") or ":" not in ligne:
            continue
        cle, valeur = ligne.split(":", 1)
        cle = slug(cle)
        if cle == "description":
            dans_desc = True
            if valeur.strip():
                desc.append(valeur.strip())
        else:
            infos[cle] = valeur.strip()
    infos["description"] = "\n".join(desc).strip()
    return infos


def ecrire_fiche(chemin, titre, disponible="non", vedette="non", afficher="oui", description=""):
    contenu = (
        "# Fiche du bijou pour le site cachanax.com\n"
        "# disponible / vedette / afficher : oui ou non\n"
        "#   vedette  = mis en avant dans le carrousel de la galerie\n"
        "#   afficher = non pour le retirer du site sans toucher aux photos\n"
        "# La description s'écrit sous la ligne « description: »\n"
        "\n"
        f"titre: {titre}\n"
        f"disponible: {disponible}\n"
        f"vedette: {vedette}\n"
        f"afficher: {afficher}\n"
        "description:\n"
        f"{description}\n"
    )
    if not TEST:
        chemin.write_text(contenu, encoding="utf-8")


def ancien_catalogue():
    """Lit le js/bijoux.js actuel (sert uniquement au tout premier lancement)."""
    if not BIJOUX_JS.exists():
        return {}
    texte = lire_texte(BIJOUX_JS)
    debut = texte.find("[", texte.find("const bijoux"))
    fin = texte.rfind("]")
    try:
        return {b["id"]: b for b in json.loads(texte[debut:fin + 1], strict=False)}
    except Exception as e:
        print(f"Attention : impossible de lire l'ancien js/bijoux.js ({e})")
        return {}


def photos_source(dossier):
    fichiers = [f for f in dossier.iterdir()
                if f.is_file() and f.suffix.lower() in EXTENSIONS]
    fichiers.sort(key=lambda f: tri_naturel(f.name))
    return fichiers[:MAX_PHOTOS]


def empreinte(fichiers):
    return [[f.name, f.stat().st_size, int(f.stat().st_mtime)] for f in fichiers]


def preparer_photos(sources, cible):
    if TEST:
        return
    if cible.exists():
        shutil.rmtree(cible)
    cible.mkdir(parents=True)
    for i, src in enumerate(sources, 1):
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                fond = Image.new("RGB", im.size, (255, 255, 255))
                fond.paste(im, mask=im.convert("RGBA").split()[-1])
                im = fond
            im.thumbnail((TAILLE_MAX, TAILLE_MAX), Image.LANCZOS)
            im.save(cible / f"{i}.jpg", "JPEG", quality=QUALITE,
                    optimize=True, progressive=True)


def chemin_web(p):
    return p.relative_to(DEPOT).as_posix()


# ── Programme ────────────────────────────────────────────────────
def main():
    if not PHOTOS.is_dir():
        print(f"Dossier Photos introuvable : {PHOTOS}")
        return
    if TEST:
        print("*** SIMULATION : aucun fichier ne sera modifié ***\n")

    premier_lancement = not ETAT.exists()
    etat = {} if premier_lancement else json.loads(ETAT.read_text(encoding="utf-8"))
    ancien = ancien_catalogue() if premier_lancement else {}
    if premier_lancement and BIJOUX_JS.exists() and not ancien:
        print("Arrêt : le catalogue actuel n'a pas pu être repris, rien n'a été modifié.")
        return

    cats = [c.name for c in PHOTOS.iterdir() if c.is_dir() and c.name not in EXCLUES]
    inconnues = sorted(set(cats) - set(CATEGORIES), key=tri_naturel)
    ordre = [c for c in CATEGORIES if c in cats] + inconnues

    bijoux, vedettes, nouvelles_fiches, masques, sans_photo = [], [], [], [], []
    traites = adoptes = 0
    nouvel_etat = {}

    for cat in ordre:
        dossiers = sorted((d for d in (PHOTOS / cat).iterdir() if d.is_dir()),
                          key=lambda d: tri_naturel(d.name))
        for d in dossiers:
            ident = f"{slug(cat)}--{slug(d.name)}"
            fiche = d / FICHE

            if not fiche.exists():
                vieux = ancien.get(ident)
                if vieux:
                    ecrire_fiche(fiche, vieux.get("titre") or titre_par_defaut(d.name),
                                 "oui" if oui(vieux.get("disponible")) else "non",
                                 "non", "oui", vieux.get("desc", ""))
                else:
                    # Au premier lancement, une pièce absente du site actuel reste masquée
                    afficher = "non" if premier_lancement else "oui"
                    ecrire_fiche(fiche, titre_par_defaut(d.name), afficher=afficher)
                    nouvelles_fiches.append((f"{cat} / {d.name}", afficher))
                infos = ({"titre": vieux.get("titre"), "disponible": vieux.get("disponible"),
                          "afficher": "oui", "description": vieux.get("desc", "")}
                         if vieux else
                         {"titre": titre_par_defaut(d.name),
                          "afficher": "non" if premier_lancement else "oui"})
            else:
                infos = lire_fiche(fiche)

            if not oui(infos.get("afficher", "oui")):
                masques.append(f"{cat} / {d.name}")
                continue

            sources = photos_source(d)
            if not sources:
                sans_photo.append(f"{cat} / {d.name}")
                continue

            cible = IMG / slug(cat) / slug(d.name)
            emp = empreinte(sources)
            deja = etat.get(ident)

            if deja and deja["sources"] == emp and all((DEPOT / p).exists() for p in deja["photos"]):
                photos = deja["photos"]
            elif premier_lancement and ident in ancien and all(
                    (DEPOT / p).exists() for p in ancien[ident]["photos"]):
                photos = ancien[ident]["photos"]          # on garde les photos déjà en ligne
                adoptes += 1
            else:
                preparer_photos(sources, cible)
                photos = [chemin_web(cible / f"{i}.jpg") for i in range(1, len(sources) + 1)]
                traites += 1
                print(f"  photos préparées : {cat} / {d.name} ({len(sources)})")

            nouvel_etat[ident] = {"sources": emp, "photos": photos}
            bijoux.append({
                "id": ident,
                "titre": infos.get("titre") or titre_par_defaut(d.name),
                "categorie": cat,
                "dossier": d.name,
                "vignette": photos[0],
                "photos": photos,
                "disponible": "oui" if oui(infos.get("disponible", "non")) else "non",
                "desc": infos.get("description", ""),
            })
            if oui(infos.get("vedette", "non")):
                vedettes.append(d.name)

    # Pièces retirées depuis la dernière fois : on supprime leurs photos du site
    retires = [i for i in etat if i not in nouvel_etat]
    for ident in retires:
        for p in etat[ident]["photos"][:1]:
            dossier = (DEPOT / p).parent
            if not TEST and dossier.is_dir() and IMG in dossier.parents:
                shutil.rmtree(dossier)

    # ── Écriture des fichiers du site ──
    if not TEST:
        entete = (
            "/*\n  CATALOGUE DES BIJOUX — FICHIER GÉNÉRÉ AUTOMATIQUEMENT, ne pas modifier.\n"
            "  Pour changer un titre, une description ou la disponibilité :\n"
            "  modifiez le fichier infos.txt du bijou dans OneDrive > Cachanax > Photos,\n"
            "  puis relancez « Mettre à jour la galerie ».\n*/\n"
        )
        BIJOUX_JS.write_text(entete + "const bijoux = "
                             + json.dumps(bijoux, ensure_ascii=False, indent=2) + ";\n",
                             encoding="utf-8")
        sel = "".join(f"  {json.dumps(v, ensure_ascii=False)},\n" for v in vedettes)
        SELECTION_JS.write_text(
            "/*\n  SÉLECTION MISE EN AVANT — FICHIER GÉNÉRÉ AUTOMATIQUEMENT, ne pas modifier.\n"
            "  Pour mettre un bijou en avant : « vedette: oui » dans son infos.txt.\n"
            "  Sans aucune vedette, le carrousel affiche 20 pièces au hasard.\n*/\n"
            f"const selection = [\n{sel}];\n", encoding="utf-8")
        ETAT.write_text(json.dumps(nouvel_etat, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── Compte rendu ──
    print("\n════════ Compte rendu ════════")
    print(f"Bijoux en ligne : {len(bijoux)}"
          f"  (dont {sum(b['disponible'] == 'oui' for b in bijoux)} disponibles,"
          f" {len(vedettes)} en vedette)")
    print(f"Photos préparées : {traites} bijou(x)")
    if adoptes:
        print(f"Photos déjà en ligne conservées telles quelles : {adoptes} bijou(x)")
    if retires:
        print(f"Retirés du site : {len(retires)}")
        for r in retires:
            print(f"   - {r}")
    if nouvelles_fiches:
        print(f"\nFiches infos.txt créées : {len(nouvelles_fiches)}")
        for nom, aff in nouvelles_fiches:
            print(f"   - {nom}" + ("   (masqué : mettez « afficher: oui » pour le publier)"
                                   if aff == "non" else ""))
    if masques:
        print(f"\nMasqués (afficher: non) : {len(masques)}")
    if sans_photo:
        print("\nDossiers sans photo, ignorés :")
        for s in sans_photo:
            print(f"   - {s}")
    if inconnues:
        print(f"\nNouvelle(s) catégorie(s) publiée(s) : {', '.join(inconnues)}")
    if TEST:
        print("\n*** SIMULATION : rien n'a été modifié ***")
    else:
        print("\nTerminé. Dans GitHub Desktop : vérifiez, « Commit », puis « Push origin ».")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nErreur : {e}")
        raise
    finally:
        if sys.stdin.isatty() and "--sans-pause" not in sys.argv:
            input("\nAppuyez sur Entrée pour fermer...")
