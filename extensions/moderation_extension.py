import datetime
from interactions import Button, ButtonStyle, Embed, EmbedField, Extension, Color, OptionType
import interactions
from redis import Redis

class ModerationExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        # 4 is the DB for keeping track of warns
        self.warndb = Redis(db=4)
        # 5 is the DB for keeping track of warn instances
        self.instancedb = Redis(db=5)

        self.TIMEOUT_FIRST_INSTANCE, self.TIMEOUT_SECOND_INSTANCE, self.TIMEOUT_THIRD_INSTANCE = datetime.timedelta(minutes=5), datetime.timedelta(hours=1), datetime.timedelta(days=1)

    ### warn command stuff ###
    @interactions.slash_command(
        name="warn",
        description="Warn a user"
    )
    @interactions.slash_option(
        name="user",
        description="The user to warn",
        required=True,
        opt_type=OptionType.USER
    )
    @interactions.slash_option(
        name="reason",
        description="The reason for the warning",
        required=True,
        opt_type=OptionType.STRING
    )
    async def warn(self, ctx, user, reason):
        warns = self.warndb.get(user.id)
        if warns is None: warns = 0
        else: warns = int(warns)
        warns += 1
        self.warndb.set(user.id, warns)
        instances = self.instancedb.get(user.id)
        if instances is None: instances = 0
        else: instances = int(instances)
        if warns == 3:
            instances += 1
            self.instancedb.set(user.id, instances)
            if instances == 1:
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + self.TIMEOUT_FIRST_INSTANCE
                timeout_str = "5 minutes"
            if instances == 2: 
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + self.TIMEOUT_SECOND_INSTANCE
                timeout_str = "1 hour"
            if instances == 3: 
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + self.TIMEOUT_THIRD_INSTANCE
                timeout_str = "1 day"
            await ctx.guild.get_member(user.id).timeout(timeout_until, reason=reason)
            self.warndb.set(user.id, 0)
            timeout_embed = Embed(
                title="User Timed Out", 
                color=Color.random(),
                description=f"{user.mention} has been timed out for {timeout_str} due to reaching 3 warnings."
            )
            await ctx.send(embed=timeout_embed)
        warn_embed = Embed(
            title="User Warned",
            color=Color.random(),
            description=f"{user.mention} has been warned for: {reason}"
        )
        warn_embed.add_field(name="Current Warn Count", value=f"{warns}")
        warn_embed.add_field(name="Current Warning Instance", value=f"{instances}")
        warn_embed.set_footer(text="At 3 warnings, the user will be timed out.")
        await ctx.send(embed=warn_embed)
    
    @interactions.slash_command(
        name="warns",
        description="Check the number of warns a user has"
    )
    @interactions.slash_option(
        name="user",
        description="The user to check",
        required=True,
        opt_type=OptionType.USER
    )
    async def warns(self, ctx, user):
        warns = self.warndb.get(user.id)
        instances = self.instancedb.get(user.id)
        if warns is None: warns = 0
        else: warns = int(warns)
        if instances is None: instances = 0
        else: instances = int(instances)
        warn_embed = Embed(
            title=f"Warning Information for {user.display_name}",
            color=Color.random()
        )
        warn_embed.add_field(name="Current Warn Count", value=f"{warns}")
        warn_embed.add_field(name="Total Warning Instances", value=f"{instances}")
        await ctx.send(embed=warn_embed)
    
    @interactions.slash_command(
        name="clearwarns",
        description="Clear the warns of a user"
    )
    @interactions.slash_option(
        name="user",
        description="The user to clear warns for",
        required=True,
        opt_type=OptionType.USER
    )
    async def clearwarns(self, ctx, user):
        self.warndb.delete(user.id)
        self.instancedb.delete(user.id)
        clear_embed = Embed(
            title="Warnings Cleared",
            color=Color.random(),
            description=f"All warnings have been cleared for {user.mention}."
        )
        await ctx.send(embed=clear_embed, ephemeral=True)
    
    ### end warn command stuff ###