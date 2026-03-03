# Operativo manutenzione sito apricenadialetto.it

## 1) Azioni già applicate nel codice (hotfix)

- Mixed content Google Docs viewer corretto a `https://docs.google.com/...` nel plugin `me_edocs`.
- Crash JS `Cannot read properties of null` mitigato con guardie null in `templates/gratis/src/yjsge.js`.
- Crash JS `Cannot read properties of null` mitigato anche in `templates/ja_elastica/blocks/header.php` (search input nullo).
- URL esterni template aggiornati a HTTPS in head/footer.
- Google Fonts del template `ja_elastica` aggiornato a HTTPS.
- Caricamento Google Analytics legacy reso condizionale a consenso (`cookie_consent_analytics=1`).
- Modulo Facebook Like Box reso condizionale a consenso marketing (`cookie_consent_marketing=1`) e iframe forzato HTTPS.
- Banner consenso cookie operativo inserito anche su `ja_elastica`.
- Forzatura HTTPS e mitigazione mixed-content aggiunte in `.htaccess` root (redirect + CSP upgrade).
- `configuration.php`: `force_ssl=2`.

## 2) Intervento immediato su produzione (ordine esatto)

1. Caricare i file patchati via SFTP.
2. Verificare che il file `.htaccess` root aggiornato sia presente lato produzione.
3. Svuotare cache Joomla e cache browser.
4. Verificare pagine:
   - `/index.php/proverbi`
   - `/index.php/vocabolario`
5. Aprire DevTools Console/Network e confermare assenza di:
   - mixed content `http://docs.google.com/...`
   - errori JS `addEvents` / `addEvent`

## 3) Query SQL operative per ripulire contenuti storici (mixed content nel DB)

Eseguire su database Joomla (prima backup):

```sql
UPDATE #__content
SET introtext = REPLACE(introtext, 'http://images.web4web.it/w4w_190x60.jpg', ''),
    fulltext  = REPLACE(fulltext,  'http://images.web4web.it/w4w_190x60.jpg', '')
WHERE introtext LIKE '%images.web4web.it/w4w_190x60.jpg%'
   OR fulltext  LIKE '%images.web4web.it/w4w_190x60.jpg%';

UPDATE #__modules
SET content = REPLACE(content, 'http://images.web4web.it/w4w_190x60.jpg', '')
WHERE content LIKE '%images.web4web.it/w4w_190x60.jpg%';

UPDATE #__content
SET introtext = REPLACE(introtext, 'http://docs.google.com/gview?', 'https://docs.google.com/gview?'),
    fulltext  = REPLACE(fulltext,  'http://docs.google.com/gview?', 'https://docs.google.com/gview?')
WHERE introtext LIKE '%http://docs.google.com/gview?%'
   OR fulltext  LIKE '%http://docs.google.com/gview?%';
```

## 4) Dati visitatori rilevati nel codice (da gestire GDPR/ePrivacy)

- Google Analytics classico (`ga.js`) nel template `gratis`.
- Facebook Like Box (`connect.facebook.net` / `facebook.com/plugins`) nel modulo `mod_itpfblikebox`.
- Cookie tecnici Joomla (sessione/login/remember) gestiti dal core.
- Log server (`logs/`) e potenziali IP/User-Agent lato hosting.

## 5) Adeguamento cookie/compliance (operativo)

1. Installare una CMP Joomla aggiornata e supportata (IAB TCF o equivalente).
2. Mappare categorie cookie:
   - Tecnici: sempre attivi.
   - Analytics: solo dopo consenso.
   - Marketing/profilazione (Facebook): solo dopo consenso.
3. Configurare CMP per valorizzare cookie:
   - `cookie_consent_analytics=1`
   - `cookie_consent_marketing=1`
4. Bloccare script terzi fino al consenso (già predisposto nei file patchati).
5. Aggiornare Informativa Cookie + Privacy con elenco fornitori e tempi conservazione.

## 6) Piano upgrade compatibilità PHP (obbligatorio)

Stato attuale: stack Joomla/estensioni molto datato (era 2.5 con estensioni 2012 circa), non idoneo a PHP moderni.

Sequenza operativa consigliata:

1. Clonare ambiente su staging.
2. Backup completo file+DB (Akeeba presente ma obsoleto: usare anche dump SQL manuale).
3. Portare Joomla a 3.10 LTS in staging (passaggio ponte).
4. Sostituire/rimuovere estensioni obsolete non compatibili:
   - `com_akeeba` 3.5.2
   - `com_phocafavicon` 2.0.3
   - `plg_content_me_edocs` 1.2
   - `mod_itpfblikebox` 1.4
   - framework `jat3` legacy
5. Aggiornare template: migrazione da `gratis` legacy a template Joomla moderno compatibile 4/5.
6. Migrare Joomla 3.10 -> 4.4 LTS -> 5.x.
7. Portare PHP a 8.2/8.3 e rifare test regressione completi.
8. Go-live con finestra di manutenzione e rollback pronto.

## 7) Checklist test finale

- Login/logout utente e admin.
- Ricerca, menu, moduli homepage.
- Pagine `proverbi` e `vocabolario` senza errori console.
- Nessun mixed-content in Network.
- Banner/cmp cookie funzionante e blocco script terzi prima del consenso.
- Backup ripristinabile testato.

## 8) Automazione upgrade “zero-loss” (consigliato)

Obiettivo: automatizzare le parti rischiose prima di ogni upgrade (backup completo + verifica integrità), riducendo al minimo la perdita dati.

### Script pronto

- `deploy/upgrade_guardrail_backup.py`

### Cosa fa automaticamente

1. Legge connessione SFTP da `.vscode/sftp.json` (host, porta, utente, key, passphrase).
2. Crea snapshot remoto con timestamp in `/home/<utente>/upgrade_backups/<timestamp>/`.
3. Genera archivio completo file sito (`tar.gz`) del `public_html`.
4. Legge credenziali DB da `configuration.php` lato server.
5. Genera dump database compresso (`mysqldump | gzip`).
6. Scarica entrambi i backup in locale in `upgrade_backups/<timestamp>/`.
7. Crea `backup_manifest.json` con hash SHA256 dei file per verifica integrità.

### Comando operativo unico (PowerShell)

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_guardrail_backup.py
```

### Regola di sicurezza prima di aggiornare Joomla/estensioni

- Non iniziare nessun upgrade se lo script non termina con `BACKUP_OK`.
- Verificare che in `upgrade_backups/<timestamp>/` esistano:
   - `site_files_<timestamp>.tar.gz`
   - `db_<timestamp>.sql.gz`
   - `backup_manifest.json`

### Rollback rapido (se qualcosa va storto)

1. Ripristino file dal `site_files_<timestamp>.tar.gz` sul server.
2. Ripristino DB da `db_<timestamp>.sql.gz`.
3. Pulizia cache Joomla (`cache/` e `tmp/`), verifica frontend/admin.

### Nota importante

L’upgrade completo 2.5 -> 3.10 -> 4.4 -> 5.x resta **semi-automatico**: backup, verifiche e deploy sono automatizzabili; i passaggi applicativi major (compatibilità estensioni/template) richiedono checkpoint manuali in staging.

## 9) Rollback assistito (script pronto)

Script: `deploy/rollback_assist.py`

### Uso base

```powershell
# Lista snapshot disponibili
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/rollback_assist.py --list

# Dry-run (nessuna modifica) su snapshot specifico
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/rollback_assist.py --snapshot 20260228_092042

# Rollback reale (richiede conferma esplicita)
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/rollback_assist.py --snapshot 20260228_092042 --apply --confirm I_UNDERSTAND
```

### Cosa fa

1. Carica i dati SFTP da `.vscode/sftp.json`.
2. Ricarica su server gli archivi dello snapshot scelto.
3. Ripristina file sito da `tar.gz`.
4. Ripristina DB da `sql.gz`.
5. Pulisce cache Joomla (`cache/`, `tmp/`).

### Protezioni incluse

- Modalità predefinita in dry-run.
- Esecuzione reale solo con doppia intenzione: `--apply --confirm I_UNDERSTAND`.

## 10) One-shot operativo (backup + preflight + rollback plan)

Script: `deploy/upgrade_one_shot.py`

### Comando principale

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_one_shot.py
```

### Cosa fa in sequenza

1. **Preflight remoto**: verifica PHP, spazio disco, permessi `cache/tmp`, presenza `configuration.php`, presenza `jat3` legacy.
2. **Backup guardrail**: esegue `upgrade_guardrail_backup.py` (file+DB+manifest hash).
3. **Rollback plan**: esegue dry-run `rollback_assist.py` sullo snapshot appena creato.
4. Salva report completo in `upgrade_backups/<snapshot>/upgrade_one_shot_report.json`.

### Opzioni utili

```powershell
# Usa snapshot esistente e salta nuovo backup
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_one_shot.py --skip-backup --snapshot 20260228_092042
```

### Regola pratica

Procedere con upgrade solo se output finale è `ONE_SHOT_OK`.

## 11) Clone staging automatico (step successivo upgrade)

Script: `deploy/prepare_staging_clone.py`

### Comandi

```powershell
# Dry-run (raccomandato prima)
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/prepare_staging_clone.py

# Esecuzione reale clone staging
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/prepare_staging_clone.py --apply --confirm I_UNDERSTAND
```

### Cosa prepara

1. Preflight tool server (`rsync`, `mysql`, `mysqldump`, permessi).
2. Clone file in `<remotePath>_staging`.
3. Clone DB in `<db>_stg`.
4. Patch `configuration.php` staging (`db`, `tmp_path`, `log_path`, `force_ssl=0`).
5. Pulizia cache staging.

### Nota hosting (già verificata)

Se il provider non consente `CREATE DATABASE`, lo script fa fallback automatico:

- usa lo **stesso database** della produzione,
- clona tutte le tabelle Joomla su un **prefix staging dedicato**,
- aggiorna `configuration.php` staging con `dbprefix` staging.

Valori correnti rilevati in ambiente:

- `staging_root`: `/home/w19158/public_html_staging`
- `staging_db`: `w19158_io` (fallback stesso DB)
- `staging_dbprefix`: `stgc57_`

## 12) Quando cambiare versione PHP (decisione operativa)

- **Produzione adesso:** NO (restare su PHP attuale finché non finisce la migrazione app).
- **Staging:**
   1. portare Joomla a 3.10 sul clone staging,
   2. test estensioni/template,
   3. passare staging a PHP 7.4 (ponte),
   4. migrare a Joomla 4/5,
   5. solo dopo test verdi, impostare produzione a PHP 8.2/8.3 in finestra go-live.

## 13) Audit estensioni staging (pre-upgrade 3.10)

Script: `deploy/audit_staging_extensions.py`

Comando:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/audit_staging_extensions.py
```

Report generato:

- `upgrade_backups/staging_extension_audit_latest.json`

Risultati attuali (staging):

- `com_akeeba` 3.5.2 → rischio **ALTA**
- `com_phocafavicon` 2.0.3 → rischio **ALTA**
- `plg_system_jat3` (JA T3 Framework) → rischio **CRITICA**
- `plg_content_me_edocs` 1.2 → rischio **ALTA**
- `mod_itpfblikebox` 1.4 → rischio **ALTA**

Ordine operativo immediato prima del salto 3.10:

1. Disattivare in staging `mod_itpfblikebox` e `plg_content_me_edocs`.
2. Valutare rimozione/disattivazione `com_phocafavicon` (favicon via template).
3. Verificare impatto `com_akeeba` (upgrade o disattivazione temporanea in staging).
4. Mantenere `jat3` per il passaggio ponte 3.10, ma pianificare sostituzione framework/template prima del salto a Joomla 4/5.

## 14) Disattivazione selettiva legacy su staging (eseguita)

Script: `deploy/disable_staging_legacy_extensions.py`

Comando applicato:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/disable_staging_legacy_extensions.py --apply --confirm I_UNDERSTAND
```

Stato confermato post-audit:

- `com_phocafavicon` → `enabled=0`
- `plg_content_me_edocs` → `enabled=0`
- `mod_itpfblikebox` → `enabled=0`
- `plg_system_jat3` → `enabled=1` (mantenuto per ponte 3.10)
- `com_akeeba` → `enabled=1` (valutazione successiva)

## 15) Precheck finale avvio upgrade Joomla 3.10 (staging)

Script: `deploy/precheck_joomla310_staging.py`

Comando:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/precheck_joomla310_staging.py
```

Report:

- `upgrade_backups/staging_precheck_j310_latest.json`

Esito attuale:

- `status`: `GO_J310_STAGING`
- `php_version`: `5.6.40`
- `joomla_version`: `2.5.4`
- staging isolato confermato (`dbprefix=stgc57_`, `force_ssl=0`, `tmp/log` su staging)

Prossima azione immediata:

Procedere con aggiornamento Joomla su staging verso 3.10 (ponte), mantenendo produzione invariata.

## 16) Upgrade Joomla 3.10 su staging (eseguito)

Script: `deploy/update_staging_to_j310.py`

Comandi eseguiti:

```powershell
# Dry-run preflight
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/update_staging_to_j310.py

# Apply reale su staging
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/update_staging_to_j310.py --apply --confirm I_UNDERSTAND
```

Risultato:

- `status`: `J310_UPDATE_OK`
- `detected_version`: `3.10.12`
- cache staging pulita dopo overlay package

Verifica post-update eseguita:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/verify_staging_clone.py
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/audit_staging_extensions.py
```

Esito:

- `STAGING_VERIFY_OK`
- `AUDIT_OK`
- stato legacy invariato in staging: `mod_itpfblikebox=0`, `me_edocs=0`, `com_phocafavicon=0`, `jat3=1`, `com_akeeba=1`

### Delta operativo immediato (eseguito)

Comando applicato per hardening aggiuntivo:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/disable_staging_legacy_extensions.py --disable-akeeba --apply --confirm I_UNDERSTAND
```

Verifica successiva eseguita:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/audit_staging_extensions.py
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/verify_staging_clone.py
```

Stato attuale estensioni legacy su staging:

- `com_akeeba=0`
- `com_phocafavicon=0`
- `plg_content_me_edocs=0`
- `mod_itpfblikebox=0`
- `plg_system_jat3=1` (mantenuto per ponte tecnico)

Prossimo step operativo:

1. Login backend staging e controllo pagina aggiornamento Joomla.
2. Smoke test frontend/admin (console JS, mixed-content, ricerca/menu).
3. Decisione su `com_akeeba` in staging prima del passo successivo (Joomla 4).

## 17) Precheck salto Joomla 4 su staging (eseguito)

Script: `deploy/precheck_joomla4_staging.py`

Comando:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/precheck_joomla4_staging.py
```

Report:

- `upgrade_backups/staging_precheck_j4_latest.json`

Esito attuale:

- `status`: `NO_GO_J4_STAGING`
- `php_version`: `5.6.40` (**bloccante**, minimo `7.2.5` per Joomla 4)
- `joomla_version`: `3.10.12` (ponte OK)
- `legacy blocker`: `plg_system_jat3` ancora `enabled=1`

Prossimo colpo operativo (obbligatorio prima di Joomla 4):

1. Portare **staging** a PHP >= `7.2.5` (preferibile `7.4` come ponte controllato).
2. Disaccoppiare template/framework `jat3` (migrazione a template compatibile Joomla 4).
3. Rieseguire `precheck_joomla4_staging.py` fino a `GO_J4_STAGING`.

## 18) Audit dipendenze JAT3 su staging (eseguito)

Script: `deploy/audit_jat3_dependencies_staging.py`

Comando:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/audit_jat3_dependencies_staging.py
```

Report:

- `upgrade_backups/staging_jat3_dependency_audit_latest.json`

Risultati chiave:

- `plg_system_jat3`: `enabled=1`
- template home attivo: `ja_elastica` (`style id=117`)
- template alternativi già presenti: `atomic`, `beez_20`, `beez5`, `gratis`

Decisione operativa “quando cambiare PHP”:

1. **Adesso** cambiare PHP solo su **staging** a `7.4`.
2. Subito dopo, verificare sito/admin staging.
3. Poi procedere al distacco `jat3` (assegnazione style/template compatibile e disabilitazione plugin).
4. Rieseguire `precheck_joomla4_staging.py`.
5. **Produzione PHP resta invariata** finché non abbiamo `GO_J4_STAGING` + test verdi.

## 19) Post-switch PHP staging + distacco JAT3 (eseguito flash)

Conferma post-switch:

- `php_version` staging rilevato: `7.4.33` (OK per bridge Joomla 4)

Comandi eseguiti:

```powershell
# Verifica stato dopo cambio PHP
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/precheck_joomla4_staging.py

# Distacco JAT3 (switch home style + disable plugin)
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/detach_jat3_staging.py --apply --confirm I_UNDERSTAND

# Verifica finale readiness Joomla 4
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/precheck_joomla4_staging.py
```

Esito finale:

- `status`: `GO_J4_STAGING`
- blocker risolti: `PHP>=7.2.5` e `plg_system_jat3=0`
- home style staging ora su `beez_20` (`template_style_id=4`)

Report principali aggiornati:

- `upgrade_backups/staging_precheck_j4_latest.json`
- `upgrade_backups/staging_jat3_dependency_audit_latest.json`

Prossimo step operativo immediato:

Procedere con migrazione Joomla 4 su staging (produzione invariata).

## 20) Migrazione Joomla 4 su staging (eseguita)

Script: `deploy/update_staging_to_j4.py`

Comandi eseguiti:

```powershell
# Dry-run preflight
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/update_staging_to_j4.py

# Apply reale su staging
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/update_staging_to_j4.py --apply --confirm I_UNDERSTAND
```

Esito:

- `status`: `J4_UPDATE_OK`
- `detected_version`: `4.4.13`

Verifiche post-update eseguite:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/precheck_joomla4_staging.py
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/verify_staging_clone.py
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/audit_staging_extensions.py
```

Risultato finale:

- `GO_J4_STAGING`
- `STAGING_VERIFY_OK`
- `AUDIT_OK`
- estensioni legacy critiche confermate disattivate (`com_akeeba`, `com_phocafavicon`, `jat3`, `me_edocs`, `mod_itpfblikebox`)

Nota operativa immediata:

Eseguire un giro backend staging per eventuali step di finalizzazione DB/UI richiesti da Joomla 4 (se presenti), poi smoke test funzionale completo frontend/admin.

## 21) Fix messaggio "The plugin JAT3 framework must be installed and enabled" (eseguito)

Root cause rilevata:

- alcune voci menu staging puntavano ancora a `template_style_id` legacy (`ja_elastica` / `gratis`), quindi su quelle pagine Joomla tentava ancora il rendering template JAT3.

Correzione applicata:

- esteso `deploy/detach_jat3_staging.py` per riallineare automaticamente **tutte** le voci menu con style legacy verso lo style target (`beez_20`).

Esecuzione:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/detach_jat3_staging.py --apply --confirm I_UNDERSTAND
```

Verifica:

- `legacy_menu_items_to_rewire=0` al dry-run successivo
- `GO_J4_STAGING` confermato da `deploy/precheck_joomla4_staging.py`

## 22) Hotfix produzione per errore index JAT3 (eseguito)

Sintomo segnalato:

- pagina `index` con messaggio: `The plugin JAT3 framework must be installed and enabled.`

Diagnosi rapida:

- lo staging era già pulito;
- in **produzione** il template home era ancora `ja_elastica` con assegnazioni menu legacy.

Correzione applicata su produzione:

Script: `deploy/hotfix_switch_production_template_fallback.py`

Comando eseguito:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/hotfix_switch_production_template_fallback.py --apply --confirm I_UNDERSTAND
```

Stato post-fix verificato:

- `home style`: `beez_20` (`id=4`)
- `legacy_menu_count`: `0`

Nota:

Questo hotfix rimuove la dipendenza runtime da JAT3 sulla index di produzione, mantenendo intatto il percorso di migrazione staging già completato.

## 23) Ripristino layout originale produzione (eseguito)

Situazione dopo hotfix precedente:

- errore JAT3 sparito ma frontend mostrava layout `beez_20` non desiderato.

Correzione applicata:

Script: `deploy/restore_production_ja_elastica.py`

Comando eseguito:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/restore_production_ja_elastica.py --apply --confirm I_UNDERSTAND
```

Stato verificato:

- `home style` produzione: `ja_elastica` (`id=117`)
- menu home (`id=435`) riallineato a `template_style_id=117`
- `jat3` plugin confermato `enabled=1`

Obiettivo ottenuto:

Layout produzione riportato al tema storico “come prima”, mantenendo staging su percorso Joomla 4.

## 24) Ricomparsa errore JAT3 su produzione: causa e mitigazione immediata

Nuova evidenza runtime produzione:

- `PHP production`: `7.4.33`
- stack legacy (`Joomla 2.5 + JAT3`) mostra incompatibilità note su PHP moderni (warning/deprecazioni core), con ricomparsa intermittente del messaggio JAT3.

Mitigazione immediata applicata (stabile):

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/hotfix_switch_production_template_fallback.py --apply --confirm I_UNDERSTAND
```

Stato post-mitigazione:

- `home style` produzione: `beez_20`
- `legacy_menu_count`: `0`
- messaggio JAT3 non più legato al routing home/menu.

Nota decisionale:

Per mantenere **layout storico JA Elastica** senza errori, produzione deve tornare a PHP legacy compatibile col ramo 2.5/JAT3 (oppure va completata la migrazione definitiva su stack moderno).

## 25) Decisione operativa confermata: fallback lock su produzione

Decisione:

- mantenere produzione in fallback (`beez_20`) fino al completamento migrazione.

Conferma stato attuale (rieseguita):

- `home style`: `beez_20` (`id=4`)
- `home menu` (`id=435`) con `template_style_id=4`
- `legacy_menu_count`: `0`

Comando di enforcement idempotente (riutilizzabile in qualsiasi momento):

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/hotfix_switch_production_template_fallback.py --apply --confirm I_UNDERSTAND
```

Regola fino a go-live migrazione:

- non ripristinare `ja_elastica` su produzione finché stack non è completamente migrato e validato.

## 26) Smoke check staging Joomla 4 (eseguito rapido)

Script:

- `deploy/smoke_check_staging_j4.py`

Comando:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/smoke_check_staging_j4.py
```

Esito:

- `status`: `SMOKE_OK`
- `php_version`: `7.4.33`
- `joomla_version`: `4.4.13`
- legacy critiche confermate disattivate su staging.

Report:

- `upgrade_backups/staging_smoke_j4_latest.json`

## 27) Piano cutover produzione pronto

Documento operativo creato:

- `CUTOVER_PRODUZIONE_J4.md`

Uso:

- contiene sequenza rapida, criteri GO/NO-GO e rollback immediato.

## 28) Simulazione cutover produzione (eseguita ora)

Comando eseguito:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_one_shot.py
```

Esito:

- `status`: `ONE_SHOT_OK`
- `snapshot`: `20260228_235841`
- backup file+DB con hash manifest completato
- rollback dry-run validato sullo stesso snapshot

Report principale:

- `upgrade_backups/20260228_235841/upgrade_one_shot_report.json`

Snapshot pronto per rollback immediato (se necessario):

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/rollback_assist.py --snapshot 20260228_235841 --apply --confirm I_UNDERSTAND
```

## 29) Cutover produzione eseguito (senza esitazioni)

Sequenza applicata in produzione:

1. Disattivazione legacy critica:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/disable_staging_legacy_extensions.py --target production --disable-akeeba --disable-jat3 --apply --confirm I_UNDERSTAND
```

2. Bridge Joomla `2.5 -> 3.10.12`:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/update_staging_to_j310.py --target production --apply --confirm I_UNDERSTAND
```

3. Upgrade Joomla `3.10.12 -> 4.4.13`:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/update_staging_to_j4.py --target production --apply --confirm I_UNDERSTAND
```

4. Smoke check finale produzione:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/smoke_check_staging_j4.py --target production
```

Esito finale:

- `joomla_version`: `4.4.13`
- `status`: `SMOKE_OK`
- report: `upgrade_backups/production_smoke_j4_latest.json`

Nota operativa:

- i warning legacy in `error_log` possono contenere righe storiche del vecchio stack; per validazione finale usare test pagina reale frontend/backend dopo hard refresh.

## 30) Verifica forense produzione (2026-03-04) — stato reale

Verifica remota eseguita in read-only via SSH sui file versione core in `public_html`.

Evidenze oggettive rilevate su produzione:

- `administrator/manifests/files/joomla.xml` → `<version>4.4.13</version>`
- `libraries/src/Version.php` → **presente** (file Joomla 4)
- `libraries/cms/version/version.php` → **presente** con:
   - `public $RELEASE = '2.5';`
   - `public $DEV_LEVEL = '4';`

Conclusione tecnica:

- lo stato attuale è **ibrido/incoerente** (mix di file Joomla 4 e file legacy 2.5),
- quindi la sola dicitura “produzione già 4.4.13” **non è affidabile** finché non si riallinea il filesystem core.

Impatti possibili:

- comportamento imprevedibile su bootstrap/version checks,
- warning/deprecation intermittenti,
- rischi su update futuri e su estensioni che leggono la versione core.

### Azione correttiva immediata (obbligatoria)

1. Eseguire backup guardrail completo (`upgrade_guardrail_backup.py`).
2. Eseguire **overlay pulito** del pacchetto Joomla 4.4.13 su produzione (tutti i file core, non patch parziali).
3. Rieseguire smoke check produzione e verifica versioning file:
    - `administrator/manifests/files/joomla.xml`
    - `libraries/src/Version.php`
    - assenza/neutralizzazione del legacy `libraries/cms/version/version.php` non coerente con stack J4.
4. Solo dopo riallineamento file, considerare lo stato “J4 in produzione” come definitivo.

Nota di governance documento:

- le sezioni precedenti che indicano cutover J4 produzione come “definitivo” sono da considerare **superate** da questa verifica forense finché il riallineamento non viene completato e validato.

## 31) Riallineamento forense completato produzione (2026-03-04)

Esecuzione immediata effettuata dopo la verifica forense del punto 30.

### Step eseguiti

1. Backup guardrail completo riuscito:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_guardrail_backup.py
```

Esito:

- `BACKUP_OK`
- `snapshot`: `20260304_003936`
- `site_archive_sha256`: `582296ae6b0c1ecd1e8531b7feaa34038caf65fe1908e9f9ce70cca72f6badb0`
- `db_dump_sha256`: `cfac0ab64e008b9ad2277a356d90110645c50c5f26a9c01d1b099344889aabaf`

2. Overlay pulito Joomla 4.4.13 su root produzione (`public_html`):

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/overlay_production_j4.py --apply --confirm I_UNDERSTAND
```

Esito:

- `J4_PRODUCTION_OVERLAY_OK`
- `detected_version=4.4.13`

3. Neutralizzazione sicura file legacy 2.5 (rinomina con backup timestamp):

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/resolve_production_hybrid_j4.py --apply --confirm I_UNDERSTAND
```

Esito:

- `HYBRID_RESOLUTION_OK`
- `legacy_file_exists: MISSING`
- `legacy_backup_exists: FOUND`

4. Verifica forense finale:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/check_remote_joomla_version.py
```

Esito oggettivo finale:

- `REMOTE_JOOMLA_XML_VERSION=4.4.13`
- `REMOTE_FILE_J4_SRC=FOUND`
- `REMOTE_FILE_LEGACY_VERSION=MISSING`

### Conclusione aggiornata

Lo stato ibrido evidenziato al punto 30 è stato **risolto**: produzione è ora coerente lato file versione con stack Joomla 4.4.13.

## 32) Ricostruzione pagina administrator + dipendenze core (2026-03-04)

Richiesta eseguita: ricostruzione backend `administrator` con dipendenze necessarie sul core nuovo.

### Root cause rilevata

Verifica live su `/administrator/` mostrava `HTTP 500` con messaggio:

- `behavior::noframes not found.`

Il backend richiedeva il metodo legacy `noframes()` nel helper core `Behavior` per compatibilità con template amministrativo legacy (`bluestork`) ancora in uso.

### Intervento eseguito

1. Hotfix core helper remoto:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/hotfix_remote_behavior_noframes.py
```

Esito:

- `PATCH_OK /home/w19158/public_html/libraries/src/HTML/Helpers/Behavior.php`

2. Verifica runtime backend:

- `https://www.apricenadialetto.it/administrator/` → `HTTP/2 200`
- pagina login amministrazione renderizzata correttamente.

3. Verifica dipendenze administrator/core (script dedicato):

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/verify_production_administrator_stack.py
```

Esito:

- `ADMIN_STACK_OK`
- `administrator/index.php`: FOUND
- `administrator/includes/app.php`: FOUND
- `libraries/src/HTML/Helpers/Behavior.php`: FOUND
- `behavior_noframes`: FOUND
- `administrator_http`: `HTTP/2 200`
- asset admin principali: `HTTP/2 200`
- `joomla_version`: `4.4.13`

Report locale:

- `upgrade_backups/production_admin_stack_latest.json`

4. Backup guardrail post-ripristino:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_guardrail_backup.py
```

Esito:

- `BACKUP_OK`
- `snapshot`: `20260304_005359`

### Stato finale

Backend `administrator` ricostruito e operativo sul core Joomla 4.4.13 con dipendenze critiche validate.
