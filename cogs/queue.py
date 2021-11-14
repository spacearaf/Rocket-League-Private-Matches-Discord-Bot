# -*- coding: utf-8 -*-

import discord
from discord.ext import commands

from collections import OrderedDict
import time
import asyncio

from models.player import Player
from models.game_handler import GameHandler
from models.game_balanced import BalancedGame
from models.game_captains import CaptainsGame
from models.game_random import RandomGame
from db.database import record

embed_template = discord.Embed(
    title='Private Matches',
    colour=discord.Colour.dark_red()
)
embed_template.set_footer(
    text='UEA Private Matches by curpha',
    icon_url='https://cdn.akamai.steamstatic.com/steamcommunity/public/images/avatars/be/bed810f8bebd7be235b8f7176e3870de1006a6e5_full.jpg'
)


class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.users_in_queue = OrderedDict()

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context):
        # print(ctx.message.channel.name)  # this works btw

        if self.users_in_queue.get(ctx.author.id, False):
            await ctx.channel.send(f'You are already in the queue, {ctx.author.mention}.')
            return

        res = record("SELECT * FROM player WHERE discord_id = ?", ctx.author.id)

        if res is None:
            await ctx.channel.send(f'You have not set your mmr, please use: `;setmmr amount`!')
            return

        self.users_in_queue[ctx.author.id] = Player(ctx.author, res[1])

        embed = embed_template.copy()

        if len(self.users_in_queue) == 1:
            embed.add_field(
                name='Queue Started!',
                value=f'{ctx.author.mention} has started a queue, type `;q` or `;queue` to join!',
                inline=False
            )
        else:
            embed.add_field(
                name='User Joined the Queue!',
                value=f'{ctx.author.mention} joined the queue, type `;q` or `;queue` to join!',
                inline=False
            )
            embed.add_field(
                name=f'Users in Queue: {str(len(self.users_in_queue))}',
                value=', '.join(user.mention for user in self.users_in_queue),
                inline=False
            )

        await ctx.channel.send(embed=embed)

        # if len(self.users_in_queue) == 6:
        if len(self.users_in_queue) == 1:  # testing
            game_users = []

            # for i in range(6):
            for i in range(1):  # testing
                game_users.append(self.users_in_queue.popitem(last=False)[1])

            game_handler = GameHandler(6, game_users)

            loop = asyncio.get_event_loop()
            loop.create_task(self.create_game(ctx, game_handler))

    async def create_game(self, ctx, game_handler):
        """
        Creates a game for the users who are in the queue.
        """
        embed = embed_template.copy()
        users = game_handler.get_users()

        print("\n")
        print(users)
        print("\n")

        embed.add_field(
            name='Game Created!',
            value=', '.join(user.get_discord_user().mention for user in users),
            inline=False
        )

        embed.add_field(
            name='Vote for Balancing Method!!',
            value=f'🇧 for Balanced Teams\n\n🇨 for Captains\n\n🇷 for Random Teams',
            inline=False
        )

        message = await ctx.channel.send(embed=embed)
        await message.add_reaction("🇧")
        await message.add_reaction("🇨")
        await message.add_reaction("🇷")

        temp = [user for user in users]

        balanced = 0
        captains = 0
        random = 0

        time_start = time.time() + 10  # should be 120 (2 mins)
        listen_for_reaction = True

        def check(reaction, user):
            return user in users and message == reaction.message

        while len(temp) > 0 and listen_for_reaction:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=time_start - time.time(), check=check)

                if reaction.emoji == "🇧":
                    balanced += 1
                elif reaction.emoji == "🇨":
                    captains += 1
                elif reaction.emoji == "🇷":
                    random += 1

                # if user in temp:
                #     temp.remove(user)
            except asyncio.TimeoutError:
                listen_for_reaction = False

        if balanced > captains and balanced > random:
            game = BalancedGame(users)
        elif captains > balanced and captains > random:
            game = CaptainsGame(users)
        else:
            game = RandomGame(users)

        await game.assign_teams()

        embed = embed_template.copy()

        embed.add_field(
            name='Team 1',
            value=', '.join(user.mention for user in game.get_team_one),
            inline=False
        )

        embed.add_field(
            name='Team 2',
            value=', '.join(user.mention for user in game.get_team_two),
            inline=False
        )

        await ctx.channel.send(embed=embed)

    @commands.command(aliases=['l'])
    async def leave(self, ctx: commands.Context):
        message = embed_template.copy()

        if ctx.author in self.users_in_queue:
            self.users_in_queue.remove(ctx.author)

            message.add_field(
                name='User Left the Queue!',
                value=f'{ctx.author.mention} left the queue.',
                inline=False
            )

            if len(self.users_in_queue) > 0:
                message.add_field(
                    name=f'Users in Queue: {str(len(self.users_in_queue))}',
                    value=', '.join(user.mention for user in self.users_in_queue),
                    inline=False
                )
            else:
                message.add_field(
                    name=f'Queue Empty!',
                    value='To restart the queue, type `;q` or `;queue`',
                    inline=False
                )

            await ctx.channel.send(embed=message)
        else:
            await ctx.channel.send(f'You are not in the queue, {ctx.author.mention}')


def setup(bot):
    bot.add_cog(Queue(bot))
