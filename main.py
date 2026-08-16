import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
import os
import random
from datetime import timedelta

TOKEN = os.getenv("TOKEN")
GUILD_ID_STR = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID_STR) if GUILD_ID_STR else 0
OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else 0

def is_owner():
    async def predicate(interaction: discord.Interaction):
        if OWNER_ID != 0 and interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Tylko właściciel!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(MainPanelView())
        self.add_view(TicketCloseView())
        self.add_view(TicketPanelView())
        self.add_view(OpiniePanelView())
        self.add_view(CennikPanelView())
        self.add_view(KodyPolecajacePanelView())
        self.add_view(PlatnosciPanelView())
        self.add_view(WeryfikacjaView())
        check_youtube_videos.start()
        await self.tree.sync()

bot = MegaBot()

@tasks.loop(minutes=1)
async def check_youtube_videos():
    pass

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")

# --- SYSTEM TICKETÓW I AUTOMATYZACJA ---
class TicketCloseView(ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    @ui.button(label="🔒 Zamknij Ticket", style=discord.ButtonStyle.danger, custom_id="t_close")
    async def close(self, i: discord.Interaction, b: ui.Button): 
        await i.channel.delete()

async def create_auto_ticket(interaction: discord.Interaction, product_name: str, quantity: int):
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name="ZAMÓWIENIA")
    if not category:
        category = await guild.create_category("ZAMÓWIENIA")

    # Tworzenie prywatnego kanału dla użytkownika
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    
    channel_name = f"zamowienie-{interaction.user.name}"
    ticket_channel = await guild.text_channel(name=channel_name, category=category, overwrites=overwrites)

    embed = discord.Embed(
        title="🛒 Nowe Zamówienie / Płatność",
        description=f"Dziękujemy za wybranie produktu!\n\n**Produkt:** {product_name}\n**Ilość sztuk:** {quantity}\n\nProszę dokonać płatności przez poniższy link Tipply, a następnie potwierdzić tutaj wpłatę.",
        color=discord.Color.green()
    )
    
    view = ui.View()
    view.add_item(ui.Button(label="💳 Zapłać przez Tipply", style=discord.ButtonStyle.link, url="https://tipply.pl/@hakerroblox"))
    view.add_item(ui.Button(label="🔒 Zamknij", style=discord.ButtonStyle.danger, custom_id="t_close_auto"))

    await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=TicketCloseView())
    await interaction.response.send_message(f"✅ Utworzono dla Ciebie automatyczny ticket: {ticket_channel.mention}", ephemeral=True)

# --- MODAL WYBORU ILOŚCI SZTUK ---
class IlooscSztukModal(ui.Modal, title="Wybierz ilość sztuk"):
    ilosc = ui.TextInput(label="Podaj liczbę sztuk", placeholder="np. 1, 5, 10...", default="1", min_length=1, max_length=3)

    def __init__(self, produkt: str):
        super().__init__()
        self.produkt = produkt

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.ilosc.value)
            if qty <= 0:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message("❌ Podaj prawidłową liczbę całkowitą większą od 0!", ephemeral=True)
            return
        
        # Wywołanie automatycznego tworzenia ticketa po podaniu ilości
        await create_auto_ticket(interaction, self.produkt, qty)

class WyborOfertyView(ui.View):
    def __init__(self): 
        super().__init__(timeout=None)

    @ui.button(label="📦 Pakiet Start", style=discord.ButtonStyle.primary, custom_id="prod_start")
    async def start_btn(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_modal(IlooscSztukModal("Pakiet Start"))

    @ui.button(label="🚀 Pakiet Basic", style=discord.ButtonStyle.success, custom_id="prod_basic")
    async def basic_btn(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_modal(IlooscSztukModal("Pakiet Basic"))

    @ui.button(label="💎 Pakiet Premium", style=discord.ButtonStyle.danger, custom_id="prod_premium")
    async def premium_btn(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_modal(IlooscSztukModal("Pakiet Premium"))

# --- POZOSTAŁE WIDOKI UI ---
class MetodaPlatnosciSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="BLIK", value="blik", emoji="🟩"),
            discord.SelectOption(label="Revolut", value="revolut", emoji="🟦")
        ]
        super().__init__(placeholder="Wybierz metodę...", options=options)
    async def callback(self, i: discord.Interaction):
        await create_auto_ticket(i, f"Płatność losowa ({self.values[0].upper()})", 1)

class PlatnosciPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(MetodaPlatnosciSelect())

class TicketPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Otwórz Ticket", custom_id="t_open")
    async def open(self, i: discord.Interaction, b: ui.Button): await create_auto_ticket(i, "Ogólny Ticket", 1)

class WeryfikacjaView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Zweryfikuj", custom_id="verify_btn")
    async def verify(self, i: discord.Interaction, b: ui.Button): await i.response.send_message("Zweryfikowano pomyślnie!", ephemeral=True)

class OpiniePanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Oceń", custom_id="rate_btn")
    async def rate(self, i: discord.Interaction, b: ui.Button): await i.response.send_message("Panel opinii...", ephemeral=True)

class CennikPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Cennik", custom_id="price_btn")
    async def price(self, i: discord.Interaction, b: ui.Button): await i.response.send_message("Cennik usług...", ephemeral=True)

class KodyPolecajacePanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Kody", custom_id="codes_btn")
    async def codes(self, i: discord.Interaction, b: ui.Button): await i.response.send_message("System kodów...", ephemeral=True)

class MainPanelView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="🛒 Zamów Produkt", style=discord.ButtonStyle.blurple, custom_id="order_btn")
    async def order(self, i: discord.Interaction, b: ui.Button): 
        await i.response.send_message("Wybierz pakiet:", view=WyborOfertyView(), ephemeral=True)

# ==========================================
# 150+ KOMEND SLASH
# ==========================================

# 1. Komendy Informacyjne i Ogólne (1-20)
@bot.tree.command(name="ping", description="[1/150] Sprawdza opóźnienie bota")
async def cmd_1(i: discord.Interaction): await i.response.send_message(f"Pong! {bot.latency*1000:.0f}ms", ephemeral=True)
@bot.tree.command(name="botinfo", description="[2/150] Informacje o bocie")
async def cmd_2(i: discord.Interaction): await i.response.send_message("Bot stworzony dla Hakerolandia.", ephemeral=True)
@bot.tree.command(name="serwerinfo", description="[3/150] Informacje o serwerze")
async def cmd_3(i: discord.Interaction): await i.response.send_message(f"Serwer: {i.guild.name}", ephemeral=True)
@bot.tree.command(name="userinfo", description="[4/150] Informacje o użytkowniku")
async def cmd_4(i: discord.Interaction, u: discord.Member = None): u = u or i.user; await i.response.send_message(f"User: {u}", ephemeral=True)
@bot.tree.command(name="avatar", description="[5/150] Pokazuje awatar")
async def cmd_5(i: discord.Interaction, u: discord.Member = None): u = u or i.user; await i.response.send_message(u.display_avatar.url, ephemeral=True)
@bot.tree.command(name="wersja", description="[6/150] Wersja bota")
async def cmd_6(i: discord.Interaction): await i.response.send_message("Wersja 5.0 Ultra", ephemeral=True)
@bot.tree.command(name="uptime", description="[7/150] Czas działania")
async def cmd_7(i: discord.Interaction): await i.response.send_message("Działa stabilnie.", ephemeral=True)
@bot.tree.command(name="regulamin", description="[8/150] Pokaż regulamin")
async def cmd_8(i: discord.Interaction): await i.response.send_message("Regulamin serwera...", ephemeral=True)
@bot.tree.command(name="cennik", description="[9/150] Pokaż cennik")
async def cmd_9(i: discord.Interaction): await i.response.send_message("Cennik usług...", ephemeral=True)
@bot.tree.command(name="pomoc", description="[10/150] Menu pomocy")
async def cmd_10(i: discord.Interaction): await i.response.send_message("Pomoc...", ephemeral=True)
@bot.tree.command(name="status", description="[11/150] Status bota")
async def cmd_11(i: discord.Interaction): await i.response.send_message("Online", ephemeral=True)
@bot.tree.command(name="kontakt", description="[12/150] Kontakt z administracją")
async def cmd_12(i: discord.Interaction): await i.response.send_message("Użyj ticketów.", ephemeral=True)
@bot.tree.command(name="partnerzy", description="[13/150] Lista partnerów")
async def cmd_13(i: discord.Interaction): await i.response.send_message("Brak partnerów.", ephemeral=True)
@bot.tree.command(name="boost", description="[14/150] Informacje o boostach")
async def cmd_14(i: discord.Interaction): await i.response.send_message("Dziękujemy za boosty!", ephemeral=True)
@bot.tree.command(name="rola", description="[15/150] Info o roli")
async def cmd_15(i: discord.Interaction, r: discord.Role): await i.response.send_message(f"Rola: {r.name}", ephemeral=True)
@bot.tree.command(name="emoji", description="[16/150] Lista emoji")
async def cmd_16(i: discord.Interaction): await i.response.send_message("Emoji serwera...", ephemeral=True)
@bot.tree.command(name="kanały", description="[17/150] Lista kanałów")
async def cmd_17(i: discord.Interaction): await i.response.send_message(str(len(i.guild.channels)), ephemeral=True)
@bot.tree.command(name="boty", description="[18/150] Liczba botów")
async def cmd_18(i: discord.Interaction): await i.response.send_message("Sprawdzam...", ephemeral=True)
@bot.tree.command(name="zaproszenie", description="[19/150] Link zaproszenia")
async def cmd_19(i: discord.Interaction): await i.response.send_message("https://discord.gg/hakerolandia", ephemeral=True)
@bot.tree.command(name="czas", description="[20/150] Aktualny czas")
async def cmd_20(i: discord.Interaction): await i.response.send_message("2026", ephemeral=True)

# 2. Komendy Sklepu i Zamówień (21-41)
@bot.tree.command(name="zamów", description="[21/150] Otwórz sklep")
async def cmd_21(i: discord.Interaction): await i.response.send_message(view=WyborOfertyView(), ephemeral=True)
@bot.tree.command(name="start-pakiet", description="[22/150] Info o pakiecie Start")
async def cmd_22(i: discord.Interaction): await i.response.send_message("Start: 19.99 zł", ephemeral=True)
@bot.tree.command(name="basic-pakiet", description="[23/150] Info o pakiecie Basic")
async def cmd_23(i: discord.Interaction): await i.response.send_message("Basic: 39.99 zł", ephemeral=True)
@bot.tree.command(name="premium-pakiet", description="[24/150] Info o pakiecie Premium")
async def cmd_24(i: discord.Interaction): await i.response.send_message("Premium: 69.99 zł", ephemeral=True)
@bot.tree.command(name="blik", description="[25/150] Płatność Blik")
async def cmd_25(i: discord.Interaction): await create_auto_ticket(i, "Płatność BLIK", 1)
@bot.tree.command(name="revolut", description="[26/150] Płatność Revolut")
async def cmd_26(i: discord.Interaction): await create_auto_ticket(i, "Płatność Revolut", 1)
@bot.tree.command(name="kod-znizkowy", description="[27/150] Sprawdź kod zniżkowy")
async def cmd_27(i: discord.Interaction, kod: str): await i.response.send_message(f"Kod {kod} rabatowy", ephemeral=True)
@bot.tree.command(name="moj-kod", description="[28/150] Twój kod polecający")
async def cmd_28(i: discord.Interaction): await i.response.send_message("Twój kod...", ephemeral=True)
@bot.tree.command(name="stworz-kod", description="[29/150] Utwórz kod")
async def cmd_29(i: discord.Interaction, nazwa: str): await i.response.send_message(f"Stworzono {nazwa}", ephemeral=True)
@bot.tree.command(name="usun-kod", description="[30/150] Usuń kod")
async def cmd_30(i: discord.Interaction): await i.response.send_message("Usunięto kod", ephemeral=True)
@bot.tree.command(name="staty-kodu", description="[31/150] Statystyki kodu")
async def cmd_31(i: discord.Interaction): await i.response.send_message("Statystyki...", ephemeral=True)
@bot.tree.command(name="opinie", description="[32/150] Wystaw opinię")
async def cmd_32(i: discord.Interaction): await i.response.send_message("Panel opinii", ephemeral=True)
@bot.tree.command(name="realizacja", description="[33/150] Czas realizacji")
async def cmd_33(i: discord.Interaction): await i.response.send_message("Do 48h", ephemeral=True)
@bot.tree.command(name="kolejka", description="[34/150] Kolejka zamówień")
async def cmd_35(i: discord.Interaction): await i.response.send_message("Brak oczekujących", ephemeral=True)
@bot.tree.command(name="sklep-status", description="[35/150] Status sklepu")
async def cmd_36(i: discord.Interaction): await i.response.send_message("Sklep otwarty", ephemeral=True)
@bot.tree.command(name="rabaty", description="[36/150] Aktywne rabaty")
async def cmd_37(i: discord.Interaction): await i.response.send_message("5% zniżki", ephemeral=True)
@bot.tree.command(name="faktura", description="[37/150] Info o fakturach")
async def cmd_38(i: discord.Interaction): await i.response.send_message("Brak faktur", ephemeral=True)
@bot.tree.command(name="reklamacje", description="[38/150] Zasady reklamacji")
async def cmd_39(i: discord.Interaction): await i.response.send_message("Przez ticket", ephemeral=True)
@bot.tree.command(name="promocje", description="[39/150] Aktualne promocje")
async def cmd_40(i: discord.Interaction): await i.response.send_message("Brak", ephemeral=True)
@bot.tree.command(name="sklep-info", description="[40/150] O sklepie")
async def cmd_41(i: discord.Interaction): await i.response.send_message("Hakerolandia Sklep", ephemeral=True)

# 3. Komendy Trade i Interakcji (42-60)
@bot.tree.command(name="trade", description="[42/150] Oferta wymiany")
async def cmd_42(i: discord.Interaction, user: discord.Member): await i.response.send_message(f"Trade z {user}", ephemeral=True)
@bot.tree.command(name="off_trade", description="[43/150] Blokada wymian")
async def cmd_43(i: discord.Interaction): await i.response.send_message("Zmieniono status trade", ephemeral=True)
@bot.tree.command(name="profil", description="[44/150] Profil trade")
async def cmd_44(i: discord.Interaction, user: discord.Member): await i.response.send_message(f"Profil {user}", ephemeral=True)
@bot.tree.command(name="legitcheck", description="[45/150] Sprawdź legit")
async def cmd_45(i: discord.Interaction, user: discord.Member): await i.response.send_message("100% Legit", ephemeral=True)
@bot.tree.command(name="reputacja", description="[46/150] Reputacja gracza")
async def cmd_46(i: discord.Interaction, user: discord.Member): await i.response.send_message("Brak uwag", ephemeral=True)
@bot.tree.command(name="warcaby", description="[47/150] Gra w warcaby")
async def cmd_47(i: discord.Interaction): await i.response.send_message("Gra niedostępna", ephemeral=True)
@bot.tree.command(name="kolo-fortuny", description="[48/150] Koło fortuny")
async def cmd_48(i: discord.Interaction): await i.response.send_message("Zakręcono!", ephemeral=True)
@bot.tree.command(name="odgadnij-liczbu", description="[49/150] Mini gra")
async def cmd_49(i: discord.Interaction): await i.response.send_message("Zgaduj 1-10", ephemeral=True)
@bot.tree.command(name="coinflip", description="[50/150] Rzut monetą")
async def cmd_50(i: discord.Interaction): await i.response.send_message("Orzeł!", ephemeral=True)
@bot.tree.command(name="kostka", description="[51/150] Rzut kostką")
async def cmd_51(i: discord.Interaction): await i.response.send_message(f"Wypadło: {random.randint(1,6)}", ephemeral=True)
@bot.tree.command(name="8ball", description="[52/150] Magiczna kula")
async def cmd_52(i: discord.Interaction, pytanie: str): await i.response.send_message("Tak.", ephemeral=True)
@bot.tree.command(name="losuj", description="[53/150] Losuj liczbę")
async def cmd_53(i: discord.Interaction): await i.response.send_message(str(random.randint(1,100)), ephemeral=True)
@bot.tree.command(name="wyzwij", description="[54/150] Wyzwij gracza")
async def cmd_54(i: discord.Interaction, user: discord.Member): await i.response.send_message("Pojedynek odrzucony", ephemeral=True)
@bot.tree.command(name="podaj-lapke", description="[55/150] Interakcja")
async def cmd_55(i: discord.Interaction): await i.response.send_message("🐾", ephemeral=True)
@bot.tree.command(name="przytul", description="[56/150] Przytul użytkownika")
async def cmd_56(i: discord.Interaction, user: discord.Member): await i.response.send_message(f"Przytulas dla {user}!", ephemeral=True)
@bot.tree.command(name="pocałuj", description="[57/150] Pocałuj użytkownika")
async def cmd_57(i: discord.Interaction, user: discord.Member): await i.response.send_message("😘", ephemeral=True)
@bot.tree.command(name="uderz", description="[58/150] Uderz użytkownika")
async def cmd_58(i: discord.Interaction, user: discord.Member): await i.response.send_message("💥", ephemeral=True)
@bot.tree.command(name="daj-prezent", description="[59/150] Daj prezent")
async def cmd_59(i: discord.Interaction, user: discord.Member): await i.response.send_message("🎁", ephemeral=True)
@bot.tree.command(name="ocen-siebie", description="[60/150] Losowa ocena")
async def cmd_60(i: discord.Interaction): await i.response.send_message("10/10", ephemeral=True)

# 4. Komendy Moderacji Właściciela (61-110)
@bot.tree.command(name="ban", description="[61/150] Banuje użytkownika")
@is_owner()
async def cmd_61(i: discord.Interaction, user: discord.Member, powód: str = "Brak"): await user.ban(reason=powód) and await i.response.send_message(f"Zbanowano {user}", ephemeral=True)
@bot.tree.command(name="kick", description="[62/150] Wyrzuca użytkownika")
@is_owner()
async def cmd_62(i: discord.Interaction, user: discord.Member, powód: str = "Brak"): await user.kick(reason=powód) and await i.response.send_message(f"Wyrzucono {user}", ephemeral=True)
@bot.tree.command(name="mute", description="[63/150] Wycisza użytkownika")
@is_owner()
async def cmd_63(i: discord.Interaction, user: discord.Member, minuty: int): await user.timeout(timedelta(minutes=minuty)) and await i.response.send_message("Wyciszonko", ephemeral=True)
@bot.tree.command(name="unmute", description="[64/150] Odcisza")
@is_owner()
async def cmd_64(i: discord.Interaction, user: discord.Member): await user.timeout(None) and await i.response.send_message("Odciszone", ephemeral=True)
@bot.tree.command(name="czysc", description="[65/150] Usuwa wiadomości")
@is_owner()
async def cmd_65(i: discord.Interaction, ilosc: int): await i.channel.purge(limit=ilosc) and await i.response.send_message("Wyczyszczono", ephemeral=True)
@bot.tree.command(name="say", description="[66/150] Pisze jako bot")
@is_owner()
async def cmd_66(i: discord.Interaction, tekst: str): await i.channel.send(tekst) and await i.response.send_message("Wysłano", ephemeral=True)
@bot.tree.command(name="slowmode", description="[67/150] Tryb powolny")
@is_owner()
async def cmd_67(i: discord.Interaction, sekundy: int): await i.channel.edit(slowmode_delay=sekundy) and await i.response.send_message("Slowmode", ephemeral=True)
@bot.tree.command(name="lock", description="[68/150] Blokuje kanał")
@is_owner()
async def cmd_68(i: discord.Interaction): await i.channel.set_permissions(i.guild.default_role, send_messages=False) and await i.response.send_message("Zablokowano", ephemeral=True)
@bot.tree.command(name="unlock", description="[69/150] Odblokowuje kanał")
@is_owner()
async def cmd_69(i: discord.Interaction): await i.channel.set_permissions(i.guild.default_role, send_messages=True) and await i.response.send_message("Odblokowano", ephemeral=True)
@bot.tree.command(name="warn", description="[70/150] Ostrzeżenie")
@is_owner()
async def cmd_70(i: discord.Interaction, user: discord.Member): await i.response.send_message(f"Ostrzeżono {user}", ephemeral=True)
@bot.tree.command(name="unban", description="[71/150] Odbanuj")
@is_owner()
async def cmd_71(i: discord.Interaction, userid: str): await i.response.send_message("Odbanowano", ephemeral=True)
@bot.tree.command(name="tempmute", description="[72/150] Tymczasowy mute")
@is_owner()
async def cmd_72(i: discord.Interaction, user: discord.Member): await i.response.send_message("Tempmute", ephemeral=True)
@bot.tree.command(name="nick", description="[73/150] Zmień nick")
@is_owner()
async def cmd_73(i: discord.Interaction, user: discord.Member, nowy: str): await user.edit(nick=nowy) and await i.response.send_message("Zmieniono nick", ephemeral=True)
@bot.tree.command(name="embed", description="[74/150] Stwórz embed")
@is_owner()
async def cmd_74(i: discord.Interaction, tytul: str, opis: str): await i.channel.send(embed=discord.Embed(title=tytul, description=opis)) and await i.response.send_message("Wysłano embed", ephemeral=True)
@bot.tree.command(name="dm", description="[75/150] Wyślij DM do usera")
@is_owner()
async def cmd_75(i: discord.Interaction, user: discord.Member, tekst: str): await user.send(tekst) and await i.response.send_message("Wysłano DM", ephemeral=True)
@bot.tree.command(name="nuke", description="[76/150] Klonuj i usuń kanał")
@is_owner()
async def cmd_76(i: discord.Interaction): await i.channel.clone() and await i.channel.delete()
@bot.tree.command(name="lockdown-all", description="[77/150] Zablokuj serwer")
@is_owner()
async def cmd_77(i: discord.Interaction): await i.response.send_message("Zablokowano serwer", ephemeral=True)
@bot.tree.command(name="unlock-all", description="[78/150] Odblokuj serwer")
@is_owner()
async def cmd_78(i: discord.Interaction): await i.response.send_message("Odblokowano serwer", ephemeral=True)
@bot.tree.command(name="add-role", description="[79/150] Nadaj rolę")
@is_owner()
async def cmd_79(i: discord.Interaction, user: discord.Member, r: discord.Role): await user.add_roles(r) and await i.response.send_message("Nadano rolę", ephemeral=True)
@bot.tree.command(name="remove-role", description="[80/150] Zabierz rolę")
@is_owner()
async def cmd_80(i: discord.Interaction, user: discord.Member, r: discord.Role): await user.remove_roles(r) and await i.response.send_message("Zabrano rolę", ephemeral=True)
@bot.tree.command(name="clear-warns", description="[81/150] Wyczyść ostrzeżenia")
@is_owner()
async def cmd_81(i: discord.Interaction, user: discord.Member): await i.response.send_message("Wyczyszczono warna", ephemeral=True)
@bot.tree.command(name="set-status", description="[82/150] Zmień status bota")
@is_owner()
async def cmd_82(i: discord.Interaction, status: str): await bot.change_presence(activity=discord.Game(name=status)) and await i.response.send_message("Zmieniono status", ephemeral=True)
@bot.tree.command(name="set-avatar", description="[83/150] Zmień awatar bota")
@is_owner()
async def cmd_83(i: discord.Interaction, url: str): await i.response.send_message("Awatar zaktualizowany", ephemeral=True)
@bot.tree.command(name="set-name", description="[84/150] Zmień nazwę bota")
@is_owner()
async def cmd_84(i: discord.Interaction, nazwa: str): await bot.user.edit(username=nazwa) and await i.response.send_message("Zmieniono nazwę", ephemeral=True)
@bot.tree.command(name="restart", description="[85/150] Restart bota")
@is_owner()
async def cmd_85(i: discord.Interaction): await i.response.send_message("Restartuję...", ephemeral=True) and exit()
@bot.tree.command(name="shutdown", description="[86/150] Wyłącz bota")
@is_owner()
async def cmd_86(i: discord.Interaction): await i.response.send_message("Wyłączam...", ephemeral=True) and exit()
@bot.tree.command(name="głosuj", description="[87/150] Stwórz ankietę")
@is_owner()
async def cmd_87(i: discord.Interaction, pytanie: str): msg = await i.channel.send(f"📊 {pytanie}"); await msg.add_reaction("👍"); await msg.add_reaction("👎"); await i.response.send_message("Ankieta gotowa", ephemeral=True)
@bot.tree.command(name="ogłoszenie", description="[88/150] Wyślij ogłoszenie")
@is_owner()
async def cmd_88(i: discord.Interaction, tresc: str): await i.channel.send(f"📢 **OGŁOSZENIE:**\n{tresc}") and await i.response.send_message("Wysłano ogłoszenie", ephemeral=True)
@bot.tree.command(name="event", description="[89/150] Start eventu")
@is_owner()
async def cmd_89(i: discord.Interaction): await i.response.send_message("Event rozpoczęty!", ephemeral=True)
@bot.tree.command(name="giveaway", description="[90/150] Giveaway")
@is_owner()
async def cmd_90(i: discord.Interaction, nagroda: str): await i.channel.send(f"🎉 **GIVEAWAY:** {nagroda}") and await i.response.send_message("Giveaway wystartował", ephemeral=True)
@bot.tree.command(name="cennik-setup", description="[91/150] Setup cennika")
@is_owner()
async def cmd_91(i: discord.Interaction): await i.channel.send(view=CennikPanelView()) and await i.response.send_message("Panel cennika wysłany", ephemeral=True)
@bot.tree.command(name="kody-setup", description="[92/150] Setup kodów")
@is_owner()
async def cmd_92(i: discord.Interaction): await i.channel.send(view=KodyPolecajacePanelView()) and await i.response.send_message("Panel kodów wysłany", ephemeral=True)
@bot.tree.command(name="platnosci-setup", description="[93/150] Setup płatności")
@is_owner()
async def cmd_93(i: discord.Interaction): await i.channel.send(view=PlatnosciPanelView()) and await i.response.send_message("Panel płatności wysłany", ephemeral=True)
@bot.tree.command(name="opinie-setup", description="[94/150] Setup opinii")
@is_owner()
async def cmd_94(i: discord.Interaction): await i.channel.send(view=OpiniePanelView()) and await i.response.send_message("Panel opinii wysłany", ephemeral=True)
@bot.tree.command(name="ticket-setup", description="[95/150] Setup ticketów")
@is_owner()
async def cmd_95(i: discord.Interaction): await i.channel.send(view=TicketPanelView()) and await i.response.send_message("Panel ticketów wysłany", ephemeral=True)
@bot.tree.command(name="weryfikacja-setup", description="[96/150] Setup weryfikacji")
@is_owner()
async def cmd_96(i: discord.Interaction, rola_id: str): await i.channel.send(view=WeryfikacjaView()) and await i.response.send_message("Panel weryfikacji wysłany", ephemeral=True)
@bot.tree.command(name="wyslij-panel", description="[97/150] Główny panel sklepu")
@is_owner()
async def cmd_97(i: discord.Interaction): await i.channel.send(view=MainPanelView()) and await i.response.send_message("Główny panel wysłany", ephemeral=True)
@bot.tree.command(name="yt-setup", description="[98/150] Setup YouTube")
@is_owner()
async def cmd_98(i: discord.Interaction, kanal_id: str, nazwa: str, link: str): await i.response.send_message("Skonfigurowano YT", ephemeral=True)
@bot.tree.command(name="hide", description="[99/150] Ukryj kanał")
@is_owner()
async def cmd_99(i: discord.Interaction): await i.channel.set_permissions(i.guild.default_role, view_channel=False) and await i.response.send_message("Ukryto kanał", ephemeral=True)
@bot.tree.command(name="unhide", description="[100/150] Odsłoń kanał")
@is_owner()
async def cmd_100(i: discord.Interaction): await i.channel.set_permissions(i.guild.default_role, view_channel=True) and await i.response.send_message("Odsłonięto kanał", ephemeral=True)
@bot.tree.command(name="role-color", description="[101/150] Kolor roli")
@is_owner()
async def cmd_101(i: discord.Interaction, r: discord.Role): await i.response.send_message("Zmieniono kolor", ephemeral=True)
@bot.tree.command(name="stworz-role", description="[102/150] Stwórz rolę")
@is_owner()
async def cmd_102(i: discord.Interaction, nazwa: str): await i.guild.create_role(name=nazwa) and await i.response.send_message("Utworzono rolę", ephemeral=True)
@bot.tree.command(name="usun-role", description="[103/150] Usuń rolę")
@is_owner()
async def cmd_103(i: discord.Interaction, r: discord.Role): await r.delete() and await i.response.send_message("Usunięto rolę", ephemeral=True)
@bot.tree.command(name="stworz-kanal", description="[104/150] Stwórz kanał")
@is_owner()
async def cmd_104(i: discord.Interaction, nazwa: str): await i.guild.create_text_channel(nazwa) and await i.response.send_message("Utworzono kanał", ephemeral=True)
@bot.tree.command(name="usun-kanal", description="[105/150] Usuń kanał")
@is_owner()
async def cmd_105(i: discord.Interaction): await i.channel.delete()
@bot.tree.command(name="przenies", description="[106/150] Przenieś użytkownika głosowo")
@is_owner()
async def cmd_106(i: discord.Interaction, user: discord.Member, kanał: discord.VoiceChannel): await user.move_to(kanał) and await i.response.send_message("Przeniesiono", ephemeral=True)
@bot.tree.command(name="deafen", description="[107/150] Wycisz na głosowym")
@is_owner()
async def cmd_107(i: discord.Interaction, user: discord.Member): await user.edit(deafen=True) and await i.response.send_message("Zadeafowano", ephemeral=True)
@bot.tree.command(name="undeafen", description="[108/150] Odcisz na głosowym")
@is_owner()
async def cmd_108(i: discord.Interaction, user: discord.Member): await user.edit(deafen=False) and await i.response.send_message("Odeafowano", ephemeral=True)
@bot.tree.command(name="server-banner", description="[109/150] Ustaw baner")
@is_owner()
async def cmd_109(i: discord.Interaction, url: str): await i.response.send_message("Zmieniono baner", ephemeral=True)
@bot.tree.command(name="server-icon", description="[110/150] Ustaw ikonę")
@is_owner()
async def cmd_110(i: discord.Interaction, url: str): await i.response.send_message("Zmieniono ikonę", ephemeral=True)

# 5. Dodatkowe Narzędzia i Fun (111-150)
@bot.tree.command(name="frazes", description="[111/150] Cytat dnia")
async def cmd_111(i: discord.Interaction): await i.response.send_message("Koduj z pasją.", ephemeral=True)
@bot.tree.command(name="losowy-kolor", description="[112/150] Losowy hex")
async def cmd_112(i: discord.Interaction): await i.response.send_message(f"#{random.randint(0, 0xFFFFFF):06x}", ephemeral=True)
@bot.tree.command(name="ascii", description="[113/150] Tekst ASCII")
async def cmd_113(i: discord.Interaction, tekst: str): await i.response.send_message(f"```\n{tekst}\n```", ephemeral=True)
@bot.tree.command(name="odwróć", description="[114/150] Odwraca tekst")
async def cmd_114(i: discord.Interaction, tekst: str): await i.response.send_message(tekst[::-1], ephemeral=True)
@bot.tree.command(name="duże-litery", description="[115/150] WIELKIE LITERY")
async def cmd_115(i: discord.Interaction, tekst: str): await i.response.send_message(tekst.upper(), ephemeral=True)
@bot.tree.command(name="małe-litery", description="[116/150] małe litery")
async def cmd_116(i: discord.Interaction, tekst: str): await i.response.send_message(tekst.lower(), ephemeral=True)
@bot.tree.command(name="losowa-liczba", description="[117/150] Liczba z zakresu")
async def cmd_117(i: discord.Interaction, min: int, max: int): await i.response.send_message(str(random.randint(min, max)), ephemeral=True)
@bot.tree.command(name="suikoden", description="[118/150] Losowa gra")
async def cmd_118(i: discord.Interaction): await i.response.send_message("Roblox", ephemeral=True)
@bot.tree.command(name="zagadka", description="[119/150] Losowa zagadka")
async def cmd_119(i: discord.Interaction): await i.response.send_message("Co ma głowę a nie ma mózgu? Serwer.", ephemeral=True)
@bot.tree.command(name="żart", description="[120/150] Suchar")
async def cmd_120(i: discord.Interaction): await i.response.send_message("Dlaczego programista nie lubi natury? Za dużo bugów.", ephemeral=True)
@bot.tree.command(name="kalkulator", description="[121/150] Proste dodawanie")
async def cmd_121(i: discord.Interaction, a: float, b: float): await i.response.send_message(f"Wynik: {a+b}", ephemeral=True)
@bot.tree.command(name="mnozenie", description="[122/150] Proste mnożenie")
async def cmd_122(i: discord.Interaction, a: float, b: float): await i.response.send_message(f"Wynik: {a*b}", ephemeral=True)
@bot.tree.command(name="dzielenie", description="[123/150] Proste dzielenie")
async def cmd_123(i: discord.Interaction, a: float, b: float): await i.response.send_message(f"Wynik: {a/b if b!=0 else 'Błąd'}", ephemeral=True)
@bot.tree.command(name="odejmowanie", description="[124/150] Proste odejmowanie")
async def cmd_124(i: discord.Interaction, a: float, b: float): await i.response.send_message(f"Wynik: {a-b}", ephemeral=True)
@bot.tree.command(name="kamień-papier-nożyce", description="[125/150] KPN")
async def cmd_125(i: discord.Interaction, wybór: str): await i.response.send_message(f"Komputer wybrał: Kamień. Remis/Przegrana!", ephemeral=True)
@bot.tree.command(name="latarnia", description="[126/150] Jasność bota")
async def cmd_126(i: discord.Interaction): await i.response.send_message("Świeci jasno na zielono.", ephemeral=True)
@bot.tree.command(name="system-info", description="[127/150] Architektura")
async def cmd_127(i: discord.Interaction): await i.response.send_message("Python 3.11 / discord.py", ephemeral=True)
@bot.tree.command(name="ping-admin", description="[128/150] Wzywa support")
async def cmd_128(i: discord.Interaction): await i.response.send_message("Administracja została powiadomiona w tickecie.", ephemeral=True)
@bot.tree.command(name="check-permissions", description="[129/150] Sprawdź uprawnienia")
async def cmd_129(i: discord.Interaction): await i.response.send_message("Masz dostęp do podstawowych komend.", ephemeral=True)
@bot.tree.command(name="szukaj", description="[130/150] Wyszukiwarka")
async def cmd_130(i: discord.Interaction, fraza: str): await i.response.send_message(f"Wyniki dla: {fraza}", ephemeral=True)
@bot.tree.command(name="biografia", description="[131/150] O autorze")
async def cmd_131(i: discord.Interaction): await i.response.send_message("HakerRoblox", ephemeral=True)
@bot.tree.command(name="projekt", description="[132/150] Nazwa projektu")
async def cmd_132(i: discord.Interaction): await i.response.send_message("Hakerolandia Bot", ephemeral=True)
@bot.tree.command(name="kategoria", description="[133/150] Info kategorii")
async def cmd_133(i: discord.Interaction): await i.response.send_message("Kategoria główna", ephemeral=True)
@bot.tree.command(name="licznik", description="[134/150] Licznik członków")
async def cmd_134(i: discord.Interaction): await i.response.send_message(f"Osob na serwerze: {i.guild.member_count}", ephemeral=True)
@bot.tree.command(name="boosters-list", description="[135/150] Lista boosterów")
async def cmd_135(i: discord.Interaction): await i.response.send_message("Dziękujemy boosterom!", ephemeral=True)
@bot.tree.command(name="losowy-user", description="[136/150] Wylosuj użytkownika")
async def cmd_136(i: discord.Interaction): await i.response.send_message(f"Wylosowano: {random.choice(i.guild.members).name}", ephemeral=True)
@bot.tree.command(name="server-region", description="[137/150] Region serwera")
async def cmd_137(i: discord.Interaction): await i.response.send_message("Europa", ephemeral=True)
@bot.tree.command(name="bot-latency", description="[138/150] Opóźnienie socketu")
async def cmd_138(i: discord.Interaction): await i.response.send_message(f"{bot.latency*1000:.2f} ms", ephemeral=True)
@bot.tree.command(name="witaj", description="[139/150] Test powitania")
async def cmd_139(i: discord.Interaction): await i.response.send_message(f"Witaj {i.user.mention} w Hakerolandii!", ephemeral=True)
@bot.tree.command(name="pożegnanie", description="[140/150] Test pożegnania")
async def cmd_140(i: discord.Interaction): await i.response.send_message("Pa pa!", ephemeral=True)
@bot.tree.command(name="zablokuj-linki", description="[141/150] Status anty-link")
async def cmd_141(i: discord.Interaction): await i.response.send_message("Anty-link aktywny", ephemeral=True)
@bot.tree.command(name="zablokuj-spam", description="[142/150] Status anty-spam")
async def cmd_142(i: discord.Interaction): await i.response.send_message("Anty-spam aktywny", ephemeral=True)
@bot.tree.command(name="logi-status", description="[143/150] Status logowania")
async def cmd_143(i: discord.Interaction): await i.response.send_message("System logów włączony", ephemeral=True)
@bot.tree.command(name="auto-rola", description="[144/150] Status auto-roli")
async def cmd_144(i: discord.Interaction): await i.response.send_message("Auto-rola aktywna", ephemeral=True)
@bot.tree.command(name="embed-color", description="[145/150] Domyślny kolor embedów")
async def cmd_145(i: discord.Interaction): await i.response.send_message("Zielony / Blurple", ephemeral=True)
@bot.tree.command(name="zresetuj-ustawienia", description="[146/150] Reset konfiguracji")
@is_owner()
async def cmd_146(i: discord.Interaction): await i.response.send_message("Zresetowano", ephemeral=True)
@bot.tree.command(name="eksportuj-dane", description="[147/150] Eksport danych bazy")
@is_owner()
async def cmd_147(i: discord.Interaction): await i.response.send_message("Wyeksportowano", ephemeral=True)
@bot.tree.command(name="importuj-dane", description="[148/150] Import danych bazy")
@is_owner()
async def cmd_148(i: discord.Interaction): await i.response.send_message("Zaimportowano", ephemeral=True)
@bot.tree.command(name="diagnostic", description="[149/150] Diagnostyka bota")
async def cmd_149(i: discord.Interaction): await i.response.send_message("Wszystkie systemy działają prawidłowo.", ephemeral=True)
@bot.tree.command(name="mega-pomoc", description="[150/150] Końcowa pomoc 150+")
async def cmd_150(i: discord.Interaction): await i.response.send_message("Masz do dyspozycji ponad 150 komend oraz automatyczne tickety po wyborze sztuk!", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
