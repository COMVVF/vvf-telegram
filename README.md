# Bot Telegram VVF — guida di attivazione

Bot informativo non ufficiale per un gruppo di funzionari. Python senza dipendenze aggiuntive, GitHub Actions su runner Linux standard in repository pubblico. Nessun servizio AI a pagamento. Controllo ogni 5 minuti; GitHub può ritardare o saltare un'esecuzione. Non è un servizio di allerta urgente garantito.

## 1. Crea il bot
1. In Telegram apri https://t.me/BotFather (account ufficiale verificato).
2. Invia `/newbot`.
3. Nome suggerito: `VVF – Aggiornamenti funzionari`.
4. Username suggerito: `VVF_Aggiornamenti_Funzionari_bot`. Se già occupato aggiungi una sigla, mantenendo il suffisso `bot`.
5. Conserva il token ricevuto. NON pubblicarlo nel codice, nel gruppo o nella chat con l'assistente.
6. Facoltativo: `/setdescription` → `Bot informativo non ufficiale. Aggiornamenti da fonti pubbliche VVF per funzionari. Verificare sempre il documento originale.`
7. Con `/setjoingroups` scegli il bot e abilita l'aggiunta ai gruppi, se disabilitata. Lascia la privacy attiva: il bot non deve leggere la conversazione ordinaria.

## 2. Inserisci il bot nel gruppo
Apri il gruppo → nome del gruppo → Aggiungi membri → cerca lo username del bot. Deve poter inviare messaggi. Non serve renderlo amministratore se il gruppo consente ai membri di scrivere. Questa versione funziona nei gruppi, non nei canali e non gestisce argomenti/topic separati.

## 3. Crea il progetto cloud
1. Accedi o registrati su https://github.com.
2. `+` → `New repository` → nome `vvf-telegram` → **Public** → Create repository.
3. Estrai il pacchetto ZIP. Carica `bot.py`, `sources.json`, `test_bot.py` e `README.md` nella radice: `Add file` → `Upload files` → Commit changes.
4. Crea il workflow: `Add file` → `Create new file`; scrivi come nome `.github/workflows/vvf.yml`. Incolla il contenuto del file `vvf.yml` del pacchetto e salva con Commit changes. In alternativa carica la cartella `.github` verificando che il percorso resti esattamente quello indicato.
5. Il branch predefinito deve contenere tutti i file. Non caricare l'intera cartella `vvf-telegram` dentro un'altra cartella del repository.
6. `Settings` → `Actions` → `General` → `Workflow permissions` → **Read and write permissions** → Save. Se un criterio dell'organizzazione impedisce la scrittura, usare un repository personale o chiedere all'amministratore.

## 4. Inserisci il token come Secret
Repository → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`.
Nome: `TELEGRAM_BOT_TOKEN`. Valore: token di BotFather. Add secret.
Il repository pubblico contiene solo codice e stato delle fonti: il token e l'ID gruppo devono stare esclusivamente nei Secrets. I log Actions sono pubblici: non inserire dati riservati nei comandi o nei messaggi di debug.

## 5. Ottieni l'ID gruppo senza siti esterni
1. Nel gruppo invia `/id@USERNAME_DEL_BOT` usando lo username effettivo (senza duplicare @).
2. Entro 24 ore: repository → `Actions` → `VVF Telegram` → `Run workflow` → mode **connect** → Run workflow.
3. Il bot risponde nel gruppo con l'ID, normalmente un numero negativo. Il programma non stampa l'ID nei log pubblici.
4. Aggiungi un secondo Secret: `TELEGRAM_CHAT_ID`, con l'intero numero ricevuto, segno meno incluso.
5. Se connect non trova il comando, rispediscilo e ripeti. Se compare Telegram HTTP 409, il token è usato da un altro programma o webhook: usare un nuovo bot dedicato oppure disattivare l'altra integrazione. Non eseguire due programmi sul medesimo token.

## 6. Test e attivazione
1. Actions → VVF Telegram → Run workflow → mode **test**. Deve comparire un messaggio di prova nel gruppo.
2. Run workflow → mode **monitor**. La prima esecuzione crea `state.json` registrando i contenuti già presenti **senza inviarli**.
3. Controlla la spunta verde e i conteggi di tutte le fonti nel log. Il workflow controllerà poi le fonti ogni 5 minuti circa; non occorre lasciare il PC acceso.
4. Non eliminare `state.json`: contiene la memoria degli invii. Il commit dello stato deve riuscire; altrimenti gli invii potrebbero ripetersi. Non applicare protezioni del branch che impediscano questi commit.
5. I workflow pubblici possono essere disabilitati dopo 60 giorni senza attività del repository. Se non vi sono nuovi contenuti per lungo tempo, controlla Actions e riabilita la pianificazione. Configura in GitHub le notifiche di errore Actions.

## Categorie e copertura reale
Sono configurate Normativa e prevenzione incendi, Soccorso tecnico e procedure operative, Circolari del Dipartimento, Formazione e personale, Concorsi e mobilità, Notizie istituzionali. Le etichette derivano da parole chiave, non da una valutazione giuridica o da AI. È possibile un falso positivo o una notizia non riconosciuta: modificare le parole chiave in `category()` dopo aver osservato i risultati.

Fonti: RSS pubblico ufficiale VVF `/news/rss.xml`; pagine di prevenzione incendi, quesiti, norme, testi coordinati e concorsi pubblici, elencate in `sources.json`. Il feed include anche notizie locali: il filtro ne esclude molte, ma non tutte. Concorsi e mobilità sono rilevati soltanto quando pubblicati nelle fonti monitorate. Nessun accesso a intranet, circolari riservate o credenziali istituzionali. Non è monitorata tutta la Gazzetta Ufficiale.

Ogni messaggio contiene categoria, titolo, eventuale breve estratto del feed, data se fornita e link ufficiale. Le pagine senza data non ricevono una data di pubblicazione inventata. I documenti PDF sono segnalati tramite link: il bot **non legge il PDF**. Rileva nuovi collegamenti o variazioni del titolo/estratto; la sostituzione di un PDF allo stesso URL e con lo stesso titolo non viene rilevata. Le pagine monitorate e il feed hanno una finestra limitata: contenuti aggiunti e rimossi tra due controlli possono sfuggire.

Gli URL già visti sono condivisi tra fonti. Un link nuovo su una fonte già inizializzata produce un avviso; non significa necessariamente che il documento sia stato appena emanato. Una nuova fonte aggiunta viene inizializzata senza inviare lo storico.

## Verifiche e limiti tecnici
Test: `python -m unittest -q`. Simulazione senza invii o modifica dello stato: `python bot.py --mode dry-run`. Il codice è verificabile con Python 3.12. I test coprono prima inizializzazione, duplicati, variazione del contenuto e fallimento dell'invio. La prova reale Telegram richiede i tuoi Secrets.

Invio Telegram e commit GitHub non sono una transazione unica: in caso di interruzione dopo un invio ma prima del salvataggio/commit può esserci un duplicato. Il bot evita retry automatici di invii dall'esito incerto. Le fonti che non rispondono non sono segnate come inizializzate; il workflow termina in errore e le riprova al prossimo controllo.

## Problemi frequenti
- HTTP 401: token errato/revocato. Aggiornare TELEGRAM_BOT_TOKEN.
- HTTP 400: controllare TELEGRAM_CHAT_ID e presenza del bot nel gruppo.
- HTTP 403: bot rimosso o senza permesso di scrittura.
- Fonte in errore: indisponibilità temporanea o struttura del sito cambiata; controllare URL e parser.
- git push fallito: consentire la scrittura del workflow e verificare le regole del branch.
- Nessuna notizia: normale dopo inizializzazione; verificare esecuzioni verdi e fonte pubblica effettivamente aggiornata.
- Migrazione del gruppo a supergruppo: ripetere connect e aggiornare il Secret con il nuovo ID.

## Arresto e sicurezza
Actions → VVF Telegram → menu con tre punti → Disable workflow. Per revocare un token esposto: BotFather → `/revoke`, quindi sostituirlo nel Secret. Questo pacchetto è pronto per la configurazione ma non è attivo nel tuo account prima dei passaggi sopra.

Documentazione ufficiale:
- https://core.telegram.org/bots/tutorial
- https://core.telegram.org/bots/api
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
