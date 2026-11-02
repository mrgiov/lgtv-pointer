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

1. HACS → ⋮ → Repository personalizzati → aggiungi questo repository, categoria **Integrazione**, poi installalo.
2. Attivalo con una riga nella configurazione (per esempio in un file di `packages/`):

   ```yaml
   lgtv_pointer:
   ```

3. Riavvia Home Assistant.

## Attenzione

Riusa il client WebSocket che `webostv` ha già aperto (`entry.runtime_data.client`), un dettaglio interno di
quell'integrazione. Un aggiornamento di Home Assistant che lo cambia può rompere questo componente: se i servizi
smettono di funzionare dopo un aggiornamento, apri una segnalazione (issue).
