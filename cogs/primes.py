import discord
import aiosqlite
import asyncio
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput, View, Button
from discord import Interaction, app_commands
from utils.paladium_api import verify_player_basic

DB_PATH = "primes.db"

# IDs (from user)
GUILD_ID = 1402777306455478354
ADMIN_CHANNEL = 1402778898923651242
TICKETS_CATEGORY = 1403037947476836523
PUBLIC_CHANNEL = 1402779650421424168
ROLE_STAFF_ID = 1402780875694801007
ROLE_CHASSEURS_ID = None
CLASSEMENT_CHANNEL = 1403741125596151980

class PrimeModal(Modal, title="Déposer une Prime Paladium"):
    pseudo = TextInput(label="Ton pseudo Minecraft/Paladium", max_length=32)
    cible = TextInput(label="Pseudo de la cible", max_length=32)
    montant = TextInput(label="Montant de la prime (ex: 5000$)", max_length=32)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        # Appels synchrones à verify_player_basic, donc sans await
        ch = verify_player_basic(self.pseudo.value)
        if not ch["ok"]:
            await interaction.followup.send(f"❌ Vérification déposant: {ch['reason']}", ephemeral=True)
            return
        ci = verify_player_basic(self.cible.value)
        if not ci["ok"]:
            await interaction.followup.send(f"❌ Vérification cible: {ci['reason']}", ephemeral=True)
            return
        faction_ch = ch["data"].get("faction")
        faction_ci = ci["data"].get("faction")
        if faction_ch and faction_ci and faction_ch == faction_ci:
            await interaction.followup.send("❌ Déposant et cible sont dans la même faction (anti-faction).", ephemeral=True)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO primes (chasseur, chasseur_discord, cible, montant, preuve, status) VALUES (?, ?, ?, ?, ?, ?)",
                (self.pseudo.value, interaction.user.id, self.cible.value, self.montant.value, None, "awaiting_proof")
            )
            await db.commit()
            prime_id = cur.lastrowid

        try:
            await interaction.user.send(
                f"Merci ! Ta prime a été enregistrée (ID {prime_id}).\nEnvoie maintenant **une image** de la preuve de paiement en réponse à ce message."
            )
            await interaction.followup.send("✅ Prime enregistrée — envoie la preuve (image) en DM au bot.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠ Impossible d'envoyer un DM — active les DM pour recevoir la demande de preuve.", ephemeral=True)

class AdminValidationView(View):
    def __init__(self, prime_id: int):
        super().__init__(timeout=None)
        self.prime_id = prime_id

    @discord.ui.button(label="Accepter ✅", style=discord.ButtonStyle.green)
    async def accept(self, interaction: Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT chasseur, chasseur_discord, cible, montant, preuve FROM primes WHERE id = ?", (self.prime_id,))
            row = await cur.fetchone()
            if not row:
                await interaction.response.send_message("Prime introuvable.", ephemeral=True)
                return
            chasseur, chasseur_discord, cible, montant, preuve = row
            await db.execute("UPDATE primes SET status = 'accepted' WHERE id = ?", (self.prime_id,))
            await db.commit()

        public_channel = interaction.guild.get_channel(PUBLIC_CHANNEL)
        role_mention = f"<@&{ROLE_CHASSEURS_ID}>" if ROLE_CHASSEURS_ID else ""
        embed = discord.Embed(title=f"🎯 Prime #{self.prime_id} publiée", color=discord.Color.gold())
        embed.add_field(name="Cible", value=cible, inline=True)
        embed.add_field(name="Montant", value=montant, inline=True)
        embed.add_field(name="Déposée par", value=chasseur, inline=False)
        if preuve:
            embed.set_image(url=preuve)

        msg = await public_channel.send(content=role_mention, embed=embed, view=ClaimView(self.prime_id))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE primes SET published_message_id = ? WHERE id = ?", (msg.id, self.prime_id))
            await db.commit()

        try:
            user = await interaction.client.fetch_user(chasseur_discord)
            await user.send(f"✅ Ta prime (ID {self.prime_id}) a été acceptée et publiée.")
        except Exception:
            pass

        await interaction.response.send_message("Prime acceptée et publiée.", ephemeral=True)

    @discord.ui.button(label="Refuser ❌", style=discord.ButtonStyle.red)
    async def reject(self, interaction: Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT chasseur_discord FROM primes WHERE id = ?", (self.prime_id,))
            row = await cur.fetchone()
            await db.execute("UPDATE primes SET status = 'rejected' WHERE id = ?", (self.prime_id,))
            await db.commit()
        if row:
            try:
                user = await interaction.client.fetch_user(row[0])
                await user.send(f"❌ Ta prime (ID {self.prime_id}) a été refusée par le staff.")
            except Exception:
                pass
        await interaction.response.send_message("Prime refusée.", ephemeral=True)

class ClaimView(View):
    def __init__(self, prime_id: int):
        super().__init__(timeout=None)
        self.prime_id = prime_id

    @discord.ui.button(label="Réclamer la prime", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=TICKETS_CATEGORY)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_role(ROLE_STAFF_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel_name = f"ticket-prime-{self.prime_id}-{interaction.user.id}"
        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, reason="Réclamation prime")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO claims (prime_id, claimer_discord) VALUES (?, ?)", (self.prime_id, interaction.user.id))
            await db.commit()
        await ticket_channel.send(f"<@&{ROLE_STAFF_ID}> — <@{interaction.user.id}> a réclamé la prime #{self.prime_id}.")
        await interaction.response.send_message(f"Ticket créé : {ticket_channel.mention}", ephemeral=True)

class PrimesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_leaderboard.start()

    def cog_unload(self):
        self.update_leaderboard.cancel()

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS primes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chasseur TEXT,
                    chasseur_discord INTEGER,
                    cible TEXT,
                    montant TEXT,
                    preuve TEXT,
                    status TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    published_message_id INTEGER
                )""")
            await db.execute("""CREATE TABLE IF NOT EXISTS claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prime_id INTEGER,
                    claimer_discord INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            await db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.init_db()

    @tasks.loop(minutes=5.0)
    async def update_leaderboard(self):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT chasseur, montant FROM primes WHERE status = 'accepted'")
            rows = await cur.fetchall()

        stats = {}
        for ch, montant in rows:
            value = 0
            if montant:
                try:
                    cleaned = "".join(c for c in str(montant) if (c.isdigit() or c == '.' or c == ',')).replace(',', '.')
                    value = float(cleaned) if cleaned else 0
                except Exception:
                    value = 0
            if ch not in stats:
                stats[ch] = {"count": 0, "sum": 0.0}
            stats[ch]["count"] += 1
            stats[ch]["sum"] += value

        sorted_by_sum = sorted(stats.items(), key=lambda kv: kv[1]["sum"], reverse=True)
        embed = discord.Embed(title="🏆 Classement des chasseurs — Top 10", color=discord.Color.dark_gold())
        description = ""
        for i, (ch, s) in enumerate(sorted_by_sum[:10], start=1):
            description += f"**{i}. {ch}** — {int(s['count'])} primes — {int(s['sum'])}$\n"
        if not description:
            description = "Aucun chasseur enregistré pour l'instant."

        embed.description = description
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        channel = guild.get_channel(CLASSEMENT_CHANNEL)
        if not channel:
            return

        try:
            async for msg in channel.history(limit=50):
                if msg.author == self.bot.user and msg.embeds:
                    await msg.edit(embed=embed)
                    return
            await channel.send(embed=embed)
        except Exception:
            pass

    @update_leaderboard.before_loop
    async def before_leaderboard(self):
        await self.bot.wait_until_ready()

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="prime-deploy", description="Déployer le message expliquant comment déposer une prime")
    @app_commands.checks.has_permissions(administrator=True)
    async def prime_deploy(self, interaction: Interaction):
        embed = discord.Embed(title="🎯 Bienvenue sur Les Primes de Paladium", color=discord.Color.blue())
        embed.description = (
            "Pour poser une prime :\n"
            "• Clique sur **Déposer une prime**\n"
            "• Remplis ton pseudo, la cible et le montant\n"
            "• Tu recevras en DM la demande d'envoyer la preuve (image)\n\n"
            "📌 Une taxe de 1000$ est appliquée à chaque dépôt (à régler en jeu au compte Lesprimesdepala).\n"
            "🛡️ Pas de triche : vérification via l'API Paladium (comptes crack / doubles / même faction).\n"
            "Les primes validées seront publiées publiquement et affichées sur le classement."
        )
        view = View()
        view.add_item(Button(label="Déposer une prime", style=discord.ButtonStyle.primary, custom_id="open_prime_modal"))
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            cid = interaction.data.get("custom_id")
            if cid == "open_prime_modal":
                await interaction.response.send_modal(PrimeModal())

async def setup(bot):
    await bot.add_cog(PrimesCog(bot))
