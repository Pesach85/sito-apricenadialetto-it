# Cutover Produzione Joomla 4 (run rapido)

## Prerequisiti (obbligatori)

- Staging in stato `GO_J4_STAGING`.
- Report smoke aggiornato: `upgrade_backups/staging_smoke_j4_latest.json` con `SMOKE_OK`.
- Finestra manutenzione concordata.
- Backup guardrail eseguito e verificato (`BACKUP_OK`).

## Sequenza operativa

1. Bloccare modifiche contenuto lato produzione durante finestra.
2. Eseguire backup completo:

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/upgrade_guardrail_backup.py
```

3. Applicare piano migrazione file+DB verso stack Joomla 4 (riuso pacchetto e script collaudati su staging).
4. Pulire cache (`cache/`, `tmp/`) e verificare accesso backend/admin.
5. Eseguire smoke check post-cutover (home, login admin, pagine chiave, console browser).

## GO/NO-GO

GO se:
- homepage e pagine chiave caricano senza fatal,
- login admin OK,
- errori critici assenti su `error_log`.

NO-GO se:
- homepage non accessibile,
- backend non accessibile,
- errori fatali persistenti.

## Rollback immediato

```powershell
D:/Sito_apricenadialetto.it/.venv/Scripts/python.exe deploy/rollback_assist.py --snapshot <SNAPSHOT_ID> --apply --confirm I_UNDERSTAND
```

## Nota fallback

Fino al cutover completo, produzione resta in fallback (`beez_20`) per stabilità.
