/* Affichage de l'agenda (ne pas modifier — les dates se changent dans agenda.js) */
(function () {
  const aujourdHui = new Date(); aujourdHui.setHours(0, 0, 0, 0);
  const jour = s => { const [a, m, j] = String(s).split('-').map(Number); return new Date(a, (m || 1) - 1, j || 1); };
  const fmt = (d, opts) => d.toLocaleDateString('fr-FR', opts);
  const maj = s => s.charAt(0).toUpperCase() + s.slice(1);
  const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const aVenir = e => jour(e.fin || e.date) >= aujourdHui;
  const tri = (a, b) => jour(a.date) - jour(b.date);
  const vide = txt => `<p class="agenda-vide">${txt}</p>`;

  function periode(e) {
    const d = jour(e.date);
    if (!e.fin || e.fin === e.date) return maj(fmt(d, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }));
    const f = jour(e.fin);
    const memeMois = d.getMonth() === f.getMonth() && d.getFullYear() === f.getFullYear();
    return memeMois
      ? `Du ${d.getDate()} au ${fmt(f, { day: 'numeric', month: 'long', year: 'numeric' })}`
      : `Du ${fmt(d, { day: 'numeric', month: 'long' })} au ${fmt(f, { day: 'numeric', month: 'long', year: 'numeric' })}`;
  }

  window.afficherExpositions = function (id) {
    const zone = document.getElementById(id); if (!zone) return;
    const liste = (typeof expositions !== 'undefined' ? expositions : []).filter(aVenir).sort(tri);
    if (!liste.length) { zone.innerHTML = vide('Prochaines dates bientôt annoncées.'); return; }
    zone.innerHTML = liste.map(e => `
      <div class="atelier-card expo-card">
        <div class="atelier-date">${esc(periode(e))}</div>
        <div class="expo-nom">${esc(e.lieu)}</div>
        <div class="atelier-info">${esc(e.nom)}${e.horaires ? ' · ' + esc(e.horaires) : ''}${e.infos ? '<br>' + esc(e.infos) : ''}</div>
      </div>`).join('');
  };

  window.afficherAteliers = function (id) {
    const zone = document.getElementById(id); if (!zone) return;
    const liste = (typeof ateliers !== 'undefined' ? ateliers : []).filter(aVenir).sort(tri);
    if (!liste.length) { zone.innerHTML = vide('Prochaines dates bientôt annoncées. Écrivez-moi pour être prévenu(e) !'); return; }
    zone.innerHTML = liste.map(a => {
      const total = Number(a.places) || 0, reste = a.restantes === undefined || a.restantes === '' ? total : Number(a.restantes);
      const complet = reste <= 0;
      const badge = complet ? '<span class="badge badge-full">Complet</span>'
        : reste < total ? `<span class="badge badge-reste">${reste} place${reste > 1 ? 's' : ''} restante${reste > 1 ? 's' : ''}</span>`
        : '<span class="badge badge-dispo">Disponible</span>';
      const titre = periode(a);
      const lien = complet ? '' : `<a class="atelier-inscription" href="contact.html?atelier=${encodeURIComponent(titre + (a.theme ? ' — ' + a.theme : ''))}">S'inscrire →</a>`;
      return `
      <div class="atelier-card${complet ? ' full' : ''}">
        <div class="atelier-date">${esc(titre)}</div>
        ${a.theme ? `<div class="expo-nom">${esc(a.theme)}</div>` : ''}
        <div class="atelier-info">${esc(a.lieu)}${a.horaires ? ' · ' + esc(a.horaires) : ''}${total ? ' · ' + total + ' places max' : ''}${a.tarif ? '<br>' + esc(a.tarif) : ''}</div>
        <div class="atelier-bas">${badge}${lien}</div>
      </div>`;
    }).join('');
  };
})();
