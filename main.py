import os
import logging
import asyncio
import discord
from discord.ext import commands
from discord import ui
import datetime

# ==============================================================================
# KONFIGURACJA LOGOWANIA
# ==============================================================================
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(name)s -> %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("HakerolandiaShop")

# ==============================================================================
# 1. WERYFIKACJA (CAPTCHA)
# ==============================================================================
class CaptchaView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="ZWERYFIKUJ SIĘ (CAPTCHA)", style=discord.ButtonStyle.green, custom_id="btn_captcha_hakerolandia")
    async def verify(self, interaction: discord.Interaction, button: ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Zweryfikowany")
        if not role:
            await interaction.response.send_message("❌ Błąd: Brak roli 'Zweryfikowany' na serwerze.", ephemeral=True)
            return
        
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Pomyślnie zweryfikowano konto!", ephemeral=True)
        except Exception as e:
            logger.error(f"Błąd nadawania roli: {e}")
            await interaction.response.send_message("❌ Brak uprawnień do nadania roli.", ephemeral=True)


# ==============================================================================
# 2. FORMULARZ ZAMÓWIENIA (MODAL)
# ==============================================================================
class ZamowienieModal(ui.Modal, title="HAKEROLANDIA — FORMULARZ ZAMÓWIENIA"):
    def __init__(self, pakiet: str, cena_jednostkowa: float, ilosc: int):
        super().__init__()
        self.pakiet = pakiet
        self.cena_jednostkowa = cena_jednostkowa
        self.ilosc = ilosc

    nick_roblox = ui.TextInput(
        label="JAKI JEST TWÓJ NICK W ROBLOX / DC:",
        placeholder="np. @HakerPro",
        required=True,
        max_length=100
    )
    
    platnosc = ui.TextInput(
        label="JAKĄ METODĄ PŁATNOŚCI CHCESZ ZAPŁACIć:",
        placeholder="BLIK / Revolut",
        required=True,
        max_length=50
    )
    
    kod_rabatowy = ui.TextInput(
        label="CZY POSIADASZ KOD ZNIŻKOWY:",
        placeholder="Jeżeli nie posiadasz, zostaw pole puste",
        required=False,
        max_length=50
    )
    
    kod_polecajacy = ui.TextInput(
        label="CZY POSIADASZ KOD POLECAJĄCY:",
        placeholder="Jeżeli nie posiadasz, zostaw pole puste",
        required=False,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        cena_calkowita = self.cena_jednostkowa * self.ilosc
        rabat = self.kod_rabatowy.value if self.kod_rabatowy.value else "Nie podano"
        polecajacy = self.kod_polecajacy.value if self.kod_polecajacy.value else "Nie podano"

        view = PodsumowanieZakupuView(
            pakiet=self.pakiet,
            ilosc=self.ilosc,
            cena=cena_calkowita,
            nick=self.nick_roblox.value,
            platnosc=self.platnosc.value,
            rabat=rabat,
            polecajacy=polecajacy
        )

        tekst = (
            f"🛒 **HAKEROLANDIA — PODSUMOWANIE ZAMÓWIENIA**\n"
            f"📦 **Pakiet:** {self.ilosc}x {self.pakiet}\n"
            f"💰 **Cena końcowa:** **{cena_calkowita:.2f} PLN**\n"
            f"👤 **Nick:** {self.nick_roblox.value}\n"
            f"💳 **Płatność:** {self.platnosc.value}\n"
            f"🏷️ **Kod zniżkowy:** {rabat}\n\n"
            f"Wszystko się zgadza? — Użyj przycisku poniżej i dokonaj płatności."
        )
        await interaction.response.send_message(tekst, view=view, ephemeral=True)


# ==============================================================================
# 3. WIDOK PODSUMOWANIA I PŁATNOŚCI + TICKET
# ==============================================================================
class PodsumowanieZakupuView(ui.View):
    def __init__(self, pakiet, ilosc, cena, nick, platnosc, rabat, polecajacy):
        super().__init__(timeout=300)
        self.pakiet = pakiet
        self.ilosc = ilosc
        self.cena = cena
        self.nick = nick
        self.platnosc = platnosc
        self.rabat = rabat
        self.polecajacy = polecajacy

        self.add_item(ui.Button(
            label="Zapłać przez Tipply", 
            style=discord.ButtonStyle.link, 
            url="https://tipply.pl/@hakerroblox", 
            emoji="💲"
        ))

    @ui.button(label="✅ Opłaciłem / Utwórz ticket", style=discord.ButtonStyle.green, custom_id="btn_finalizuj_ticket", row=1)
    async def finalizuj_zamowienie(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        channel_name = f"zamówienie-{user.name}"
        try:
            ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
        except Exception as e:
            logger.error(f"Nie udało się utworzyć ticketa: {e}")
            await interaction.response.send_message("❌ Brak uprawnień do utworzenia kanału ticketa.", ephemeral=True)
            return

        embed = discord.Embed(title="HAKEROLANDIA — NOWE ZAMÓWIENIE SERWERA", color=discord.Color.green())
        embed.add_field(name="Zamówiony Pakiet", value=f"{self.ilosc}x {self.pakiet} ({self.cena:.2f} PLN)", inline=False)
        embed.add_field(name="Nick klienta", value=self.nick, inline=False)
        embed.add_field(name="Metoda Płatności", value=self.platnosc, inline=False)
        embed.add_field(name="Kod zniżkowy", value=self.rabat, inline=False)
        embed.add_field(name="Kod polecający", value=self.polecajacy, inline=False)

        await ticket_channel.send(
            content=f"🔔 **Witaj {user.mention}!**\n"
                    f"Twoje zamówienie zostało zarejestrowane. Prosimy o wysłanie tutaj dowodu wpłaty (screena).\n"
                    f"Realizacja następuje do 48h! *(Gdy skończycie, użyj `/zakoncz`)*",
            embed=embed
        )

        await interaction.response.edit_message(
            content=f"✅ Przekierowano pomyślnie! Utworzono dla Ciebie prywatny ticket: {ticket_channel.mention}",
            view=None
        )


# ==============================================================================
# 4. WYBÓR ILOŚCI SZTUK
# ==============================================================================
class WyborIlosciSelect(ui.View):
    def __init__(self, pakiet, cena):
        super().__init__(timeout=None)
        self.pakiet = pakiet
        self.cena = cena

    @ui.select(
        placeholder="Wybierz ilość sztuk...",
        custom_id="select_ilosc_sztuk",
        options=[
            discord.SelectOption(label="1 szt.", value="1"),
            discord.SelectOption(label="2 szt.", value="2"),
            discord.SelectOption(label="3 szt.", value="3"),
        ]
    )
    async def select_ilosc(self, interaction: discord.Interaction, select: ui.Select):
        ilosc = int(select.values[0])
        await interaction.response.send_modal(
            ZamowienieModal(pakiet=self.pakiet, cena_jednostkowa=self.cena, ilosc=ilosc)
        )


# ==============================================================================
# 5. GŁÓWNE MENU WYBORU PAKIETÓW (SELECT MENU)
# ==============================================================================
class GlowneMenuPakietow(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="Wybierz pakiet serwera do zakupu...",
        custom_id="select_pakiet_serwera",
        options=[
            discord.SelectOption(label="START (19,99 zł)", description="Max 10 kategorii / 30 kanałów, Lobby, Zabezpieczenia", value="START|19.99"),
            discord.SelectOption(label="BASIC (39,99 zł)", description="Max 20 kategorii / 50 kanałów, Ekonomia + sklep", value="BASIC|39.99"),
            discord.SelectOption(label="PREMIUM (69,99 zł)", description="Nielimitowane kategorie/kanały, Pomoc w rozwoju", value="PREMIUM|69.99"),
        ]
    )
    async def select_pakiet(self, interaction: discord.Interaction, select: ui.Select):
        dane = select.values[0].split("|")
        pakiet = dane[0]
        cena = float(dane[1])

        await interaction.response.send_message(
            f"📦 Wybrałeś pakiet: **{pakiet}** ({cena} PLN). Teraz wybierz ilość sztuk:",
            view=WyborIlosciSelect(pakiet=pakiet, cena=cena),
            ephemeral=True
        )


# ==============================================================================
# 6. GŁÓWNA KLASA BOTA
# ==============================================================================
class HakerolandiaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        logger.info("Ładowanie stałych widoków...")
        self.add_view(GlowneMenuPakietow())
        self.add_view(CaptchaView())
        
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            try:
                MY_GUILD = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=MY_GUILD)
                await self.tree.sync(guild=MY_GUILD)
                logger.info(f"Zsynchronizowano komendy dla serwera: {guild_id}")
            except Exception as e:
                logger.error(f"Błąd synchronizacji: {e}")

    async def on_ready(self):
        logger.info(f"Zalogowano pomyślnie jako {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="HAKEROLANDIA | Sklep Serwerów"))


bot = HakerolandiaBot()


# ==============================================================================
# 7. KOMENDY SLASH
# ==============================================================================
@bot.tree.command(name="wyslij-panel", description="Wysyła panel zakupu serwerów z menu rozwijanym")
async def wyslij_panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Brak uprawnień administratora!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="🖥️ ZAMÓW SWÓJ SERWER",
        description="HAKEROLANDIA\n\n"
                    "⚠️ **UWAGA!**\n"
                    "Zamówienia realizujemy PO KOLEI — zgodnie z kolejnością wpłat. ❤️\n\n"
                    "👇 **Wybierz interesujący Cię pakiet z menu poniżej, aby złożyć zamówienie!**",
        color=discord.Color.dark_green()
    )
    
    await interaction.channel.send(embed=embed, view=GlowneMenuPakietow())
    await interaction.response.send_message("✅ Pomyślnie wysłano panel sklepu!", ephemeral=True)


@bot.tree.command(name="cennik", description="Wyświetla oficjalny cennik serwerów Hakerolandia")
async def cennik(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📃 CENNIK HAKEROLANDIA",
        description="⚠️ **UWAGA!**\n"
                    "Zamówienia realizujemy PO KOLEI — zgodnie z kolejnością wpłat. ❤️\n\n"
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
                    "BLIK • Revolut\n\n"
                    "⏱️ Realizacja do 48h\n"
                    "⭐ Po odbiorze możesz zostawić opinię!\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "🔥 **HAKEROLANDIA**\n"
                    "Twój pomysł. Nasza realizacja.\n"
                    "━━━━━━━━━━━━━━━━━━",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="wyslij-weryfikacje", description="Wysyła panel weryfikacji CAPTCHA")
async def wyslij_weryfikacje(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="🛡️ HAKEROLANDIA — WERYFIKACJA",
        description="Kliknij przycisk poniżej, aby zweryfikować konto.",
        color=discord.Color.gold()
    )
    await interaction.channel.send(embed=embed, view=CaptchaView())
    await interaction.response.send_message("✅ Wysłano weryfikację!", ephemeral=True)


@bot.tree.command(name="zakoncz", description="Zamyka i usuwa bieżący ticket zamówienia (Tylko Admin)")
async def zakoncz(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Nie masz uprawnień administratora do zamykania ticketów!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="HAKEROLANDIA — ZAMÓWIENIE ZREALIZOWANE",
        description="Dziękujemy za zakupy! Zapraszamy do wystawienia opinii.\nTen kanał zostanie automatycznie usunięty za 5 sekund.",
        color=discord.Color.green()
    )
    
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Rozpoczęto zamykanie ticketa...", ephemeral=True)
    
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete()
    except Exception as e:
        logger.error(f"Nie udało się usunąć kanału ticketa: {e}")


# ==============================================================================
# 8. START APLIKACJI
# ==============================================================================
def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.critical("KRYTYCZNY BŁĄD: Brak zmiennej DISCORD_TOKEN w konfiguracji!")
        return
    bot.run(token)

if __name__ == "__main__":
    main()
