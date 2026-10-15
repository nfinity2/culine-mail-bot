# Culine meil → Discord (GitHub Actions)

## Paigaldamine
1. Loo GitHubis **uus public repository** (ära lisa paroole ega `.env` faili). Avaliku repo tavapärased GitHub-hosted Actionsi minutid on tasuta. Kontrolli GitHubi kehtivaid kasutustingimusi.
2. Laadi repo juurkausta `mail_to_discord.py`, `requirements.txt`, `.gitignore`, `.env.example` ja `README.md`. Loo ka `.github/workflows/mail.yml` täpselt samas asukohas. Võid kasutada GitHubi `Add file > Upload files` (peidetud `.github` kataloogi jaoks võib mugavam olla Git või VS Code).
3. Repo **Settings → Secrets and variables → Actions → New repository secret**. Lisa:
   - `MAIL_USER`: sinu päris postkasti aadress (nt info@culine.ee)
   - `MAIL_PASSWORD`: postkasti parool
   - `DISCORD_WEBHOOK_URL`: UUS privaatse Discordi kanali webhook URL
4. Repo **Settings → Actions → General → Workflow permissions**: vali **Read and write permissions** ja salvesta. Kui valik on lukus, peab organisatsiooni admin seda lubama.
5. Repo **Actions → Culine infomeili teavitused → Run workflow**. Esimene käivitus salvestab olemasolevate kirjade viimase UID ja ei saada vanu kirju.
6. Saada uus testkiri ja käivita workflow uuesti; kontrolli Discordi. Edaspidi on ajastus iga 5 minuti järel (GitHub võib käivitamist edasi lükata või ajastatud tööde käivitusi vahele jätta).

## Turvalisus ja piirangud
- Ära laadi üles `.env`, `state.json` ei sisalda paroole ega postkasti aadressi (postkasti võti on SHA-256 räsi), kuid sisaldab viimase kirja UID-d. Avalikus repos on UID avalik.
- Discordi webhooki tuleb käsitleda saladusena. Kui oled URL-i kuskil avaldanud, kustuta vana webhook ja loo uus.
- GitHubi tasuta Actions ei ole garanteeritud 24/7 reaalajateenus. Ajastatud töö võib hilineda ja avaliku repo ajastused võidakse 60 päeva tegevusetuse järel keelata.
- Ebaõnnestunud jooks ei salvesta uut UID-d; järgmine jooks proovib uuesti. Kui Discord sai sõnumi, kuid GitHubi salvestus ebaõnnestus, võib teavitus korduda.
- Ära käivita sama postkasti jaoks Windowsi ja GitHubi boti korraga, muidu võivad teavitused korduda.
- Kui konto parool on ainult tavaline parool, kontrolli teenusepakkujalt, kas saad luua eraldi rakenduseparooli või ainult lugemisõigusega ligipääsu.
