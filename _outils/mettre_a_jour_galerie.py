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

  Les photos du site sont retouchées automatiquement (retouche.py) :
  vignette dans le passe-partout, couleurs et lumière corrigées.
  Réglage par bijou dans infos.txt, ligne « vignette: ».

  Réseaux sociaux : la ligne « publier: nouveau » ou « publier: noel »
  d'un infos.txt place la pièce dans Cachanax > Publications > a_publier.json.
  Dans le dossier Noël, seuls les sous-dossiers comptent.

  Lancement : double-clic sur « Mettre à jour la galerie.bat »
  Simulation (ne modifie rien) : python mettre_a_jour_galerie.py --test
════════════════════════════════════════════════════════════════
"""

import json
import re
import shutil
import sys
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Il manque des outils : lancez d'abord « Installer les outils.bat ».")
    input("Appuyez sur Entrée pour fermer...")
    sys.exit(1)

# ── Réglages ─────────────────────────────────────────────────────
DEPOT = Path(__file__).resolve().parent.parent           # ...\GitHub\Cachanax
PHOTOS = DEPOT.parent.parent / "Photos"                   # ...\Cachanax\Photos

# Catégories affichées, dans l'ordre des boutons de filtre
CATEGORIES = ["Colliers", "Bracelets", "Boucles d'oreilles", "Parures", "Divers", "Noël"]
# Dossiers de Photos jamais publiés
EXCLUES = ["Expos", "Montres"]

MAX_PHOTOS = 5          # photos par bijou
TAILLE_MAX = 1200       # plus grand côté, en pixels
QUALITE = 88            # qualité JPEG
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

CHOIX_VIGNETTE = ("auto", "detoure", "corrige", "origine")

FICHE = "infos.txt"
ETAT = Path(__file__).resolve().parent / "etat_galerie.json"
BIJOUX_JS = DEPOT / "js" / "bijoux.js"
SELECTION_JS = DEPOT / "js" / "selection.js"
IMG = DEPOT / "img"

# Réseaux sociaux : hors du dépôt, donc jamais envoyé sur GitHub
PUBLICATIONS = PHOTOS.parent / "Publications"
A_PUBLIER = PUBLICATIONS / "a_publier.json"
JOURNAL = PUBLICATIONS / "journal_publications.json"
PHOTOS_PUBLI = PUBLICATIONS / "photos"
HORS_SITE_PUBLIABLES = []              # catégories hors site, mais publiables
SITE_WEB = "https://cachanax.com/"
TAGS = {"non": None, "": None, "nouveau": "nouveau", "nouveaute": "nouveau",
        "nouvelle": "nouveau", "noel": "noel"}

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
            # « publier: » ajouté en fin de fichier ne doit pas finir dans la description
            tag = re.match(r"\s*publier\s*:(.*)$", ligne, flags=re.I)
            if tag:
                infos["publier"] = tag.group(1).strip()
                continue
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


def choix_vignette(infos):
    choix = slug(infos.get("vignette", "auto"))
    return choix if choix in CHOIX_VIGNETTE else "auto"


FICHES_COMPLETEES = []


def completer_fiche(chemin):
    """Ajoute « publier: non » aux fiches qui n'ont pas encore cette ligne,
    juste avant « description: ». Le reste de la fiche n'est pas touché."""
    texte = lire_texte(chemin)
    if re.search(r"^\s*publier\s*:", texte, flags=re.I | re.M):
        return
    lignes = texte.splitlines()
    pos = next((i for i, l in enumerate(lignes) if re.match(r"\s*description\s*:", l, flags=re.I)),
               len(lignes))
    lignes.insert(pos, "publier: non")
    aide = "# publier : nouveau, noel ou non (réseaux sociaux)"
    if aide not in lignes:
        com = [i for i, l in enumerate(lignes[:pos]) if l.startswith("#")]
        if com:
            lignes.insert(com[-1] + 1, aide)
    if not TEST:
        avec_reprises(chemin.write_text, "\n".join(lignes) + "\n", "utf-8")
    FICHES_COMPLETEES.append(chemin)


def ecrire_fiche(chemin, titre, disponible="non", vedette="non", afficher="oui", description=""):
    contenu = (
        "# Fiche du bijou pour le site cachanax.com\n"
        "# disponible / vedette / afficher : oui ou non\n"
        "#   vedette  = mis en avant dans le carrousel de la galerie\n"
        "#   afficher = non pour le retirer du site sans toucher aux photos\n"
        "# vignette : auto, detoure, corrige ou origine\n"
        "#   auto = détourée si le résultat est fiable, sinon photo corrigée dans le cadre\n"
        "# publier : nouveau, noel ou non (réseaux sociaux)\n"
        "# La description s'écrit sous la ligne « description: »\n"
        "\n"
        f"titre: {titre}\n"
        f"disponible: {disponible}\n"
        f"vedette: {vedette}\n"
        f"afficher: {afficher}\n"
        "vignette: auto\n"
        "publier: non\n"
        "description:\n"
        f"{description}\n"
    )
    if not TEST:
        chemin.write_text(contenu, encoding="utf-8")


def ecrire_fiche_hors_site(chemin, titre):
    contenu = (
        "# Fiche de la pièce pour Instagram et Facebook (elle n'apparaît pas sur le site)\n"
        "# publier : noel, nouveau ou non\n"
        "# disponible : non pour l'écarter des publications\n"
        "# La description s'écrit sous la ligne « description: »\n"
        "\n"
        f"titre: {titre}\n"
        "disponible: oui\n"
        "publier: non\n"
        "description:\n"
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


def empreinte(fichiers, choix):
    return [[f.name, f.stat().st_size, int(f.stat().st_mtime)] for f in fichiers] + [choix]


def avec_reprises(action, *args):
    """OneDrive peut verrouiller un fichier un instant pendant la synchronisation."""
    for essai in range(6):
        try:
            return action(*args)
        except PermissionError:
            if essai == 5:
                raise
            time.sleep(2)


def preparer_photos(sources, cible, choix, retouche):
    """Retouche les photos d'un bijou et renvoie la version retenue pour la vignette.
    Le travail se fait hors de OneDrive, puis les fichiers sont remplacés un par un :
    le dossier du bijou n'est jamais supprimé, il peut être verrouillé par OneDrive."""
    if TEST:
        return "simulation"
    version = None
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        for i, src in enumerate(sources, 1):
            with Image.open(src) as im:
                if i == 1:
                    sortie, version = retouche.vignette(im, choix)
                else:
                    sortie = retouche.autre_photo(im, TAILLE_MAX)
            sortie.save(temp / f"{i}.jpg", "JPEG", quality=QUALITE, optimize=True, progressive=True)
        cible.mkdir(parents=True, exist_ok=True)
        for f in sorted(temp.iterdir()):
            avec_reprises(shutil.copyfile, f, cible / f.name)
    gardes = {f"{i}.jpg" for i in range(1, len(sources) + 1)}
    for f in cible.glob("*.jpg"):
        if f.name not in gardes:
            avec_reprises(f.unlink)
    return version


def retirer_dossier(dossier):
    """Une pièce retirée du site : un dossier verrouillé n'arrête pas la mise à jour."""
    try:
        for f in dossier.glob("*"):
            avec_reprises(f.unlink)
        avec_reprises(dossier.rmdir)
    except OSError:
        print(f"Attention : dossier à supprimer plus tard : {dossier}")


def chemin_web(p):
    return p.relative_to(DEPOT).as_posix()


# ── Réseaux sociaux ──────────────────────────────────────────────
def lire_json(chemin, defaut):
    return json.loads(lire_texte(chemin), strict=False) if chemin.exists() else defaut


def photos_publication(sources, cible, retouche):
    """Photos d'une pièce à publier : toutes traitées de la même façon,
    couleurs et lumière corrigées, sans passe-partout, cadrage d'origine."""
    if TEST:
        return
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        for i, src in enumerate(sources, 1):
            with Image.open(src) as im:
                sortie = retouche.autre_photo(im, TAILLE_MAX)
            sortie.save(temp / f"{i}.jpg", "JPEG", quality=QUALITE, optimize=True, progressive=True)
        cible.mkdir(parents=True, exist_ok=True)
        for f in sorted(temp.iterdir()):
            avec_reprises(shutil.copyfile, f, cible / f.name)
    gardes = {f"{i}.jpg" for i in range(1, len(sources) + 1)}
    for f in cible.glob("*.jpg"):
        if f.name not in gardes:
            avec_reprises(f.unlink)


def preparer_publications(bijoux, retouche):
    """Dresse la liste des pièces à publier et renvoie les lignes du compte rendu."""
    en_ligne = {b["id"]: b for b in bijoux}
    avant = {p["id"]: p for p in lire_json(A_PUBLIER, {"pieces": []})["pieces"]}
    journal = lire_json(JOURNAL, {})
    pieces, ecartees, inconnus = [], [], []
    fiches = deja = 0

    cats = sorted((c for c in PHOTOS.iterdir() if c.is_dir()
                   and (c.name in HORS_SITE_PUBLIABLES or c.name not in EXCLUES)),
                  key=lambda c: tri_naturel(c.name))
    for cat in cats:
        hors_site = cat.name in HORS_SITE_PUBLIABLES
        # Seuls les sous-dossiers comptent : les photos en vrac sont ignorées
        for d in sorted((d for d in cat.iterdir() if d.is_dir()), key=lambda d: tri_naturel(d.name)):
            fiche = d / FICHE
            if not fiche.exists():
                if hors_site and photos_source(d):
                    ecrire_fiche_hors_site(fiche, titre_par_defaut(d.name))
                    fiches += 1
                continue
            completer_fiche(fiche)
            infos = lire_fiche(fiche)
            nom = f"{cat.name} / {d.name}"
            valeur = slug(infos.get("publier", "non"))
            if valeur not in TAGS:
                inconnus.append(f"{nom} : « {infos.get('publier')} »")
                continue
            tag = TAGS[valeur]
            if not tag:
                continue
            ident = f"{slug(cat.name)}--{slug(d.name)}"
            if ident in journal:
                deja += 1
                continue
            if not oui(infos.get("disponible", "non")):
                ecartees.append(f"{nom} (disponible: non)")
                continue
            ancienne = avant.get(ident, {})
            # Toutes les pièces : photos de publication traitées de la même façon
            sources = photos_source(d)
            if True:
                if not sources:
                    ecartees.append(f"{nom} (aucune photo)")
                    continue
                emp = empreinte(sources, "publication")
                if (ancienne.get("empreinte") == emp
                        and all((PUBLICATIONS / p).exists() for p in ancienne["photos"])):
                    photos = ancienne["photos"]
                else:
                    try:
                        print(f"  photos de publication : {nom}", flush=True)
                        photos_publication(sources, PHOTOS_PUBLI / ident, retouche)
                    except Exception as e:
                        ecartees.append(f"{nom} (échec des photos : {e})")
                        continue
                    photos = [f"photos/{ident}/{i}.jpg" for i in range(1, len(sources) + 1)]
            pieces.append({
                "id": ident,
                "tag": tag,
                "categorie": cat.name,
                "dossier": d.name,
                "titre": infos.get("titre") or titre_par_defaut(d.name),
                "description": infos.get("description", ""),
                "photos": photos,
                "source": "local",
                "empreinte": emp,
                "tague_le": ancienne.get("tague_le") or datetime.fromtimestamp(
                    fiche.stat().st_mtime).isoformat(timespec="seconds"),
            })

    pieces.sort(key=lambda p: (p["tague_le"], tri_naturel(p["id"])))

    if not TEST:
        PUBLICATIONS.mkdir(parents=True, exist_ok=True)
        A_PUBLIER.write_text(json.dumps({"genere_le": datetime.now().isoformat(timespec="seconds"),
                                         "pieces": pieces}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        if not JOURNAL.exists():
            JOURNAL.write_text("{}\n", encoding="utf-8")
        # Les photos d'une pièce déjà préparée restent là tant qu'elle est au journal
        gardes = {p["id"] for p in pieces} | set(journal)
        if PHOTOS_PUBLI.is_dir():
            for dossier in PHOTOS_PUBLI.iterdir():
                if dossier.is_dir() and dossier.name not in gardes:
                    retirer_dossier(dossier)

    n, c = (sum(p["tag"] == t for p in pieces) for t in ("nouveau", "noel"))
    lignes = [f"\nÀ publier sur les réseaux : {len(pieces)} pièce(s)"
              f"  ({n} nouveauté(s), {c} Noël ; {deja} déjà publiée(s))"]
    sans_texte = [p for p in pieces if not p["description"]]
    if sans_texte:
        lignes.append(f"   Sans description : {len(sans_texte)}")
        lignes += [f"   - {p['categorie']} / {p['dossier']}" for p in sans_texte]
    if fiches:
        lignes.append(f"   Fiches infos.txt créées dans Noël : {fiches}"
                      " (mettez « publier: noel » sur les pièces à ressortir)")
    if ecartees:
        lignes.append(f"   Taguées mais écartées : {len(ecartees)}")
        lignes += [f"   - {e}" for e in ecartees]
    if inconnus:
        lignes.append("   Valeur de « publier: » non reconnue (nouveau, noel ou non) :")
        lignes += [f"   - {i}" for i in inconnus]
    return lignes


# ── Programme ────────────────────────────────────────────────────
def main():
    if not PHOTOS.is_dir():
        print(f"Dossier Photos introuvable : {PHOTOS}")
        return
    if TEST:
        print("*** SIMULATION : aucun fichier ne sera modifié ***\n")

    retouche = None
    if not TEST:
        try:
            import retouche
        except ImportError as e:
            print(f"Il manque des outils ({e.name}) : lancez d'abord « Installer les outils.bat ».")
            print("Rien n'a été modifié.")
            return

    if not TEST:
        for reste in IMG.glob("*/*.tmp"):        # restes d'une mise à jour interrompue
            shutil.rmtree(reste, ignore_errors=True)

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
    versions, echecs = [], []
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
                completer_fiche(fiche)
                infos = lire_fiche(fiche)

            if not oui(infos.get("afficher", "oui")):
                masques.append(f"{cat} / {d.name}")
                continue

            sources = photos_source(d)
            if not sources:
                sans_photo.append(f"{cat} / {d.name}")
                continue

            cible = IMG / slug(cat) / slug(d.name)
            choix = choix_vignette(infos)
            emp = empreinte(sources, choix)
            deja = etat.get(ident)

            if deja and deja["sources"] == emp and all((DEPOT / p).exists() for p in deja["photos"]):
                photos = deja["photos"]
            elif premier_lancement and ident in ancien and all(
                    (DEPOT / p).exists() for p in ancien[ident]["photos"]):
                photos = ancien[ident]["photos"]          # on garde les photos déjà en ligne
                adoptes += 1
            else:
                try:
                    version = preparer_photos(sources, cible, choix, retouche)
                except Exception as e:
                    # Un bijou en échec n'arrête pas les autres
                    echecs.append(f"{cat} / {d.name} : {e}")
                    print(f"  ÉCHEC : {cat} / {d.name} : {e}", flush=True)
                    if not deja:
                        continue
                    nouvel_etat[ident] = deja
                    photos = deja["photos"]
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
                    continue
                photos = [chemin_web(cible / f"{i}.jpg") for i in range(1, len(sources) + 1)]
                traites += 1
                versions.append((f"{cat} / {d.name}", version))
                print(f"  photos préparées : {cat} / {d.name} ({len(sources)}, vignette : {version})", flush=True)

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
                retirer_dossier(dossier)

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

    # Un problème ici ne doit pas gêner la mise à jour du site, déjà écrite
    try:
        lignes_publi = preparer_publications(bijoux, retouche)
    except Exception as e:
        lignes_publi = [f"\nAttention : liste des publications non mise à jour ({e})"]

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
    if FICHES_COMPLETEES:
        print(f"\nLigne « publier: non » ajoutée à {len(set(FICHES_COMPLETEES))} fiche(s) infos.txt")
    if masques:
        print(f"\nMasqués (afficher: non) : {len(masques)}")
    if sans_photo:
        print("\nDossiers sans photo, ignorés :")
        for s in sans_photo:
            print(f"   - {s}")
    if inconnues:
        print(f"\nNouvelle(s) catégorie(s) publiée(s) : {', '.join(inconnues)}")
    if echecs:
        print(f"\nBijoux non traités ({len(echecs)}), relancez la mise à jour :")
        for e in echecs:
            print(f"   - {e}")
    for ligne in lignes_publi:
        print(ligne)
    if TEST:
        print("\n*** SIMULATION : rien n'a été modifié ***")
    else:
        if versions:
            print("\nÀ contrôler dans GitHub Desktop avant de publier :")
            for nom, version in versions:
                print(f"   - {nom} : vignette {version}")
            print("Si une vignette ne convient pas, changez « vignette: » dans son infos.txt "
                  "(detoure, corrige ou origine), puis relancez.")
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
