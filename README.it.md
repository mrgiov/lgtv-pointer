# LG webOS TV pointer

[English](README.md) · **Italiano**

Integrazione personalizzata di Home Assistant che aggiunge all'integrazione `webostv` ciò che questa non offre.
È il complemento di [lg-tv-remote-card](https://github.com/mrgiov/lg-tv-remote-card), ma i servizi si possono
usare anche da soli.

| Servizio | Cosa fa |
| --- | --- |
| `lgtv_pointer.move` (`dx`, `dy`) | sposta il puntatore del telecomando magico |
| `lgtv_pointer.click` | clicca dove si trova il puntatore |
| `lgtv_pointer.scroll` (`dx`, `dy`) | scorre |
| `lgtv_pointer.watch_keyboard` | genera l'evento `lgtv_pointer_keyboard` quando un campo di testo prende o perde il focus sulla TV |
| `lgtv_pointer.app_icons` | copia le icone delle app della TV in `/config/www/lg-tv-remote/icons/` e restituisce `{icons: {titolo: url}}` (la TV le serve in HTTPS con un certificato autofirmato, quindi un browser non può caricarle direttamente) |

Tutti i servizi richiedono l'`entity_id` di un media player `webostv`.

## Installazione

1. HACS → cerca **LG webOS TV pointer** (oppure ⋮ → Repository personalizzati → questo repository, categoria **Integrazione**) e installalo.
2. Riavvia Home Assistant.
3. Accendi la TV. Impostazioni → Dispositivi e servizi → Aggiungi integrazione → **LG webOS TV pointer**, inserisci l'indirizzo IP della TV, premi Invia e accetta la richiesta di connessione sulla TV.

I servizi richiedono l'`entity_id` del media player `webostv` della TV; l'integrazione trova da sola la propria voce per quella TV.

## Come si collega

Si abbina da sola alla TV e tiene una connessione propria, separata da quella dell'integrazione `webostv` del core (la TV la elenca come seconda app abbinata). Si collega quando un servizio viene chiamato, quindi una TV spenta non è un problema: la chiamata fallisce con «TV not connected».

## Passaggio dalla 1.x

La 1.x si attivava con una riga `lgtv_pointer:` nella configurazione e prendeva in prestito la connessione di `webostv`. Togli quella riga (per esempio `packages/lgtv_pointer.yaml`), riavvia e aggiungi l'integrazione come sopra. I servizi e l'evento `lgtv_pointer_keyboard` non cambiano, quindi la card continua a funzionare.
