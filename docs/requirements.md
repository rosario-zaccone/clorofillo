# Requisiti Sistema Vaso Smart

## Configurazione
- **REQ-01** L’utente deve poter configurare la connessione Wi-Fi del Raspberry e il bot tramite smartphone via Bluetooth.  
- **REQ-02** Il sistema deve supportare tre vasi.  

## Irrigazione
- **REQ-03** L’utente deve poter configurare l’irrigazione di ciascun vaso (soglia umidità, taglia vaso per calcolare la durata, modalità).  
- **REQ-04** Il sistema deve poter irrigare automaticamente i vasi.  
- **REQ-05** L’utente deve poter visualizzare l’umidità.  
- **REQ-06** Il sistema deve notificare in caso di serbatoio vuoto.  
- **REQ-16** L'utente deve poter attivare l'irrigazione a comando.

## Timelapse & direzione crescita
- **REQ-07** L’utente deve poter configurare la frequenza di scatto per il timelapse (max 1 scatto/ora).  
- **REQ-08** L’utente, dato un intervallo di date, deve poter visualizzare il relativo timelapse.  
- **REQ-09** L’utente deve poter conoscere la direzione di crescita delle piante.  

## Insetti
- **REQ-10** L’utente deve poter configurare la frequenza di scatto per l’identificazione di insetti (max 1 ogni 5 s, min 1 ogni 40 s, oppure nessuna foto in caso di disattivazione della funzinalità); queste foto sono scartate a lungo termine.  
- **REQ-11** Il sistema deve poter individuare possibili insetti confrontando la foto appena scattata con la precedente; poi deve chiedere conferma all’utente e, se confermato, usare API per identificare l’insetto.  
- **REQ-12** L’utente deve poter visualizzare il diario degli insetti.  

## Fioriture
- **REQ-13** Il sistema deve poter individuare le fioriture.  
- **REQ-14** L’utente deve poter visualizzare il diario delle fioriture.  

## Sistema
- **REQ-15** Il sistema deve visualizzare un messaggio in caso di errore.  
