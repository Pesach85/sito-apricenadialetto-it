# Admin Legacy Remediation Plan (2026-03-04)

## Obiettivo
Portare il backend a uno stato Joomla 4 pulito e stabile, eliminando progressivamente la dipendenza da API legacy (`JRequest`, `JError`, ecc.) senza bloccare la produzione.

## Baseline misurata
Audit locale: `upgrade_backups/admin_legacy_audit_latest.json`

- Finding totali: **1477**
- Critici (JRequest): **565**
- High (JError/JModelLegacy/JControllerLegacy): **293**
- Medium (JTable/JFactory::getDbo/JArrayHelper/DS): **619**

Top aree critiche:
1. `administrator/components/com_jaextmanager/**`
2. `administrator/components/com_akeeba/liveupdate/**`
3. `administrator/components/com_media/**`
4. `administrator/components/com_installer/**`
5. `administrator/components/com_users/**`

## Strategia in 3 fasi

### Fase 1 — Stabilizzazione runtime (immediata)
- Mantenere un solo punto di compatibilità in `administrator/includes/legacy_dispatcher_polyfill.php`.
- Coprire i metodi `JRequest::*` realmente usati nel backend (`get`, `getVar`, `getCmd`, `getInt`, `getBool`, `getString`, `getWord`, `setVar`, `checkToken`).
- Obiettivo: **zero fatal** su route admin core critiche (`com_content`, `com_installer`, `com_users`, login).

### Fase 2 — Bonifica extension legacy (staging)
- Disattivare/sostituire estensioni admin con maggiore densità legacy:
  - `com_jaextmanager`
  - vecchi moduli/liveupdate Akeeba non compatibili
- Ridurre in modo aggressivo i richiami `JRequest::get`/`getVar` nelle estensioni custom o obsolete.
- Criterio: ogni estensione deve passare smoke admin senza usare polyfill non necessario.

### Fase 3 — Upgrade pulito J4/J5-ready
- Eseguire upgrade solo quando i check staging sono GO:
  - precheck ambiente + estensioni
  - smoke completo backend
  - error log pulito dopo navigazione guidata admin
- Dopo cutover: ridurre gradualmente il polyfill fino a tenerlo solo per compat residuale minima.

## Sequenza operativa consigliata
1. Stabilizzare produzione con polyfill unico (già in corso).
2. Clonare staging aggiornato.
3. Bonificare `com_jaextmanager` e pacchetti legacy prioritari.
4. Rieseguire audit + smoke ad ogni blocco.
5. Procedere a upgrade definitivo solo con log admin pulito.

## Definition of Done
- Nessun fatal PHP nel backend durante smoke dei flussi principali.
- Nessun errore bloccante su `administrator/index.php?option=com_content&task=article.add`.
- Report audit aggiornato con trend in riduzione (critici/high in forte calo).
- Precheck staging J4 in stato GO.

## Stato operativo aggiornato (2026-03-04 10:49)
- Produzione admin: route principali verificate con smoke autenticato, tutte **200 OK**.
- Add Article: operativo (`index.php?option=com_content&task=article.add` OK).
- Staging probe ufficiale: **SMOKE_OK** (`upgrade_backups/staging_smoke_j4_latest.json`).
- Delta safe applicato: hardening `JRequest` polyfill admin (metodi legacy essenziali).

## Incidente cPanel 403 — Diagnosi e runbook rapido

### Sintomo rilevato
- `https://apricenadialetto.it:2083/` e `https://cpanel.apricenadialetto.it:2083/` rispondono `403 Forbidden` con header/server `openresty`.

### Diagnosi tecnica
- Il backend Joomla admin può risultare operativo anche quando cPanel è bloccato.
- Il 403 su 2083 indica blocco a livello proxy/WAF/ACL (non errore applicativo Joomla).

### Checklist immediata lato hosting/provider
1. Verificare e rimuovere eventuale ban IP su cPanel:
   - `cPHulk` (blacklist/temporary blocks)
   - CSF/LFD deny list
2. Controllare regole WAF/ModSecurity su endpoint 2083.
3. Verificare ACL/reverse proxy OpenResty/Nginx su host e vhost cPanel.
4. Confermare che il traffico verso 2083 non venga bloccato da geofilter/rate limit.
5. Dopo fix, test rapido:
   - `https://apricenadialetto.it:2083/login/` deve mostrare la login cPanel (non 403).

### Verifica post-fix consigliata
- Eseguire smoke admin applicativo:
  - `deploy/smoke_admin_routes.py`
- Eseguire scansione log:
  - `deploy/find_remote_loadarray_stack.py`
- Confermare assenza di nuovi fatal in `administrator/error_log` dopo i test.
