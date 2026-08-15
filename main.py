import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os
import random
from datetime import timedelta
import feedparser

# --- KONFIGURACJA ---
TOKEN = os.getenv("TOKEN")
GUILD_ID_STR = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID_STR) if GUILD_ID_STR else 0

OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else 0

user_balances = {}
yt_subscriptions = {}

def is_owner():
    async def predicate(interaction: discord.Interaction):
        if OWNER_ID != 0 and interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Tylko właściciel bota może używać tej komendy!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class ZaawansowanyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(MainPanelView())
        self.add_view(WyborOfertyView())
        self.add_view(TicketCloseView())
        self.add_view(OpiniePanelView())
        
        check_youtube_videos.start()

        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("✅ Zsynchronizowano komendy dla serwera testowego!")
        else:
            await self.tree.sync()

bot = ZaawansowanyBot()

@bot.event
async def on_ready():
    print(f"🤖 Zalogowano jako: {bot.user}")

@tasks.loop(minutes=1)
async def check_youtube_videos():
    for guild_id, data in yt_subscriptions.items():
        channel_id = data["channel_id"]
        yt_id = data["yt_id"]
        yt_kanal = data["yt_kanal"]
        yt_link = data["yt_link"]
        yt_wiadomosc = data["yt_wiadomosc"]
        last_video = data["last_video"]

        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={yt_id}"
        feed = feedparser.parse(rss_url)

        if feed.entries:
            latest = feed.entries[0]
            video_id = latest.id.split(":")[-1]
            video_title = latest.title
            video_link = latest.link

            if video_id != last_video:
                yt_subscriptions[guild_id]["last_video"] = video_id
                
                channel = bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                        title=video_title,
                        url=video_link,
                        color=discord.Color.from_rgb(255, 0, 0),
                    )
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                    embed.set_image(url=thumbnail_url)
                    embed.set_author(
                        name=yt_kanal,
                        icon_url="https://www.iconpacks.net/icons/2/free-youtube-logo-icon-2431-thumb.png",
                        url=yt_link
                    )
                    embed.set_footer(text="YouTube • Powiadomienie o nowym filmie", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png")

                    view = ui.View()
                    view.add_item(ui.Button(label="Oglądaj na YouTube", url=video_link, style=discord.ButtonStyle.link, emoji="▶️"))

                    tekst_wysylki = yt_wiadomosc if yt_wiadomosc else "🔔 **Nowy film pojawił się na kanale!** Sprawdź go koniecznie:"
                    await channel.send(content=tekst_wysylki, embed=embed, view=view)

@check_youtube_videos.before_loop
async def before_check_youtube():
    await bot.wait_until_ready()

@bot.event
async def on_member_join(member: discord.Member):
    try:
        embed = discord.Embed(
            title="HAKEROLANDIA — WITAMY",
            description=(
                f"Hej **{member.mention},** miło Cię widzieć na serwerze **Hakerolandia.**\n\n"
                "🛡️ **Musisz się zweryfikować.** — Przejdź na odpowiedni kanał weryfikacyjny i kliknij w przycisk.\n"
                "🛒 **Chcesz coś zamówić?** — Po zweryfikowaniu się przejdź na kanał sklepu.\n\n"
                "Dołącz do **najlepszej ekipy i korzystaj z promocji,** zanim ktoś inny zgarnie je pierwszy!"
            ),
            color=discord.Color.blurple()
        )
        await member.send(embed=embed)
    except discord.Forbidden:
        pass

class ZamowienieModal(ui.Modal):
    def __init__(self, pakiet_nazwa: str, cena_wyjsciowa: float):
        super().__init__(title="POTRZEBNE INFORMACJE.")
        self.pakiet_nazwa = pakiet_nazwa
        self.cena_wyjsciowa = cena_wyjsciowa

    nick_dc = ui.TextInput(label="JAKI JEST TWOJ NICK NA DISCORDZIE:", placeholder="Podaj swoj nick z discorda.", required=True, max_length=50)
    platnosc_text = ui.TextInput(label="WYBIERZ PLATNOSC (BLIK / REVOLUT):", placeholder="Wpisz wybrana metode platnosci", required=True, max_length=30)
    kod_znizkowy = ui.TextInput(label="CZY POSIADASZ KOD ZNIZKOWY:", placeholder="Przyklad: HAKERROBLOX", required=False, max_length=20)
    uwagi = ui.TextInput(label="DODATKOWE UWAGI DO ZAMOWIENIA:", placeholder="Opisz swoje wymagania", style=discord.TextStyle.paragraph, required=False, max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        wybrana_platnosc = self.platnosc_text.value.strip()
        cena_ostateczna = self.cena_wyjsciowa
        rabat_info = "Brak"

        if self.kod_znizkowy.value.strip().lower() == "hakerroblox":
            cena_ostateczna = self.cena_wyjsciowa * 0.95
            rabat_info = "HakerRoblox (-5% znizki)"

        embed = discord.Embed(title="🟢 POTWIERDZENIE ZAMOWIENIA", description="Twoje zgloszenie zamowienia zostalo zapisane.", color=discord.Color.green())
        embed.add_field(name="📦 Wybrana usluga:", value=f"• **1x {self.pakiet_nazwa}**", inline=False)
        embed.add_field(name="💰 Cena:", value=f"**{cena_ostateczna:.2f} zl**", inline=False)
        embed.add_field(name="👤 Nick Discord:", value=self.nick_dc.value, inline=True)
        embed.add_field(name="💳 Platnosc:", value=wybrana_platnosc, inline=True)
        embed.add_field(name="🎟️ Kod rabatowy:", value=rabat_info, inline=False)
        if self.uwagi.value:
            embed.add_field(name="📝 Dodatkowe uwagi:", value=self.uwagi.value, inline=False)

        view = ui.View()
        view.add_item(ui.Button(label="Oplac zamowienie", url="https://tipply.pl/@hakerroblox", style=discord.ButtonStyle.link, emoji="💳"))
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class PakietSelect(ui.Select):
    def __init__(self):
        opcje = [
            discord.SelectOption(label="Pakiet START — 19,99 zl", description="Max 10 kategorii / 30 kanalow", emoji="🟢", value="start"),
            discord.SelectOption(label="Pakiet BASIC — 39,99 zl", description="Max 20 kategorii / 50 kanalow", emoji="🔵", value="basic"),
            discord.SelectOption(label="Pakiet PREMIUM — 69,99 zl", description="Nielimitowane kategorie i kanaly", emoji="🟣", value="premium"),
        ]
        super().__init__(placeholder="Wybierz pakiet z menu...", min_values=1, max_values=1, options=opcje, custom_id="wybor_pakietu_select")

    async def callback(self, interaction: discord.Interaction):
        wybor = self.values[0]
        if wybor == "start":
            await interaction.response.send_modal(ZamowienieModal("Pakiet START", 19.99))
        elif wybor == "basic":
            await interaction.response.send_modal(ZamowienieModal("Pakiet BASIC", 39.99))
        elif wybor == "premium":
            await interaction.response.send_modal(ZamowienieModal("Pakiet PREMIUM", 69.99))

class WyborOfertyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PakietSelect())

class MainPanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Zloz zamowienie", style=discord.ButtonStyle.secondary, custom_id="przycisk_zamowienia", emoji="🛒")
    async def start_order(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="🟢 KATALOG OFERT — HAKEROLANDIA",
            description="Wybierz interesujacy Cie pakiet z menu ponizej:",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, view=WyborOfertyView(), ephemeral=True)

class TicketCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Zamknij ticket", style=discord.ButtonStyle.danger, custom_id="zamknij_ticket_btn", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Nie masz uprawnień do zamykania ticketów", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await interaction.channel.delete()

class TicketPanelView(ui.View):
    def __init__(self, rola_id: int = None):
        super().__init__(timeout=None)
        self.rola_id = rola_id

    @ui.button(label="Otworz Ticket", style=discord.ButtonStyle.primary, custom_id="otworz_ticket_btn", emoji="📩")
    async def open_t(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        }
        if self.rola_id:
            rola = interaction.guild.get_role(self.rola_id)
            if rola:
                overwrites[rola] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ch = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title="CENTRUM POMOCY — HAKEROLANDIA", description=f"Witaj {interaction.user.mention}! Administracja wkrótce odpowie.", color=discord.Color.blue())
        await ch.send(embed=embed, view=TicketCloseView())
        await interaction.followup.send(f"✅ Utworzono ticket: {ch.mention}", ephemeral=True)

class CaptchaModal(ui.Modal):
    def __init__(self, rola_id: int, correct_answer: int, equation_str: str):
        super().__init__(title="WERYFIKACJA BEZPIECZENSTWA")
        self.rola_id, self.correct_answer = rola_id, correct_answer
        self.answer_input = ui.TextInput(label=f"Wynik: {equation_str}", placeholder="Wpisz wynik", required=True, max_length=5)
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            val = int(self.answer_input.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Wynik musi być liczbą!", ephemeral=True)
            return
        if val == self.correct_answer:
            rola = interaction.guild.get_role(self.rola_id)
            if rola:
                await interaction.user.add_roles(rola)
                await interaction.followup.send("✅ Zweryfikowano pomyślnie!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Błędny wynik!", ephemeral=True)

class WeryfikacjaView(ui.View):
    def __init__(self, rola_id: int = None):
        super().__init__(timeout=None)
        self.rola_id = rola_id

    @ui.button(label="Zweryfikuj sie", style=discord.ButtonStyle.success, custom_id="przycisk_weryfikacji", emoji="🛡️")
    async def verify(self, interaction: discord.Interaction, button: ui.Button):
        n1, n2 = random.randint(1, 10), random.randint(1, 10)
        await interaction.response.send_modal(CaptchaModal(self.rola_id, n1 + n2, f"{n1} + {n2} = ?"))

class OpinieModal(ui.Modal):
    def __init__(self):
        super().__init__(title="WYSTAW OPINIE")

    wykonawca = ui.TextInput(label="WYKONAWCA USLUGI:", placeholder="Np. HakerRoblox (haker.roblox)", required=True, max_length=100)
    tresc = ui.TextInput(label="TRESC OPINII:", placeholder="Napisz co sądzisz o usłudze...", style=discord.TextStyle.paragraph, required=True, max_length=500)
    jakosc = ui.TextInput(label="JAKOSC I WYKONANIE (1-5):", placeholder="Wpisz cyfrę od 1 do 5", required=True, max_length=1)
    czas = ui.TextInput(label="CZAS REALIZACJI (1-5):", placeholder="Wpisz cyfrę od 1 do 5", required=True, max_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            val_jakosc = int(self.jakosc.value.strip())
            val_czas = int(self.czas.value.strip())
            if not (1 <= val_jakosc <= 5) or not (1 <= val_czas <= 5):
                raise ValueError()
        except ValueError:
            await interaction.followup.send("❌ Oceny jakości i czasu muszą być cyframi od 1 do 5!", ephemeral=True)
            return

        gwiazdki_jakosc = "⭐" * val_jakosc
        gwiazdki_czas = "⭐" * val_czas

        embed = discord.Embed(color=discord.Color.from_rgb(30, 144, 255))
        embed.set_author(name=f"{interaction.guild.name} × OPINIA", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        opis_opinii = (
            f"» **Twórca opinii:** {interaction.user.mention}\n"
            f"» **Wykonawca usługi:** {self.wykonawca.value}\n"
            f"» **Treść opinii:** {self.tresc.value}\n\n"
            f"» **Jakość i Wykonanie Usługi:** {gwiazdki_jakosc} ({val_jakosc}/5)\n"
            f"» **Czas Realizacji Zamówienia:** {gwiazdki_czas} ({val_czas}/5)"
        )
        embed.description = opis_opinii
        embed.set_footer(text="Hakerolandia • System Opinii")

        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Twoja opinia została pomyślnie wysłana!", ephemeral=True)

class OpiniePanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Wystaw Opinie", style=discord.ButtonStyle.success, custom_id="przycisk_wystaw_opinie", emoji="⭐")
    async def open_opinie_modal(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(OpinieModal())

@bot.tree.command(name="opinie", description="[Użytkownik] Wystawia opinię o wykonanej usłudze przez formularz")
async def cmd_opinie(interaction: discord.Interaction):
    await interaction.response.send_modal(OpinieModal())

@bot.tree.command(name="opinie-setup", description="[Właściciel] Wysyła panel z przyciskiem do wystawiania opinii")
@is_owner()
async def cmd_opinie_setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    opis = (
        "» **Wystawiając opinię** pokazujesz innym, jak przebiegła Twoja obsługa.\n"
        "» **Gorąco prosimy** o jej wystawienie, buduje to nasze zaufanie.\n\n"
        "» Zrobisz to klikając **poniższy przycisk**."
    )
    
    embed = discord.Embed(color=discord.Color.from_rgb(30, 144, 255))
    embed.set_author(name=f"{interaction.guild.name} × WYSTAW NAM OPINIĘ", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.description = opis
    
    await interaction.channel.send(embed=embed, view=OpiniePanelView())
    await interaction.followup.send("✅ Wysłano panel opinii.", ephemeral=True)

@bot.tree.command(name="wyslij-panel", description="[Właściciel] Wysyła główny panel sklepu z pełnym opisem i opcjonalnym obrazkiem")
@app_commands.describe(obrazek_url="Bezpośredni link URL do obrazka/bannera (opcjonalnie)")
@is_owner()
async def cmd_wyslij_panel(interaction: discord.Interaction, obrazek_url: str = None):
    await interaction.response.defer(ephemeral=True)
    
    opis = (
        "🖥️ **ZAMÓW SWÓJ SERWER**\n"
        "**HAKEROLANDIA**\n\n"
        "⚠️ **UWAGA!**\n"
        "Zamówienia realizujemy **PO KOLEI** — zgodnie z kolejnością wpłat. ❤️\n\n"
        "🟢 **START — 19,99 zł**\n"
        "• Max 10 kategorii / 30 kanałów\n"
        "• Podstawowe rangi\n"
        "• Lobby\n"
        "• Zabezpieczenia\n"
        "• Własne preferencje\n\n"
        "🔵 **BASIC — 39,99 zł**\n"
        "• Max 20 kategorii / 50 kanałów\n"
        "• Rangi użytkowników i administracji\n"
        "• Ekonomia + sklep\n"
        "• Selfrole\n"
        "• Invite Logger\n"
        "• Lobby + statystyki\n"
        "• Zabezpieczenia\n\n"
        "🟣 **PREMIUM — 69,99 zł**\n"
        "• Nielimitowane kategorie i kanały\n"
        "• Rozbudowane rangi\n"
        "• Ekonomia + sklep\n"
        "• Logi + statystyki\n"
        "• Zaawansowane zabezpieczenia\n"
        "• Lobby + regulamin\n"
        "• Pomoc w rozwoju serwera\n\n"
        "💳 **PŁATNOŚĆ**\n"
        "BLIK • REVOLUT\n\n"
        "⏱️ Realizacja do 48h\n"
        "⭐ Po odbiorze możesz zostawić opinię!\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 **HAKEROLANDIA**\n"
        "Twój pomysł. Nasza realizacja.\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    embed = discord.Embed(description=opis, color=discord.Color.blurple())
    if obrazek_url:
        embed.set_image(url=obrazek_url)

    await interaction.channel.send(embed=embed, view=MainPanelView())
    await interaction.followup.send("✅ Wysłano panel sklepu.", ephemeral=True)

@bot.tree.command(name="ticket-setup", description="[Właściciel] Wysyła panel ticketów")
@app_commands.describe(rola_id="ID roli administracyjnej")
@is_owner()
async def cmd_ticket_setup(interaction: discord.Interaction, rola_id: str = None):
    await interaction.response.defer(ephemeral=True)
    rid = int(rola_id) if rola_id else None
    view = TicketPanelView(rid)
    embed = discord.Embed(title="📩 CENTRUM WSPARCIA", description="Kliknij, aby otworzyć ticket.", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Wysłano panel ticketów.", ephemeral=True)

@bot.tree.command(name="weryfikacja-setup", description="[Właściciel] Wysyła panel weryfikacji")
@app_commands.describe(rola_id="ID roli weryfikacji")
@is_owner()
async def cmd_weryfikacja_setup(interaction: discord.Interaction, rola_id: str):
    await interaction.response.defer(ephemeral=True)
    rid = int(rola_id)
    view = WeryfikacjaView(rid)
    embed = discord.Embed(title="🛡️ WERYFIKACJA", description="Kliknij, aby się zweryfikować.", color=discord.Color.dark_gray())
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Wysłano panel weryfikacji.", ephemeral=True)

@bot.tree.command(name="yt-setup", description="[Właściciel] Ustawia powiadomienia z YouTube")
@app_commands.describe(
    kanal_id_yt="ID kanału YouTube (np. UCxxxx)",
    yt_kanal="Wymagana nazwa Twojego kanału YouTube",
    yt_link="Wymagany link do Twojego kanału YouTube",
    yt_wiadomosc="Opcjonalna wiadomość/ping nad embedem (np. @everyone Nowy film!)"
)
@is_owner()
async def cmd_yt_setup(
    interaction: discord.Interaction, 
    kanal_id_yt: str, 
    yt_kanal: str, 
    yt_link: str, 
    yt_wiadomosc: str = None
):
    await interaction.response.defer(ephemeral=True)
    
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={kanal_id_yt}"
    feed = feedparser.parse(rss_url)
    
    last_vid = ""
    if feed.entries:
        last_vid = feed.entries[0].id.split(":")[-1]

    yt_subscriptions[interaction.guild.id] = {
        "channel_id": interaction.channel.id,
        "yt_id": kanal_id_yt,
        "yt_kanal": yt_kanal,
        "yt_link": yt_link,
        "yt_wiadomosc": yt_wiadomosc,
        "last_video": last_vid
    }

    await interaction.followup.send(
        f"✅ Skonfigurowano powiadomienia dla kanału **{yt_kanal}**!",
        ephemeral=True
    )

@bot.tree.command(name="ping", description="[Info] Sprawdza ping bota")
async def cmd_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! **{round(bot.latency * 1000)} ms**", ephemeral=True)

@bot.tree.command(name="ban", description="[Właściciel] Banuje użytkownika")
@is_owner()
async def cmd_ban(interaction: discord.Interaction, użytkownik: discord.Member, powód: str = "Brak"):
    await użytkownik.ban(reason=powód)
    await interaction.response.send_message(f"🔨 Zbanowano {użytkownik.mention}. Powód: {powód}", ephemeral=True)

@bot.tree.command(name="kick", description="[Właściciel] Wyrzuca użytkownika")
@is_owner()
async def cmd_kick(interaction: discord.Interaction, użytkownik: discord.Member, powód: str = "Brak"):
    await użytkownik.kick(reason=powód)
    await interaction.response.send_message(f"👢 Wyrzucono {użytkownik.mention}. Powód: {powód}", ephemeral=True)

@bot.tree.command(name="mute", description="[Właściciel] Wycisza użytkownika")
@is_owner()
async def cmd_mute(interaction: discord.Interaction, użytkownik: discord.Member, minuty: int, powód: str = "Brak"):
    await użytkownik.timeout(timedelta(minutes=minuty), reason=powód)
    await interaction.response.send_message(f"🔇 Wyciszono {użytkownik.mention} na {minuty} min.", ephemeral=True)

@bot.tree.command(name="czysc", description="[Właściciel] Usuwa wiadomości")
@is_owner()
async def cmd_czysc(interaction: discord.Interaction, ilosc: int):
    await interaction.response.defer(ephemeral=True)
    usuniete = await interaction.channel.purge(limit=ilosc)
    await interaction.followup.send(f"✅ Usunięto {len(usuniete)} wiadomości.", ephemeral=True)

@bot.tree.command(name="portfel", description="[Ekonomia] Sprawdza stan konta")
async def cmd_balance(interaction: discord.Interaction):
    bal = user_balances.get(interaction.user.id, 0)
    await interaction.response.send_message(f"💰 Stan konta: **{bal} monet**.", ephemeral=True)

@bot.tree.command(name="praca", description="[Ekonomia] Zarób monety")
async def cmd_work(interaction: discord.Interaction):
    zarobek = random.randint(30, 150)
    user_balances[interaction.user.id] = user_balances.get(interaction.user.id, 0) + zarobek
    await interaction.response.send_message(f"💼 Zarobiłeś **{zarobek} monet**!")

@bot.tree.command(name="rzut-moneta", description="[4Fun] Rzut monetą")
async def cmd_coinflip(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 Wylosowano: **{random.choice(['Orzeł', 'Reszka'])}**!")

if __name__ == "__main__":
    bot.run(TOKEN)
