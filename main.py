import os
import logging
import asyncio
import discord
from discord.ext import commands
from discord import ui

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# ==================== 1. WERYFIKACJA (CAPTCHA) ====================
class CaptchaView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Zweryfikuj się (CAPTCHA)", style=discord.ButtonStyle.green, custom_id="btn_captcha_hakerolandia")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Zweryfikowany")
        
        if role:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("✅ Pomyślnie zweryfikowano! Witaj na serwerze HAKEROLANDIA.", ephemeral=True)
            except Exception:
                await interaction.response.send_message("❌ Bot nie posiada uprawnień do nadania roli weryfikacji!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Rola 'Zweryfikowany' nie została utworzona na tym serwerze.", ephemeral=True)


# ==================== 2. FORMULARZ ZAMÓWIENIA ====================
class ZamowienieModal(ui.Modal, title="HAKEROLANDIA — Formularz Zamówienia"):
    def __init__(self, pakiet: str, cena: str):
        super().__init__()
        self.pakiet = pakiet
        self.cena = cena

    nick_dc = ui.TextInput(
        label="JAKI JEST TWÓJ NICK W ROBLOX / DC:",
        placeholder="haker.roblox",
        required=True,
        max_length=100
    )
    
    platnosc = ui.TextInput(
        label="JAKĄ METODĄ PŁATNOŚCI CHCESZ ZAPŁACIć:",
        placeholder="BLIK",
        required=True,
        max_length=100
    )
    
    kod_rabatowy = ui.TextInput(
        label="CZY POSIADASZ KOD ZNIŻKOWY:",
        placeholder="HakerRoblox15",
        required=False,
        max_length=50
    )
    
    kod_polecajacy = ui.TextInput(
        label="CZY POSIADASZ KOD POLECAJĄCY:",
        placeholder="HakerRoblox15",
        required=False,
        max_length=50
    )
    
    uwagi = ui.TextInput(
        label="UWAGI DO ZAMÓWIENIA:",
        placeholder="Wpisz dodatkowe uwagi (opcjonalnie)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        view = OplacZamowienieView(
            pakiet=self.pakiet,
            cena=self.cena,
            nick=self.nick_dc.value,
            platnosc=self.platnosc.value,
            rabat=self.kod_rabatowy.value or 'Nie podano',
            polecajacy=self.kod_polecajacy.value or 'Nie podano',
            uwagi=self.uwagi.value or 'Brak'
        )
        
        tekst = (
            f"🛒 **HAKEROLANDIA — PODSUMOWANIE**\n"
            f"📦 **Pakiet:** {self.pakiet} (**{self.cena}**)\n"
            f"👤 **Nick:** {self.nick_dc.value}\n"
            f"💳 **Płatność:** {self.platnosc.value}\n\n"
            f"Kliknij poniższy przycisk **„Opłać zamówienie”**, aby utworzyć ticket i przejść do realizacji!"
        )
        await interaction.response.send_message(tekst, view=view, ephemeral=True)


# ==================== 3. PRZYCISK "OPŁAĆ ZAMÓWIENIE" ====================
class OplacZamowienieView(ui.View):
    def __init__(self, pakiet, cena, nick, platnosc, rabat, polecajacy, uwagi):
        super().__init__(timeout=300)
        self.pakiet = pakiet
        self.cena = cena
        self.nick = nick
        self.platnosc = platnosc
        self.rabat = rabat
        self.polecajacy = polecajacy
        self.uwagi = uwagi

    @ui.button(label="💳 Opłać zamówienie", style=discord.ButtonStyle.green, emoji="⚡")
    async def oplac_button(self, interaction: discord.Interaction, button: ui.Button):
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
        except Exception:
            await interaction.response.send_message("❌ Nie udało się utworzyć ticketa z powodu braku uprawnień bota.", ephemeral=True)
            return

        embed = discord.Embed(title="HAKEROLANDIA — NOWE ZAMÓWIENIE", color=discord.Color.green())
        embed.add_field(name="Pakiet", value=f"{self.pakiet} - {self.cena}", inline=False)
        embed.add_field(name="Nick (Roblox/DC)", value=self.nick, inline=False)
        embed.add_field(name="Płatność", value=self.platnosc, inline=False)
        embed.add_field(name="Kod zniżkowy", value=self.rabat, inline=False)
        embed.add_field(name="Kod polecający", value=self.polecajacy, inline=False)
        embed.add_field(name="Uwagi", value=self.uwagi, inline=False)

        await ticket_channel.send(
            content=f"🔔 **NOWE ZAMÓWIENIE!** Witaj {user.mention}!\n"
                    f"Wyślij tutaj dowód wpłaty (screen/potwierdzenie), a administracja wkrótce zrealizuje zamówienie.\n"
                    f"*(Gdy administracja skończy, użyje komendy `/zakoncz`)*",
            embed=embed
        )

        await interaction.response.edit_message(
            content=f"✅ Płatność zainicjowana! Utworzono dla Ciebie prywatny ticket: {ticket_channel.mention}",
            view=None
        )


# ==================== 4. SKLEP (3 PAKIETY) ====================
class SklepView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="PAKIET START (19,99 zł)", style=discord.ButtonStyle.primary, custom_id="btn_start")
    async def pakiet_start(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ZamowienieModal(pakiet="PAKIET START", cena="19,99 zł"))

    @ui.button(label="PAKIET BASIC (39,99 zł)", style=discord.ButtonStyle.success, custom_id="btn_basic")
    async def pakiet_basic(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ZamowienieModal(pakiet="PAKIET BASIC", cena="39,99 zł"))

    @ui.button(label="PAKIET PREMIUM (69,99 zł)", style=discord.ButtonStyle.danger, custom_id="btn_premium")
    async def pakiet_premium(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ZamowienieModal(pakiet="PAKIET PREMIUM", cena="69,99 zł"))


# ==================== 5. GŁÓWNA KLASA BOTA ====================
class HakerolandiaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        self.add_view(SklepView())
        self.add_view(CaptchaView())
        
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            try:
                MY_GUILD = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=MY_GUILD)
                await self.tree.sync(guild=MY_GUILD)
                logging.info(f"Zsynchronizowano pomyślnie komendy dla serwera: {guild_id}")
            except Exception as e:
                logging.error(f"Błąd podczas synchronizacji komend: {e}")
        else:
            logging.warning("BŁĄD: Zmienna środowiskowa GUILD_ID nie została zdefiniowana w Railway!")

    async def on_ready(self):
        logging.info(f"Bot zalogowany pomyślnie jako: {self.user} (ID: {self.user.id})")
        activity = discord.Activity(type=discord.ActivityType.watching, name="HAKEROLANDIA | Pakiety i Sklep")
        await self.change_presence(status=discord.Status.online, activity=activity)

bot = HakerolandiaBot()

# ==================== 6. KOMENDY SLASH ====================

@bot.tree.command(name="wyslij-sklep", description="Wysyła panel sklepu z pakietami na kanał")
async def wyslij_sklep(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="🛒 HAKEROLANDIA — OFERTA SKLEPU",
        description="Wybierz interesujący Cię pakiet, klikając odpowiedni przycisk poniżej:",
        color=discord.Color.dark_green()
    )
    embed.add_field(name="📦 PAKIET START", value="Cena: **19,99 zł**\n• Podstawowy zestaw dla każdego gracza", inline=False)
    embed.add_field(name="📦 PAKIET BASIC", value="Cena: **39,99 zł**\n• Rozszerzony pakiet o wyższej wartości", inline=False)
    embed.add_field(name="📦 PAKIET PREMIUM", value="Cena: **69,99 zł**\n• Pełny zestaw maksymalny + priorytet", inline=False)
    
    await interaction.channel.send(embed=embed, view=SklepView())
    await interaction.response.send_message("✅ Pomyślnie wysłano panel sklepu!", ephemeral=True)

@bot.tree.command(name="cennik", description="Wyświetla pełny cennik serwera Hakerolandia")
async def cennik(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 HAKEROLANDIA — OFICJALNY CENNIK",
        description="Sprawdź cennik naszych paczek i produktów:",
        color=discord.Color.blue()
    )
    embed.add_field(name="1️⃣ Pakiet Start", value="• Cena: **19,99 zł**\n• Szybka realizacja", inline=False)
    embed.add_field(name="2️⃣ Pakiet Basic", value="• Cena: **39,99 zł**\n• Najczęściej wybierany", inline=False)
    embed.add_field(name="3️⃣ Pakiet Premium", value="• Cena: **69,99 zł**\n• Najwyższa jakość i bonusy", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="wyslij-weryfikacje", description="Wysyła panel weryfikacyjny CAPTCHA na kanał")
async def wyslij_weryfikacje(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Nie masz uprawnień!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="🛡️ HAKEROLANDIA — WERYFIKACJA",
        description="Kliknij przycisk poniżej, aby zweryfikować swoje konto i odblokować pełny dostęp do kanałów serwera.",
        color=discord.Color.gold()
    )
    await interaction.channel.send(embed=embed, view=CaptchaView())
    await interaction.response.send_message("✅ Wysłano panel weryfikacji!", ephemeral=True)

@bot.tree.command(name="zakoncz", description="Zamyka zamówienie, wysyła podsumowanie i usuwa ticket (Tylko Admin)")
async def zakoncz(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Nie masz uprawnień administratora!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="HAKEROLANDIA — ZAMÓWIENIE ZREALIZOWANE",
        description="Dziękujemy za skorzystanie z naszych usług.\nGorąco zachęcamy do wystawienia **pozytywnej opinii**.",
        color=discord.Color.green()
    )
    
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Zamówienie zakończone. Kanał zostanie usunięty za 5 sekund...", ephemeral=True)
    
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete()
    except Exception:
        pass


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.critical("KRYTYCZNY BŁĄD: Brak zmiennej DISCORD_TOKEN w konfiguracji środowiska!")
        return
    bot.run(token)

if __name__ == "__main__":
    main()
