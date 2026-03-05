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

## Stato operativo aggiornato (2026-03-04 11:26)
- Accesso da IP rete fissa: **ripristinato**.
- Ripristino completo pannello admin applicato in modalità safe (solo configurazione DB, nessun overwrite core rischioso):
  - Script: `deploy/restore_admin_panel_defaults.php`
  - Backup automatico creato: `/home/w19158/public_html/upgrade_backups/admin_modules_backup_20260304_102631.json`
- Moduli core admin ora pubblicati e allineati alle posizioni standard:
  - `mod_quickicon` (`icon`)
  - `mod_popular`, `mod_latest`, `mod_logged` (`cpanel`)
  - `mod_unread`, `mod_online` (`header`)
  - `mod_menu`, `mod_status`, `mod_submenu`, `mod_title`, `mod_toolbar`
- Verifica post-ripristino:
  - Smoke autenticato admin: tutte le route principali **200 OK**.
  - Stato template admin: `Atum` attivo e default.
  - Ispezione UI admin: confermata pubblicazione moduli core (`cpanel/header/menu/toolbar/status/title`).

## Nota di sicurezza operativa
- Per mantenere stabilità in questo ambiente ibrido legacy/J4, il ripristino è stato eseguito su stato moduli/template e non tramite sostituzione massiva di file core (approccio già testato come non sicuro su `framework.php`).

## Hotfix UI admin senza stile (2026-03-04 11:36)
- Segnalazione: backend admin visualizzato "senza alcuno stile" (layout leggibile ma inusabile).
- Root cause verificata:
  - Il template `administrator/templates/atum/index.php` caricava il preset `template.atum.ltr`, ma il manifest asset Atum puntava CSS relativi non coerenti con il layout file reale.
  - Risultato: nell'`<head>` venivano iniettati solo stylesheet vendor (es. FontAwesome), ma non `template.min.css`.
- Correzione applicata (safe + con backup):
  - Script: `deploy/fix_admin_atum_template_asset_paths.php`
  - File patchati con backup `.bak_paths_*`:
    - `/home/w19158/public_html/administrator/templates/atum/joomla.asset.json`
    - `/home/w19158/public_html/media/templates/administrator/atum/joomla.asset.json`
  - URI riallineati a percorsi validi media:
    - `media/templates/administrator/atum/css/template.min.css`
    - `media/templates/administrator/atum/css/template-rtl.min.css`
    - `media/templates/administrator/atum/css/user.css`
    - `media/system/css/searchtools/searchtools.min.css`
- Verifica post-fix:
  - Smoke admin autenticato: tutte le route principali `200 OK`.
  - Snapshot HTML dashboard: presente link stylesheet Atum `.../media/templates/administrator/atum/css/template.min.css?...`.

## Aggiornamento account admin richiesto (2026-03-04 11:31)
- Email `joomladev` aggiornata a: `plombardi85@gmail.com`.

## Hotfix Notice in "All Menu Items" (2026-03-04 11:41)
- Errore segnalato:
  - `Notice: Undefined property: stdClass::$language`
  - file: `/home/w19158/public_html/administrator/components/com_menus/models/fields/menuitembytype.php`
  - linee coinvolte: blocchi equivalenti alle linee 221/223 e 253/255.
- Root cause: alcuni record/link menu arrivano senza proprietà `language` valorizzata, ma il field model accedeva direttamente a `$link->language`.
- Fix applicato (con backup automatico):
  - script: `deploy/fix_remote_menuitembytype_language_notice.py`
  - backup remoto: `menuitembytype.php.bak_langnotice_20260304_114123`
  - patch: fallback safe `isset($link->language) ? $link->language : '*'` prima della costruzione label lingua.
- Verifica:
  - lint PHP remoto: OK
  - test autenticato su `index.php?option=com_menus&view=items`: `Undefined property: stdClass::$language` non presente (`count=0`).

### Parità staging (2026-03-04 11:47)
- Fix replicato anche su staging:
  - `/home/w19158/public_html_staging/administrator/components/com_menus/models/fields/menuitembytype.php`
- Backup creato: `menuitembytype.php.bak_langnotice_20260304_114723`
- Stato patch staging: entrambe le occorrenze aggiornate con fallback `isset($link->language) ? $link->language : '*'`.
- Lint PHP staging: OK.
- Cache staging svuotate (`cache` + `administrator/cache`).

## Hotfix icone mancanti nel backend (2026-03-04 11:59)
- Sintomo: pannello admin funzionante ma icone non visibili (quadratini placeholder).
- Root cause: nel rendering Atum veniva caricato solo `fontawesome.min.css` base, senza bundle completo glyph.
- Fix applicato:
  - script: `deploy/fix_admin_icons_fontawesome_bundle.php`
  - file patchati (con backup `.bak_icons_*`):
    - `/home/w19158/public_html/administrator/templates/atum/joomla.asset.json`
    - `/home/w19158/public_html/media/templates/administrator/atum/joomla.asset.json`
  - dipendenze Atum allineate al bundle completo: `media/system/css/joomla-fontawesome.min.css`.
- Verifica:
  - smoke admin: tutte le route principali `200 OK`.
  - HTML dashboard contiene ora `<link ... /media/system/css/joomla-fontawesome.min.css ...>`.

## Hotfix warning filesystem providers (2026-03-04 12:07)
- Avviso segnalato:
  - `No filesystem providers have been found. Please enable at least one filesystem plugin.`
- Root cause:
  - plugin core `filesystem/local` presente su disco (`plugins/filesystem/local`) ma **non registrato** in `#__extensions`.
- Correzione applicata:
  - script: `deploy/register_filesystem_local_plugin.php`
  - registrazione extension: `type=plugin`, `folder=filesystem`, `element=local`, `enabled=1`.
  - extension_id creato: `10051`.
- Verifica:
  - route admin `com_media` e `com_menus` testate in login autenticato senza presenza del warning.

## Riduzione legacy safe (2026-03-04 12:20)
- Obiettivo: ridurre superfici legacy senza impatto funzionale su backend e preparare upgrade successivo.
- Azioni applicate (produzione + staging):
  - Disabilitato componente legacy non-core `com_jaextmanager` (era abilitato, ora `enabled=0`).
  - Disabilitata estensione template legacy `ja_elastica` **solo dopo controllo di sicurezza**:
    - non template frontend di default (`home=0`)
    - nessuna assegnazione menu pubblicata (`published_assignments=0`)
    - quindi disattivazione a rischio basso confermata.
- Verifica post-change:
  - cache svuotate su entrambi gli ambienti;
  - smoke admin autenticato produzione: tutte le route principali `200 OK`.

## Prossimo blocco consigliato (upgrade-ready, safe-first)
1. Mantenere disattive tutte le estensioni legacy non indispensabili (`com_jaextmanager` già rimosso da runtime attivo).
2. Eseguire audit periodico `administrator/**/*.php` per trend su `JRequest/JError/JModelLegacy` e fissare target di riduzione per release.
3. Consolidare staging come ambiente “clean baseline” per test upgrade (provider filesystem, moduli Atum, warning-critical eliminati).
4. Prima del prossimo upgrade Joomla: snapshot DB+files, smoke admin completo, rollback plan già pronto.

## Audit legacy aggiornato (2026-03-04 12:26)
- Report: `upgrade_backups/admin_legacy_audit_latest.json`
- Totale finding: **1483**
- Severità:
  - Critical: **567** (`JRequest::*`)
  - High: **296** (`JError`, `JModelLegacy`, `JControllerLegacy`)
  - Medium: **620** (`DS`, `JTable`, `JFactory::getDbo`, `JArrayHelper`)
- Top concentrazione (file):
  1. `administrator/components/com_jaextmanager/models/default.php` (51)
  2. `administrator/components/com_jaextmanager/controllers/default.php` (24)
  3. `administrator/components/com_akeeba/liveupdate/classes/controller.php` (23)
  4. `administrator/components/com_jaextmanager/controllers/services.php` (20)
  5. `administrator/components/com_media/controllers/folder.php` (16)

### Lettura operativa del rischio
- `com_jaextmanager` rimane la concentrazione n.1 ma è già **disabilitato** (`enabled=0`), quindi rischio runtime ridotto.
- Hotspot attivo più rilevante non-core: `com_akeeba` (`enabled=1`).
- Hotspot core residui (`com_media`, `com_installer`, `com_menus`, `com_templates`, `com_users`) richiedono patch chirurgiche, non disattivazione.

### Backlog prioritario pre-upgrade (ordine consigliato)
1. **Akeeba liveupdate**: ridurre `JRequest/JError` nei file `administrator/components/com_akeeba/liveupdate/**` (impatto alto, rischio medio-basso con patch mirate).
2. **com_media (core)**: bonifica minima su controller/view più colpiti mantenendo piena compatibilità admin.
3. **com_installer + com_menus (core)**: sostituzioni progressive API legacy nei metodi usati dallo smoke.
4. **Riaudit + smoke** a ogni blocco (no big-bang): target riduzione critical/high per step.

## Blocco Akeeba liveupdate (2026-03-04 12:32)
- Intervento safe applicato su produzione:
  - `administrator/components/com_akeeba/liveupdate/classes/controller.php`
  - `administrator/components/com_akeeba/liveupdate/classes/view.php`
- Strategia tecnica:
  - sostituzione chiamate dirette `JRequest::*` con input-safe wrappers (`inputCmd/inputBool/inputString`) nel controller;
  - conversione letture request nel view con `JFactory::getApplication()->input`.
  - fallback compatibilità mantenuto nel controller (`class_exists('JRequest')`) per evitare regressioni.
- Sicurezza operativa:
  - backup remoti `.bak_inputapi_*` creati prima della modifica;
  - lint PHP remoto su entrambi i file: OK;
  - smoke admin autenticato: tutte le route principali `200 OK`.

### Delta misurato post-blocco
- Audit precedente: `FINDINGS=1483` (`critical=567`).
- Audit attuale: `FINDINGS=1452` (`critical=536`).
- Riduzione netta: **-31 finding** totali e **-31 critical (`JRequest`)** in un singolo blocco a rischio basso.

## Blocco Akeeba liveupdate — step 2 (2026-03-04 12:28)
- Estensione patch input-safe su ulteriori file attivi:
  - `administrator/components/com_akeeba/liveupdate/liveupdate.php`
  - `administrator/components/com_akeeba/liveupdate/classes/view.php`
  - `administrator/components/com_akeeba/liveupdate/classes/tmpl/install.php`
  - `administrator/components/com_akeeba/liveupdate/classes/tmpl/startupdate.php`
- Deploy con backup batch `.bak_batch_20260304_122827`, lint PHP OK su tutti i file.
- Smoke admin post-deploy: tutte le route principali `200 OK`.
- Pulizia `JRequest` nei file toccati: residuo **0** occorrenze.

### Delta audit cumulato (inizio sessione -> stato attuale)
- Inizio: `FINDINGS=1483`, `critical=567`.
- Stato attuale: `FINDINGS=1432`, `critical=511`.
- Miglioramento cumulato: **-51 finding** totali, **-56 critical**.

## Incidenti runtime segnalati dall'utente (2026-03-04 12:35)

### 1) `com_akeeba` fatal in admin
- Segnalazione iniziale: `Call to undefined method JRequest::_cleanVar()` su `index.php?option=com_akeeba`.
- Fix applicati:
  - estensione polyfill `JRequest` (`administrator/includes/legacy_dispatcher_polyfill.php`) con metodo compat `::_cleanVar()`.
  - compat layer FOF su `isSite()` -> check `isClient('site')` dove disponibile (`libraries/fof/controller.php`, `dispatcher.php`, `toolbar.php`).
- Esito finale operativo:
  - il componente `com_akeeba` risultava comunque incompatibile con piattaforma engine legacy (`Can not find a suitable Akeeba Engine platform for your site`).
  - per stabilità e obiettivo anti-legacy, `com_akeeba` è stato disattivato in produzione (`enabled=0`; extension_id `10044`).
  - route `index.php?option=com_akeeba` ora risponde `404` (nessun fatal backend).

### 2) errore lock su menu item `id=560`
- Segnalazione: `Blocco fallito ... utente che sta bloccando non coincide ...` in edit menu item.
- Diagnosi: record `#__menu.id=560` con `checked_out=42`.
- Correzione: unlock forzato (`checked_out=0`, `checked_out_time='0000-00-00 00:00:00'`).
- Verifica: URL edit `id=560` torna `200` senza messaggio di lock.

## Micro-batch riduzione criticals (2026-03-04)
- Obiettivo del batch: ridurre `JRequest::*` nei componenti admin con patch low-risk e verifica sintattica immediata.
- Delta misurato locale su `administrator/components/**/*.php`:
  - baseline batch: `JREQUEST_COUNT=293`
  - stato finale batch: `JREQUEST_COUNT=248`
  - miglioramento netto: **-45** occorrenze `JRequest::*`.

### File toccati in questo batch
- `administrator/components/com_installer/models/discover.php`
  - conversione input su `cid` in `discover_install()`.
- `administrator/components/com_installer/models/manage.php`
  - allineamento input `filters` su API input moderna.
  - fix strutturale docblock/metodo dopo auto-correction (parse error risolto).
- `administrator/components/com_templates/views/prevuuw/view.html.php`
  - rimozione residui `JRequest` per `client/id/option`.
- `administrator/components/com_phocafavicon/helpers/phocafaviconfileupload.php`
  - conversione token check e letture request principali (`Filedata`, `folder`, `format`, `return-url`, `viewback`, `field`, `option`).

### Verifica tecnica
- Lint PHP eseguito sui file toccati nel batch: **OK**.
- Parse error intercettati durante il batch (`com_installer/models/discover.php`, `com_installer/models/manage.php`) corretti e rilintati con esito pulito.

## Hotfix DB `checked_out` null su menu item 560 (2026-03-04)
- Errore segnalato in admin edit menu item:
  - `Column 'checked_out' cannot be null`
  - URL: `index.php?option=com_menus&view=item&client_id=0&layout=edit&id=560`
- Correzione immediata applicata in produzione via SQL remoto:
  - `id=560` forzato a `checked_out=0`, `checked_out_time='0000-00-00 00:00:00'`.
  - normalizzazione globale tabella `#__menu` per eventuali record legacy con `checked_out` / `checked_out_time` null.
- Verifica post-fix (remota):
  - `ITEM560 560|CONTATTI|0|0000-00-00 00:00:00`
  - `MENU_NULL_CHECKOUT_COUNT 0`

### Hardening codice (prevenzione)
- Aggiunto guard rail in `administrator/components/com_menus/tables/menu.php`:
  - normalizzazione campi checkout in `bind()`, `load()` e `store()` per evitare future scritture `NULL` su colonne NOT NULL.

### Mitigazione runtime aggiuntiva (toggle stato menu)
- Persistendo errore UI su cambio stato (`publish/unpublish`) in lista menu, applicata mitigazione mirata su:
  - `administrator/components/com_menus/models/item.php`
- Modifica: override `publish()` con percorso diretto su tabella menu (`$table->publish(...)`) mantenendo controlli permessi/default home e cache clean, evitando pipeline eventi generica che in questo ambiente causava side-effect sul campo `checked_out`.
- Deploy produzione effettuato con backup remoto:
  - `/home/w19158/public_html/administrator/components/com_menus/models/item.php.bak_publishfix_20260304_132541`
- Verifica post-deploy:
  - lint remoto file: OK
  - nessun nuovo match nei log remoti su `checked_out ... null` al momento del controllo.
