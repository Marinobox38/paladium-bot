import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import Interaction

GUILD_ID = 1402777306455478354
TICKETS_CATEGORY = 1403037947476836523
ROLE_STAFF_ID = 1402780875694801007

class TicketCloseView(View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: Interaction, button):
        chan = interaction.client.get_channel(self.channel_id)
        if chan:
            await chan.send("Fermeture du ticket dans 5 secondes...")
            await discord.utils.sleep_until(discord.utils.utcnow()+discord.timedelta(seconds=5))
            try:
                await chan.delete(reason=f"Ticket fermé par {interaction.user}")
            except Exception:
                await interaction.response.send_message("Impossible de supprimer le salon.", ephemeral=True)
            else:
                await interaction.response.send_message("Ticket fermé.", ephemeral=True)
        else:
            await interaction.response.send_message("Salon introuvable.", ephemeral=True)

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="ticket-deploy", description="Déployer le message d'ouverture de ticket")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_deploy(self, interaction: Interaction):
        embed = discord.Embed(title="📩 Ouvrir un ticket", description=(
            "Règlement des tickets :\n"
            "- Utilise un ticket pour réclamations liées aux primes uniquement.\n"
            "- Fournis toutes les preuves nécessaires.\n"
            "- Respecte le staff et les autres joueurs."
        ), color=discord.Color.blurple())
        view = View()
        view.add_item(Button(label="Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn"))
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            cid = interaction.data.get("custom_id")
            if cid == "open_ticket_btn":
                guild = interaction.guild
                category = discord.utils.get(guild.categories, id=TICKETS_CATEGORY)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.get_role(ROLE_STAFF_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                }
                channel_name = f"ticket-{interaction.user.id}"
                ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, reason="Ticket ouvert via deploy")
                view = TicketCloseView(ticket_channel.id)
                await ticket_channel.send(f"<@&{ROLE_STAFF_ID}> — Ticket ouvert par <@{interaction.user.id}>", view=view)
                await interaction.response.send_message(f"✅ Ticket créé : {ticket_channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
