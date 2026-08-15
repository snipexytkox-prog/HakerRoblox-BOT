import os
import random
from datetime import timedelta
import discord
from discord import app_commands, ui
from discord.ext import commands

# Pobieranie danych ze zmiennych środowiskowych Railway
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID_STR = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID_STR) if GUILD_ID_STR else 0

# Pobieranie ID właściciel bota (wklej swoje ID w zmiennych środowiskowych Railway)
OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else 0

# Bazy danych w pamięci
user_balances = {}
user_warnings = {}


# Sprawdzenie czy użytkownik jest właścicielem bota
def is_owner():
    async def predicate(interaction: discord.Interaction):
        if OWNER_ID == 0:
            await interaction.response.send_message(
                "❌ Ostrzeżenie: Nie skonfigurowano zmiennej OWNER_ID na Railway!",
                ephemeral=True,
            )
            return False
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "❌ Tylko właściciel bota może używać tej komendy!",
                ephemeral=True,
            )
            return False
        return True

    return app_commands.check(predicate)


class ZaawansowanyBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        activity = discord.Activity(
            type=discord.ActivityType.watching, name="Nowe Zamówienia"
        )
        super().__init__(
            command_prefix="!",
            intents=intents,
            status=discord.Status.online,
            activity=activity,
        )

    async def setup_hook(self):
        self.add_view(MainPanelView())
        self.add_view(WyborOfertyView())
        self.add_view(TicketCloseView())

        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(
                "✅ Pomyślnie zsynchronizowano natychmiastowe komendy dla serwera testowego!"
            )
        else:
            print(
                "⚠️ OSTRZEŻENIE: Brak zmiennej GUILD_ID! Synchronizacja globalna może potrwać do godziny."
            )
            await self.tree.sync()


bot = ZaawansowanyBot()


@bot.event
async def on_ready():
    print(f"🤖 Zalogowano pomyślnie jako: {bot.user}")


# --- 1. SYSTEM SKLEPU I ZAMÓWIEŃ (BLIK / REVOLUT) ---
class PlatnoscSelect(ui.Select):

    def __init__(self, pakiet_nazwa: str, cena_wyjsciowa: float, nick_dc: str, uwagi: str, kod_znizkowy: str):
        self.pakiet_nazwa = pakiet_nazwa
        self.cena_wyjsciowa = cena_wyjsciowa
        self.nick_dc = nick_dc
        self.uwagi = uwagi
        self.kod_znizkowy = kod_znizkowy

        opcje = [
            discord.SelectOption(
                label="BLIK",
                description="Szybka płatność kodem BLIK",
                emoji="💸",
                value="blik"
            ),
            discord.SelectOption(
                label="REVOLUT",
                description="Płatność za pomocą Revolut",
                emoji="💳",
                value="revolut"
            ),
        ]
        super().__init__(
            placeholder="Wybierz metodę płatności...",
            min_values=1,
            max_values=1,
            options=opcje,
            custom_id="wybor_platnosci_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        wybrana_platnosc = self.values[0].upper()
        cena_ostateczna = self.cena_wyjsciowa
        rabat_info = "Brak"

        wpisany_kod = self.kod_znizkowy.strip()
        if wpisany_kod.lower() == "hakerroblox":
            cena_ostateczna = self.cena_wyjsciowa * 0.95
            rabat_info = "HakerRoblox (-5% zniżki)"
        elif wpisany_kod != "":
            rabat_info = f"Nieznany kod ({wpisany_kod})"

        embed = discord.Embed(
            title="🟢 POTWIERDZENIE ZAMÓWIENIA",
            description="Twoje zgłoszenie zamówienia zostało zapisane.",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="📦 Wybrana usługa:",
            value=f"• **1x {self.pakiet_nazwa}**",
            inline=False,
        )

        if rabat_info.startswith("HakerRoblox"):
            embed.add_field(
                name="💰 Cena:",
                value=f"~~{self.cena_wyjsciowa:.2f} zł~~ ➡️ **{cena_ostateczna:.2f} zł**",
                inline=False,
            )
        else:
            embed.add_field(
                name="💰 Cena:",
                value=f"**{self.cena_wyjsciowa:.2f} zł**",
                inline=False,
            )

        embed.add_field(name="👤 Nick Discord:", value=self.nick_dc, inline=True)
        embed.add_field(name="💳 Płatność:", value=wybrana_platnosc, inline=True)
        embed.add_field(name="🎟️ Kod rabatowy:", value=rabat_info, inline=False)
        if self.uwagi:
            embed.add_field(name="📝 Dodatkowe uwagi:", value=self.uwagi, inline=False)

        view = ui.View()
        view.add_item(
            ui.Button(
                label="Opłać zamówienie",
                url="https://tipply.pl/@hakerroblox",
                style=discord.ButtonStyle.link,
                emoji="💳",
            )
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class PlatnoscView(ui.View):

    def __init__(self, pakiet_nazwa: str, cena_wyjsciowa: float, nick_dc: str, uwagi: str, kod_znizkowy: str):
        super().__init__(timeout=180)
        self.add_item(PlatnoscSelect(pakiet_nazwa, cena_wyjsciowa, nick_dc, uwagi, kod_znizkowy))


class ZamowienieModal(ui.Modal, title="POTRZEBNE INFORMACJE."):

    def __init__(self, pakiet_nazwa: str, cena_wyjsciowa: float):
        super().__init__()
        self.pakiet_nazwa = pakiet_nazwa
        self.cena_wyjsciowa = cena_wyjsciowa

    nick_dc = ui.TextInput(
        label="JAKI JEST TWÓJ NICK NA DISCORDDZIE:",
        placeholder="Podaj swój nick z @.",
        required=True,
        max_length=50,
    )
    kod_znizkowy = ui.TextInput(
        label="CZY POSIADASZ KOD ZNIŻKOWY:",
        placeholder="Przykład: HAKERROBLOX",
        required=False,
        max_length=20,
    )
    uwagi = ui.TextInput(
        label="DODATKOWE UWAGI DO ZAMÓWIENIA:",
        placeholder="Opisz swoje wymagania",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        view = PlatnoscView(
            self.pakiet_nazwa,
            self.cena_wyjsciowa,
            self.nick_dc.value,
            self.uwagi.value,
            self.kod_znizkowy.value
        )
        embed = discord.Embed(
            title="💳 WYBÓR METODY PŁATNOŚCI",
            description="Wybierz metodę płatności (BLIK / REVOLUT) z menu rozwijanego poniżej:",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PakietSelect(ui.Select):

    def __init__(self):
        opcje = [
            discord.SelectOption(
                label="Pakiet START — 19,99 zł",
                description="Max 10 kategorii / 30 kanałów + podstawy",
                emoji="🟢",
                value="start",
            ),
            discord.SelectOption(
                label="Pakiet BASIC — 39,99 zł",
                description="Max 20 kategorii / 50 kanałów + ekonomia",
                emoji="🔵",
                value="basic",
            ),
            discord.SelectOption(
                label="Pakiet PREMIUM — 69,99 zł",
                description="Nielimitowane kategorie i kanały + full opcja",
                emoji="🟣",
                value="premium",
            ),
        ]
        super().__init__(
            placeholder="Wybierz pakiet z menu...",
            min_values=1,
            max_values=1,
            options=opcje,
            custom_id="wybor_pakietu_select",
        )

    async def callback(self, interaction: discord.Interaction):
        wybor = self.values[0]
        if wybor == "start":
            await interaction.response.send_modal(
                ZamowienieModal("Pakiet START", 19.99)
            )
        elif wybor == "basic":
            await interaction.response.send_modal(
                ZamowienieModal("Pakiet BASIC", 39.99)
            )
        elif wybor == "premium":
            await interaction.response.send_modal(
                ZamowienieModal("Pakiet PREMIUM", 69.99)
            )


class WyborOfertyView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PakietSelect())


class MainPanelView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Złóż zamówienie",
        style=discord.ButtonStyle.secondary,
        custom_id="przycisk_zamowienia",
        emoji="🛒",
    )
    async def start_order(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        embed = discord.Embed(
            title="🟢 KATALOG OFERT — HAKEROLANDIA",
            description="Wybierz interesujący Cię pakiet z menu poniżej:",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(
            embed=embed, view=WyborOfertyView(), ephemeral=True
        )


# --- 2. SYSTEM TICKETÓW (Z OBSŁUGĄ ROLI_ID) ---
class TicketCloseView(ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Zamknij ticket",
        style=discord.ButtonStyle.danger,
        custom_id="zamknij_ticket_btn",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nie masz uprawnień do zamykania ticketów.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await interaction.channel.delete()


class TicketPanelView(ui.View):

    def __init__(self, rola_id: int = None):
        super().__init__(timeout=None)
        self.rola_id = rola_id

    @ui.button(
        label="Otwórz Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="otworz_ticket_btn",
        emoji="📩",
    )
    async def open_t(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False
            ),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        }

        if self.rola_id:
            rola = interaction.guild.get_role(self.rola_id)
            if rola:
                overwrites[rola] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                )

        ch = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name}", overwrites=overwrites
        )

        embed = discord.Embed(
            title="CENTRUM POMOCY — HAKEROLANDIA",
            description=f"Witaj {interaction.user.mention}! Masz pytania lub chcesz zamówić serwer? Administracja odpowie najszybciej jak to możliwe.",
            color=discord.Color.blue(),
        )
        await ch.send(embed=embed, view=TicketCloseView())
        await interaction.followup.send(
            f"✅ Utworzono dla Ciebie ticket: {ch.mention}", ephemeral=True
        )


# --- 3. WERYFIKACJA CAPTCHA ---
class CaptchaModal(ui.Modal):

    def __init__(self, rola_id: int, correct_answer: int, equation_str: str):
        super().__init__(title="WERYFIKACJA BEZPIECZEŃSTWA")
        self.rola_id, self.correct_answer = rola_id, correct_answer
        self.answer_input = ui.TextInput(
            label=f"Rozwiąż Działanie: {equation_str}",
            placeholder="Wpisz wynik cyfrą",
            required=True,
            max_length=5,
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            val = int(self.answer_input.value.strip())
        except ValueError:
            await interaction.followup.send(
                "❌ Wynik musi być liczbą całkowitą!", ephemeral=True
            )
            return
        if val == self.correct_answer:
            rola = interaction.guild.get_role(self.rola_id)
            if not rola:
                await interaction.followup.send(
                    "❌ Nie znaleziono skonfigurowanej roli na serwerze.",
                    ephemeral=True,
                )
                return
            if rola in interaction.user.roles:
                await interaction.followup.send(
                    "⚠️ Posiadasz już tę rolę weryfikacji!", ephemeral=True
                )
            else:
                await interaction.user.add_roles(rola)
                await interaction.followup.send(
                    "✅ Weryfikacja zakończona sukcesem! Otrzymałeś dostęp do serwera.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                "❌ Błędny wynik działania! Spróbuj ponownie.", ephemeral=True
            )


class WeryfikacjaView(ui.View):

    def __init__(self, rola_id: int = None):
        super().__init__(timeout=None)
        self.rola_id = rola_id

    @ui.button(
        label="Zweryfikuj się",
        style=discord.ButtonStyle.success,
        custom_id="przycisk_weryfikacji",
        emoji="🛡️",
    )
    async def verify(self, interaction: discord.Interaction, button: ui.Button):
        if not self.rola_id:
            await interaction.response.send_message(
                "❌ Brak przypisanej roli weryfikacji.", ephemeral=True
            )
            return
        n1, n2 = random.randint(1, 10), random.randint(1, 10)
        await interaction.response.send_modal(
            CaptchaModal(self.rola_id, n1 + n2, f"{n1} + {n2} = ?")
        )


# --- 4. FILTR WIADOMOŚCI ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    niedozwolone = ["złe_słowo_testowe"]
    if any(slowo in message.content.lower() for slowo in niedozwolone):
        try:
            await message.delete()
            await message.channel.send(
                f"⚠️ {message.author.mention}, ta treść jest zabroniona na serwerze!",
                delete_after=5,
            )
        except:
            pass
    await bot.process_commands(message)


# =========================================================================
# --- 5. WSZYSTKE KOMENDY ---
# =========================================================================

@bot.tree.command(
    name="wyslij-panel",
    description="[Właściciel] Wysyła główny panel sklepu Hakerolandia",
)
@is_owner()
async def cmd_wyslij_panel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    tresc_panelu = (
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

    embed = discord.Embed(
        description=tresc_panelu, color=discord.Color.from_rgb(114, 137, 218)
    )
    await interaction.channel.send(embed=embed, view=MainPanelView())
    await interaction.followup.send(
        "✅ Pomyślnie wysłano panel sklepu Hakerolandia.", ephemeral=True
    )


@bot.tree.command(
    name="ticket-setup", description="[Właściciel] Wysyła panel ticketów pomocy"
)
@app_commands.describe(
    rola_id="ID roli administracyjnej, która ma widzieć tickety (opcjonalnie)"
)
@is_owner()
async def cmd_ticket_setup(
    interaction: discord.Interaction, rola_id: str = None
):
    await interaction.response.defer(ephemeral=True)

    rid = None
    if rola_id:
        try:
            rid = int(rola_id)
        except ValueError:
            await interaction.followup.send(
                "❌ Podaj poprawne numeryczne ID roli!", ephemeral=True
            )
            return

    view = TicketPanelView(rid)
    bot.add_view(view)

    embed = discord.Embed(
        title="📩 CENTRUM WSPARCIA — HAKEROLANDIA",
        description="Kliknij przycisk poniżej, aby otworzyć ticket i skontaktować się z administracją.",
        color=discord.Color.blue(),
    )
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send(
        "✅ Pomyślnie wysłano panel ticketów.", ephemeral=True
    )


@bot.tree.command(
    name="weryfikacja-setup",
    description="[Właściciel] Wysyła panel weryfikacji użytkowników",
)
@app_commands.describe(rola_id="ID roli przyznawanej po weryfikacji")
@is_owner()
async def cmd_weryfikacja_setup(interaction: discord.Interaction, rola_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        rid = int(rola_id)
    except ValueError:
        await interaction.followup.send(
            "❌ Podaj poprawne ID numeryczne roli!", ephemeral=True
        )
        return
    view = WeryfikacjaView(rid)
    bot.add_view(view)
    embed = discord.Embed(
        title="🛡️ SYSTEM WERYFIKACJI",
        description="Kliknij poniższy przycisk, aby przejść weryfikację antybotową.",
        color=discord.Color.dark_gray(),
    )
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send(
        "✅ Wysłano panel weryfikacji.", ephemeral=True
    )


@bot.tree.command(
    name="pomoc", description="[Info] Wyświetla listę wszystkich dostępnych komend"
)
async def cmd_pomoc(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="📚 POMOC — DOSTĘPNE KOMENDY",
        description="Wszystkie komendy obsługiwane są jako komendy ukośnika (Slash Commands).",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="🛠️ Administracja i Setup (Tylko Właściciel)",
        value="`/wyslij-panel`, `/ticket-setup`, `/weryfikacja-setup`, `/lock`, `/unlock`, `/powoli`",
        inline=False,
    )
    embed.add_field(
        name="🛡️ Moderacja (Tylko Właściciel)",
        value="`/ban`, `/kick`, `/mute`, `/unmute`, `/czysc`, `/warn`, `/ostrzeżenia`",
        inline=False,
    )
    embed.add_field(
        name="📊 Informacje",
        value="`/ping`, `/serwer-info`, `/użytkownik-info`, `/bot-info`, `/avatar`, `/liczba-osób`, `/regulamin`",
        inline=False,
    )
    embed.add_field(
        name="🎮 Zabawa (4Fun)",
        value="`/8ball`, `/rzut-moneta`, `/losuj-liczbe`, `/ocena`, `/żart`, `/przytul`, `/ciastko`",
        inline=False,
    )
    embed.add_field(
        name="💰 Ekonomia",
        value="`/portfel`, `/praca`, `/codzienna-nagroda`, `/przelej`",
        inline=False,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(
    name="regulamin", description="[Info] Wyświetla oficjalny regulamin serwera"
)
async def cmd_regulamin(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 REGULAMIN SERWERA",
        description="⭐ **Baw się dobrze i szanuj innych!**",
        color=discord.Color.gold(),
    )
    embed.add_field(name="🤝 1. Szanuj innych", value="Nie wyzywaj, nie obrażaj i nie prowokuj.", inline=False)
    embed.add_field(name="🛡️ 2. Szanuj administrację", value="Wykonuj polecenia administracji.", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ban", description="[Właściciel] Banuje wybranego użytkownika")
@is_owner()
async def cmd_ban(interaction: discord.Interaction, użytkownik: discord.Member, powód: str = "Brak podanego powodu"):
    await interaction.response.defer(ephemeral=True)
    await użytkownik.ban(reason=powód)
    await interaction.followup.send(f"🔨 Zbanowano użytkownika {użytkownik.mention}. Powód: **{powód}**", ephemeral=True)


@bot.tree.command(name="kick", description="[Właściciel] Wyrzuca użytkownika z serwera")
@is_owner()
async def cmd_kick(interaction: discord.Interaction, użytkownik: discord.Member, powód: str = "Brak podanego powodu"):
    await interaction.response.defer(ephemeral=True)
    await użytkownik.kick(reason=powód)
    await interaction.followup.send(f"👢 Wyrzucono użytkownika {użytkownik.mention}. Powód: **{powód}**", ephemeral=True)


@bot.tree.command(name="mute", description="[Właściciel] Wycisza użytkownika na określony czas")
@is_owner()
async def cmd_mute(interaction: discord.Interaction, użytkownik: discord.Member, minuty: int, powód: str = "Brak"):
    await interaction.response.defer(ephemeral=True)
    await użytkownik.timeout(timedelta(minutes=minuty), reason=powód)
    await interaction.followup.send(f"🔇 Wyciszono użytkownika {użytkownik.mention} na {minuty} minut.", ephemeral=True)


@bot.tree.command(name="unmute", description="[Właściciel] Zdejmuje wyciszenie z użytkownika")
@is_owner()
async def cmd_unmute(interaction: discord.Interaction, użytkownik: discord.Member):
    await interaction.response.defer(ephemeral=True)
    await użytkownik.timeout(None)
    await interaction.followup.send(f"🔊 Odciszono użytkownika {użytkownik.mention}.", ephemeral=True)


@bot.tree.command(name="czysc", description="[Właściciel] Masowo usuwa wiadomości z kanału")
@is_owner()
async def cmd_czysc(interaction: discord.Interaction, ilosc: int):
    if ilosc < 1 or ilosc > 100:
        await interaction.response.send_message("❌ Możesz usunąć od 1 do 100 wiadomości naraz.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    usuniete = await interaction.channel.purge(limit=ilosc)
    await interaction.followup.send(f"✅ Pomyślnie usunięto **{len(usuniete)}** wiadomości.", ephemeral=True)


@bot.tree.command(name="warn", description="[Właściciel] Przyznaje ostrzeżenie użytkownikowi")
@is_owner()
async def cmd_warn(interaction: discord.Interaction, użytkownik: discord.Member, powód: str):
    await interaction.response.defer(ephemeral=True)
    user_warnings[użytkownik.id] = user_warnings.get(użytkownik.id, 0) + 1
    await interaction.followup.send(f"⚠️ Udzielono ostrzeżenia dla {użytkownik.mention}. Łącznie ostrzeżeń: **{user_warnings[użytkownik.id]}**. Powód: {powód}", ephemeral=True)


@bot.tree.command(name="ostrzeżenia", description="[Info] Sprawdza liczbę ostrzeżeń użytkownika")
async def cmd_ostrzeżenia(interaction: discord.Interaction, użytkownik: discord.Member = None):
    await interaction.response.defer(ephemeral=True)
    cel = użytkownik or interaction.user
    liczba = user_warnings.get(cel.id, 0)
    await interaction.followup.send(f"📌 Użytkownik {cel.mention} posiada **{liczba}** ostrzeżeń.", ephemeral=True)


@bot.tree.command(name="lock", description="[Właściciel] Blokuje bieżący kanał przed pisaniem")
@is_owner()
async def cmd_lock(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.followup.send("🔒 Ten kanał został pomyślnie zablokowany.", ephemeral=True)


@bot.tree.command(name="unlock", description="[Właściciel] Odblokowuje bieżący kanał")
@is_owner()
async def cmd_unlock(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.followup.send("🔓 Ten kanał został odblokowany.", ephemeral=True)


@bot.tree.command(name="powoli", description="[Właściciel] Ustawia tryb powolnego pisania (slowmode)")
@is_owner()
async def cmd_powoli(interaction: discord.Interaction, sekundy: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.edit(slowmode_delay=sekundy)
    await interaction.followup.send(f"⏱️ Ustawiono tryb powolnego pisania na **{sekundy} sekund**.", ephemeral=True)


@bot.tree.command(name="ping", description="[Info] Sprawdza opóźnienie (ping) bota")
async def cmd_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Opóźnienie wynosi: **{round(bot.latency * 1000)} ms**", ephemeral=True)


@bot.tree.command(name="serwer-info", description="[Info] Wyświetla informacje o obecnym serwerze")
async def cmd_serwerinfo(interaction: discord.Interaction):
    await interaction.response.defer()
    g = interaction.guild
    embed = discord.Embed(title=f"📊 Informacje o serwerze: {g.name}", color=discord.Color.green())
    embed.add_field(name="Właściciel", value=g.owner.mention if g.owner else "Brak danych", inline=True)
    embed.add_field(name="Liczba członków", value=g.member_count, inline=True)
    embed.add_field(name="Liczba kanałów", value=len(g.channels), inline=True)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="użytkownik-info", description="[Info] Wyświetla informacje o wybranym użytkowniku")
async def cmd_userinfo(interaction: discord.Interaction, użytkownik: discord.Member = None):
    await interaction.response.defer()
    u = użytkownik or interaction.user
    embed = discord.Embed(title=f"👤 Informacje o: {u.name}", color=discord.Color.blue())
    embed.add_field(name="ID Użytkownika", value=u.id, inline=True)
    embed.add_field(name="Konto utworzone", value=u.created_at.strftime("%d.%m.%Y"), inline=True)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="bot-info", description="[Info] Informacje o bocie")
async def cmd_botinfo(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 Jestem zaawansowanym botem Hakerolandii!", ephemeral=True)


@bot.tree.command(name="avatar", description="[Info] Pokazuje awatar wybranego użytkownika")
async def cmd_avatar(interaction: discord.Interaction, użytkownik: discord.Member = None):
    await interaction.response.defer()
    u = użytkownik or interaction.user
    embed = discord.Embed(title=f"🖼️ Awatar użytkownika {u.name}", color=discord.Color.purple())
    if u.display_avatar:
        embed.set_image(url=u.display_avatar.url)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="liczba-osób", description="[Info] Pokazuje szybki licznik członków na serwerze")
async def cmd_membercount(interaction: discord.Interaction):
    await interaction.response.send_message(f"👥 Aktualna liczba członków: **{interaction.guild.member_count}**", ephemeral=True)


@bot.tree.command(name="8ball", description="[4Fun] Magiczna kula odpowie na Twoje pytanie")
async def cmd_8ball(interaction: discord.Interaction, pytanie: str):
    odpowiedzi = ["Tak, zdecydowanie.", "Zdecydowanie tak.", "Nie mam pojęcia.", "Nie licz na to.", "Zdecydowanie nie."]
    embed = discord.Embed(title="🎱 Magiczna Kula", color=discord.Color.magenta())
    embed.add_field(name="Twoje pytanie:", value=pytanie, inline=False)
    embed.add_field(name="Odpowiedź:", value=random.choice(odpowiedzi), inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="rzut-moneta", description="[4Fun] Rzuca monetą")
async def cmd_coinflip(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 Wylosowano: **{random.choice(['Orzeł', 'Reszka'])}**!")


@bot.tree.command(name="losuj-liczbe", description="[4Fun] Losuje liczbę")
async def cmd_roll(interaction: discord.Interaction, maksimum: int = 100):
    await interaction.response.send_message(f"🎲 Wylosowana liczba (1-{maksimum}): **{random.randint(1, maksimum)}**")


@bot.tree.command(name="ocena", description="[4Fun] Ocenia podaną rzecz")
async def cmd_rate(interaction: discord.Interaction, tekst: str):
    await interaction.response.send_message(f"⭐ Ocena dla **{tekst}**: **{random.randint(0, 10)}/10**!")


@bot.tree.command(name="żart", description="[4Fun] Opowiada żart")
async def cmd_joke(interaction: discord.Interaction):
    zarty = ["– Dlaczego programiści nie lubią natury? – Bo ma za dużo bugów!"]
    await interaction.response.send_message(random.choice(zarty))


@bot.tree.command(name="przytul", description="[4Fun] Przytula użytkownika")
async def cmd_hug(interaction: discord.Interaction, użytkownik: discord.Member):
    await interaction.response.send_message(f"🤗 {interaction.user.mention} przytula {użytkownik.mention}!")


@bot.tree.command(name="ciastko", description="[4Fun] Częstuje ciastkiem")
async def cmd_cookie(interaction: discord.Interaction, użytkownik: discord.Member):
    await interaction.response.send_message(f"🍪 {interaction.user.mention} częstuje ciastkiem {użytkownik.mention}!")


@bot.tree.command(name="portfel", description="[Ekonomia] Sprawdza stan konta")
async def cmd_balance(interaction: discord.Interaction):
    bal = user_balances.get(interaction.user.id, 0)
    await interaction.response.send_message(f"💰 W Twoim portfelu znajduje się: **{bal} monet**.", ephemeral=True)


@bot.tree.command(name="praca", description="[Ekonomia] Zarób monety")
async def cmd_work(interaction: discord.Interaction):
    zarobek = random.randint(30, 150)
    user_balances[interaction.user.id] = user_balances.get(interaction.user.id, 0) + zarobek
    await interaction.response.send_message(f"💼 Zarobiłeś **{zarobek} monet**!")


@bot.tree.command(name="codzienna-nagroda", description="[Ekonomia] Codzienny bonus")
async def cmd_daily(interaction: discord.Interaction):
    bonus = 500
    user_balances[interaction.user.id] = user_balances.get(interaction.user.id, 0) + bonus
    await interaction.response.send_message(f"🎁 Odebrałeś bonus **{bonus} monet**!")


@bot.tree.command(name="przelej", description="[Ekonomia] Przelej monety")
async def cmd_pay(interaction: discord.Interaction, użytkownik: discord.Member, kwota: int):
    if kwota <= 0:
        await interaction.response.send_message("❌ Kwota musi być większa od zera.", ephemeral=True)
        return
    uid = interaction.user.id
    if user_balances.get(uid, 0) < kwota:
        await interaction.response.send_message("❌ Nie posiadasz tyle monet!", ephemeral=True)
        return
    user_balances[uid] -= kwota
    user_balances[użytkownik.id] = user_balances.get(użytkownik.id, 0) + kwota
    await interaction.response.send_message(f"✅ Przelewano **{kwota} monet** dla {użytkownik.mention}.")


if __name__ == "__main__":
    if not TOKEN:
        print("❌ BŁĄD: Brak zmiennej środowiskowej DISCORD_TOKEN!")
    else:
        bot.run(TOKEN)
