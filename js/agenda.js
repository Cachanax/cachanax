/*
  ════════════════════════════════════════════════════════════════
  AGENDA — expositions et ateliers
  Affiché sur la page d'accueil (les deux) et sur la page Ateliers.

  • Les dates passées disparaissent toutes seules du site.
  • Dates au format AAAA-MM-JJ (ex. "2026-11-21" pour le 21 novembre 2026).
  • Chaque bloc { … } est séparé du suivant par une virgule.
  • Liste vide = le site affiche « Prochaines dates bientôt annoncées ».
  ════════════════════════════════════════════════════════════════
*/

/* ── EXPOSITIONS / MARCHÉS ──
   Modèle à copier (enlevez les // au début des lignes) :

  {
    date: "2026-11-21",          // premier jour
    fin: "2026-11-22",           // dernier jour (laissez "" si un seul jour)
    nom: "Marché de Noël",
    lieu: "Salle des fêtes, Lentilly (69)",
    horaires: "10h – 18h",       // facultatif
    infos: ""                    // facultatif : stand, thème…
  },
 */

const expositions = [
  {
    date: "2026-11-28",          // premier jour
    fin: "",                     // dernier jour (laissez "" si un seul jour)
    nom: "Marché de Noël",
    lieu: "Lentilly (69), Ecole Jeanne d'Arc",
    horaires: "10h – 18h",       // facultatif
    infos: ""                    // facultatif : stand, thème…
  },
  {
    date: "2026-11-29",          // premier jour
    fin: "",                     // dernier jour (laissez "" si un seul jour)
    nom: "Marché de Noël",
    lieu: "St Pierre la Palud (69), Place Mangini",
    horaires: "10h – 18h",       // facultatif
    infos: ""                    // facultatif : stand, thème…
  },
  {
    date: "2026-12-12",          // premier jour
    fin: "",                     // dernier jour (laissez "" si un seul jour)
    nom: "Marché de Noël",
    lieu: "Arnas (69), Autour de la Mairie",
    horaires: "10h – 18h",       // facultatif
    infos: ""                    // facultatif : stand, thème…
  },
  {
    date: "2026-12-20",          // premier jour
    fin: "",                     // dernier jour (laissez "" si un seul jour)
    nom: "Marché de Noël",
    lieu: "Les Olmes (69)",
    horaires: "10h – 18h",       // facultatif
    infos: ""                    // facultatif : stand, thème…
  },
];


/* ── ATELIERS ──
   Modèle à copier :

  {
    date: "2026-11-14",
    horaires: "14h – 17h",
    lieu: "Lentilly (69)",
    places: 4,                   // nombre de places total
    restantes: 2,                // places encore libres (0 = Complet)
    tarif: "50 € · matériel en option +10 €",
    theme: ""                    // facultatif : ex. « Boucles d'oreilles en tissage brick »
  },
*/

const ateliers = [
{
    date: "2026-11-14",
    horaires: "14h – 17h",
    lieu: "Lentilly (69)",
    places: 4,                   // nombre de places total
    restantes: 4,                // places encore libres (0 = Complet)
    tarif: "50 € · matériel en option +10 €",
    theme: ""                    // facultatif : ex. « Boucles d'oreilles en tissage brick »
  },
  {
    date: "2026-12-9",
    horaires: "14h – 17h",
    lieu: "Lentilly (69)",
    places: 4,                   // nombre de places total
    restantes: 4,                // places encore libres (0 = Complet)
    tarif: "50 € · matériel en option +10 €",
    theme: ""                    // facultatif : ex. « Boucles d'oreilles en tissage brick »
  },
];
