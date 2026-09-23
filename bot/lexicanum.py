# -*- coding: utf-8 -*-
"""Lexicanum — arşiv botu.
Komutlar: /ara /rastgele /istatistik (herkes) · /kayit-ekle /kayit-duzenle /index-yenile (manage_messages)
Çalıştırma: DISCORD_TOKEN=... python3 lexicanum.py"""
import json
import os
import random
import re
import unicodedata
from datetime import datetime, timezone

import discord
from discord import app_commands

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
TOKEN = os.environ['DISCORD_TOKEN']

GUILDS = json.load(open(os.path.join(DATA, 'guilds.json')))
LOG_CHANNELS = {}
if os.path.exists(os.path.join(DATA, 'log_channels.json')):
    LOG_CHANNELS = json.load(open(os.path.join(DATA, 'log_channels.json')))


def load_index():
    p = os.path.join(DATA, 'index.json')
    return json.load(open(p)) if os.path.exists(p) else []


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split())


INDEX = load_index()

intents = discord.Intents(guilds=True, members=True)
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def slug_of(gid):
    return GUILDS.get(str(gid), {}).get('slug')


def search(q, gid=None, limit=10):
    nq = norm(q)
    if not nq:
        return []
    toks = nq.split()
    scored = []
    for r in INDEX:
        if gid and str(r['g']) != str(gid):
            continue
        nt = norm(r['t'])
        if nt == nq:
            sc = 100
        elif nt.startswith(nq):
            sc = 80
        elif nq in nt:
            sc = 60
        else:
            inter = len(set(toks) & set(nt.split()))
            if not inter:
                continue
            sc = inter * 10 - abs(len(nt) - len(nq)) / 100
        scored.append((sc, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]


def result_embed(title, rows):
    e = discord.Embed(title=title, colour=0xC8A24B)
    e.description = '\n'.join(
        f'• [{r["t"]}]({r["l"]}) — *{r["f"]}* · {r["s"]}' for r in rows)
    return e


@tree.command(name='ara', description='Arşivde kayıt ara')
@app_commands.describe(sorgu='Aranacak kayıt adı', sunucu='Yalnızca bu sunucuda ara')
@app_commands.choices(sunucu=[app_commands.Choice(name=m['name'], value=s)
                            for m in GUILDS.values() for s in [m['slug']]])
async def ara(inter, sorgu: str, sunucu: app_commands.Choice[str] = None):
    gid = None
    if sunucu:
        gid = next(g for g, m in GUILDS.items() if m['slug'] == sunucu.value)
    rows = search(sorgu, gid)
    if not rows:
        await inter.response.send_message(f'**{sorgu}** için kayıt bulunamadı.', ephemeral=True)
        return
    await inter.response.send_message(embed=result_embed(f'“{sorgu}” — {len(rows)} sonuç', rows))


@tree.command(name='rastgele', description='Arşivden rastgele bir kayıt')
@app_commands.describe(sunucu='Yalnızca bu sunucudan')
@app_commands.choices(sunucu=[app_commands.Choice(name=m['name'], value=s)
                            for m in GUILDS.values() for s in [m['slug']]])
async def rastgele(inter, sunucu: app_commands.Choice[str] = None):
    pool = INDEX
    if sunucu:
        gid = next(g for g, m in GUILDS.items() if m['slug'] == sunucu.value)
        pool = [r for r in INDEX if str(r['g']) == str(gid)]
    elif inter.guild_id:
        pool = [r for r in INDEX if str(r['g']) == str(inter.guild_id)] or INDEX
    r = random.choice(pool)
    await inter.response.send_message(embed=result_embed('Rastgele kayıt', [r]))


@tree.command(name='istatistik', description='Arşiv istatistikleri')
async def istatistik(inter):
    e = discord.Embed(title='Lexicanum — Arşiv', colour=0xC8A24B)
    for gid, m in GUILDS.items():
        n = sum(1 for r in INDEX if str(r['g']) == gid)
        e.add_field(name=m['name'], value=f'{n} kayıt', inline=True)
    e.set_footer(text=f'Toplam {len(INDEX)} kayıt')
    await inter.response.send_message(embed=e)


def is_admin(inter):
    return inter.user.guild_permissions.manage_messages


async def forum_ac(inter, cur: str):
    g = inter.guild
    if not g:
        return []
    return [app_commands.Choice(name=c.name, value=str(c.id))
            for c in g.channels
            if isinstance(c, discord.ForumChannel) and cur.lower() in c.name.lower()][:25]


class KayitModal(discord.ui.Modal):
    def __init__(self, forum):
        super().__init__(title='Yeni kayıt')
        self.forum = forum
        self.isim = discord.ui.TextInput(label='Kayıt adı', max_length=100)
        self.govde = discord.ui.TextInput(
            label='Kayıt metni', style=discord.TextStyle.paragraph,
            placeholder='-# THE ... ARCHIVE · ... · Kayıt\n\n# İsim — ...\n\n...',
            max_length=4000)
        self.add_item(self.isim)
        self.add_item(self.govde)

    async def on_submit(self, inter):
        name = self.isim.value.strip()
        body = self.govde.value.strip()
        try:
            chunks = [body[i:i + 2000] for i in range(0, len(body), 2000)] or ['—']
            th = await self.forum.create_thread(name=name, content=chunks[0])
            for c in chunks[1:]:
                await th.send(c)
            await inter.response.send_message(
                f'Kayıt açıldı: {th.jump_url}', ephemeral=True)
            INDEX.append({'t': name, 'g': str(self.forum.guild.id),
                          'f': self.forum.name, 'c': '',
                          'l': f'https://discord.com/channels/{self.forum.guild.id}/{th.id}',
                          's': GUILDS.get(str(self.forum.guild.id), {}).get('name', '?')})
        except Exception as e:
            await inter.response.send_message(f'Hata: {e}', ephemeral=True)


@tree.command(name='kayit-ekle', description='Foruma yeni kayıt aç (yönetici)')
@app_commands.describe(forum='Kaydın açılacağı forum')
@app_commands.autocomplete(forum=forum_ac)
async def kayit_ekle(inter, forum: str):
    if not is_admin(inter):
        await inter.response.send_message('Yetkin yok.', ephemeral=True)
        return
    ch = inter.guild.get_channel(int(forum))
    if not isinstance(ch, discord.ForumChannel):
        await inter.response.send_message('Forum bulunamadı.', ephemeral=True)
        return
    await inter.response.send_modal(KayitModal(ch))


async def kayit_ac(inter, cur: str):
    g = inter.guild
    if not g:
        return []
    nq = norm(cur)
    rows = [r for r in INDEX if str(r['g']) == str(g.id)]
    if nq:
        rows = [r for r in rows if nq in norm(r['t'])]
    return [app_commands.Choice(name=r['t'][:100], value=r['l'].rsplit('/', 1)[1])
            for r in rows[:25]]


class DuzenleModal(discord.ui.Modal):
    def __init__(self, thread, msg_id, old):
        super().__init__(title='Kaydı düzenle')
        self.thread, self.msg_id = thread, msg_id
        self.govde = discord.ui.TextInput(
            label='Kayıt metni', style=discord.TextStyle.paragraph,
            default=old[:4000], max_length=4000)
        self.add_item(self.govde)

    async def on_submit(self, inter):
        body = self.govde.value.strip()
        try:
            await self.thread.edit(archived=False)
            msg = await self.thread.fetch_message(self.msg_id)
            first, rest = body[:2000], body[2000:].strip()
            await msg.edit(content=first)
            if rest:
                await self.thread.send(rest[:2000])
            await self.thread.edit(archived=True)
            await inter.response.send_message('Kayıt güncellendi.', ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f'Hata: {e}', ephemeral=True)


@tree.command(name='kayit-duzenle', description='Kayıt metnini düzenle (yönetici)')
@app_commands.describe(kayit='Düzenlenecek kayıt')
@app_commands.autocomplete(kayit=kayit_ac)
async def kayit_duzenle(inter, kayit: str):
    if not is_admin(inter):
        await inter.response.send_message('Yetkin yok.', ephemeral=True)
        return
    try:
        tid = int(kayit)
        th = await inter.guild.fetch_channel(tid)
        msg = await th.fetch_message(tid)
    except Exception as e:
        await inter.response.send_message(f'Kayıt bulunamadı: {e}', ephemeral=True)
        return
    old = msg.content
    if old.startswith('http'):
        old = old.split('\n', 1)[1] if '\n' in old else ''
    await inter.response.send_modal(DuzenleModal(th, tid, old))


@tree.command(name='index-yenile', description='Kayıt indeksini yeniden tara (yönetici)')
async def index_yenile(inter):
    if not is_admin(inter):
        await inter.response.send_message('Yetkin yok.', ephemeral=True)
        return
    await inter.response.send_message('İndeks taranıyor — birkaç dakika sürebilir…', ephemeral=True)
    import asyncio
    import build_index as bi

    def run():
        bi.TOKEN = TOKEN
        bi.H = {'Authorization': 'Bot ' + TOKEN, 'Content-Type': 'application/json'}
        bi.main()

    await asyncio.to_thread(run)
    global INDEX
    INDEX = load_index()
    await inter.followup.send(f'Bitti — {len(INDEX)} kayıt indekslendi.', ephemeral=True)


def log_embed(member, join):
    e = discord.Embed(
        title='Üye Katıldı' if join else 'Üye Ayrıldı',
        colour=0x2E8B57 if join else 0x8B2E2E,
        description=f'**{member.mention}** ({member.name})',
        timestamp=datetime.now(timezone.utc))
    e.set_thumbnail(url=member.display_avatar.url)
    g = bot.get_guild(member.guild.id)
    if g:
        e.set_footer(text=f'Üye sayısı: {g.member_count}')
    return e


@bot.event
async def on_member_join(m):
    cid = LOG_CHANNELS.get(str(m.guild.id))
    if cid:
        await bot.get_channel(int(cid)).send(embed=log_embed(m, True))


@bot.event
async def on_member_remove(m):
    cid = LOG_CHANNELS.get(str(m.guild.id))
    if cid:
        await bot.get_channel(int(cid)).send(embed=log_embed(m, False))


@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching,
                                  name='arşivi · /ara'))
    print(f'Lexicanum çevrimiçi — {bot.user} · {len(INDEX)} kayıt', flush=True)


bot.run(TOKEN)
