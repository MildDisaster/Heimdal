#
# Heimdal - A discord bot to verify new users
#           with discord.py v1.2.3
#
# This validates against php service that returns a json object :
#
#   {
#        image_path: "https:/path/to/generated/image/file",
#        valid_response : "generatedString"
#   }
#



#
# some friends

import aiohttp
import aiofiles
import discord

from discord.ext import commands
from os.path import isfile
from datetime import datetime


#
# some properties

token = 'YOUR_INFOS_HERE'

role_unverified = 'unverified'
role_verified = 'verified'
channel_jail = 'welcome'
log_file = 'heimdal.log'
log_limit = 100
challenge_url = 'YOUR_INFOS_HERE'
thumbnail_url = 'YOUR_INFOS_HERE'

bot = commands.Bot(command_prefix='?', description='Eternal Guardian')
bot.remove_command('help')





#
# some functions

def is_channel(ctx, channel=channel_jail):
    if ctx.message.channel.name == channel:
        return True
    else:
        raise commands.DisabledCommand(f'This command is not applicable here')


def setup_log():
    if not isfile(log_file):
        print(f'New logfile created at : {log_file}')
        open(log_file, 'a').close()





async def add_log(msg):

    # local list to store the magic
    logs = list()

    # lets cook up a timestamp
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # lets format our message a bit
    clean_msg = f'[{ts}] - '+msg

    # read file into our list
    async with aiofiles.open(log_file, 'r') as afp:
        async for log_line in afp:
            logs.append(log_line.strip('\n'))

    # append our new message
    logs.append(clean_msg)

    # pop the oldest items off if we need to
    if len(logs) > log_limit :
        logs.pop(0)

    # write list back out to file
    async with aiofiles.open(log_file, 'w') as afp:
        await afp.writelines(['%s\n' % log for log in logs])





#
# some commands

@bot.command()
@commands.check(is_channel)
async def verify(ctx):

    # we want to delete all messages by the author, as well as our welcome message
    channel = ctx.message.channel
    author_id = ctx.message.author.id
    author_name = ctx.message.author.name
    match = f'Hello {author_name},'

    async for message in channel.history().filter(lambda m: m.author.id == author_id):
        await message.delete()

    async for message in channel.history().filter(lambda m: m.author.bot):
        if match in message.content:
            await message.delete()

    # check for status
    unverified = discord.utils.get(ctx.guild.roles, name=role_unverified)
    if unverified in ctx.author.roles:

        await add_log(f'User {ctx.author.name} has started verification')

        # lets go fetch our captcha challenge/response object
        async with aiohttp.ClientSession() as session:
            async with session.get(challenge_url) as get:
                if get.status == 200:
                    reply = await get.json()

        # send message to notify a DM has been sent
        dm_notice = await ctx.send('Sending verification challenge via DM')

        # send our challenge
        embed = discord.Embed(
            title='\u2015 **Verification** \u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015',
            color=0x588DA0)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(
            name='\a',
            value='Please reply here with the characters from the image below.',
            inline=False
        )
        embed.set_image(url=reply['image_path'])
        embed.set_footer(text='**Note:** This is case sensitive')
        await ctx.author.send(embed=embed)

        # update notify
        await dm_notice.add_reaction('✅')

        # our check response function
        def check(m):
            return m.content == reply['valid_response']

        # wait for response
        response = await bot.wait_for('message', check=check)

        # set our verified role
        verify_role = discord.utils.get(ctx.guild.roles, name=role_verified)
        await ctx.author.add_roles(verify_role)

        # remove unverified role
        await ctx.author.remove_roles(unverified)

        # send congratulatory blurb
        embed = discord.Embed(
            title='\u2015 **Verified** \u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015\u2015',
            color=0x588DA0)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name='Thank you', value='You now have access to the server!')
        await ctx.author.send(embed=embed)

        # delete messages
        await dm_notice.delete()

        await add_log(f'User {ctx.author.name} has been verified')

    else:
        await add_log(f'User {ctx.author.name} is already verified')
        raise commands.CheckFailure(f'User: {ctx.author.name} is already verifed ')





#
# some events

@bot.event
async def on_ready():
    print(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(activity=discord.Game(name='with Gjallarhorn'))
    print(f'Successfully logged in and booted...!')
    setup_log()


@bot.event
async def on_member_join(member):
    await add_log(f'User {member.name} has joined the server')

    unverified = discord.utils.get(member.guild.roles, name=role_unverified)
    await member.add_roles(unverified)

    channel = discord.utils.get(member.guild.text_channels, name=channel_jail)
    await channel.send(f'Hello {member.name}, please type ?verify to begin')





#
# bombs away !
bot.run(token, bot=True, reconnect=True)