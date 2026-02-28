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
