"""Lexicanum — arşiv botu.
Komutlar: /ara /sor /rastgele /istatistik (herkes) · /kayit-ekle /kayit-duzenle /index-yenile (manage_messages)
Çalıştırma: DISCORD_TOKEN=... python3 lexicanum.py"""
import asyncio
import logging
import os
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from rapidfuzz import fuzz, process

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from lib.jsonio import read_json, write_json_atomic
from lib.textnorm import norm

log = logging.getLogger('lexicanum')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
TOKEN = os.environ['DISCORD_TOKEN']

GUILDS = read_json(os.path.join(DATA, 'guilds.json'), default={})
LOG_CHANNELS = read_json(os.path.join(DATA, 'log_channels.json'), default={})


def load_index():
    rows = read_json(os.path.join(DATA, 'index.json'), default=[])
    for r in rows:
        # 'i': thread id (eski kayıtlarda yok — URL'den türet)
        # 'n': önceden-normalize başlık (search her sorguda yeniden hesaplamaz)
        r.setdefault('i', str(r.get('l', '')).rsplit('/', 1)[-1])
        r.setdefault('n', norm(r['t']))
    return rows


def save_index():
    write_json_atomic(os.path.join(DATA, 'index.json'), INDEX)


INDEX = load_index()
INDEX_LOCK = asyncio.Lock()

intents = discord.Intents(guilds=True, members=True)
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def slug_of(gid):
    return GUILDS.get(str(gid), {}).get('slug')


def search(q, gid=None, limit=10):
    """-> (ilk `limit` kayıt, toplam eşleşme sayısı)."""
    nq = norm(q)
    if not nq:
        return [], 0
    toks = nq.split()
    scored = []
    for r in INDEX:
        if gid and str(r['g']) != str(gid):
            continue
        nt = r.get('n') or norm(r['t'])
        if nt == nq:
            sc = 100
        elif nt.startswith(nq):
            sc = 80
        elif nq in nt:
            sc = 60
        else:
            inter = len(set(toks) & set(nt.split()))
            fz = fuzz.token_set_ratio(nq, nt)
            if inter:
                sc = inter * 10 - abs(len(nt) - len(nq)) / 100
            elif fz >= 75:
                sc = 20 + fz * 0.35
            else:
                continue
        scored.append((sc, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]], len(scored)


def suggest(nq, gid=None, limit=3):
    """0 sonuçta 'bunu mu demek istediniz?' — en yakın başlıklar."""
    cand = [r for r in INDEX if not gid or str(r['g']) == str(gid)]
    hits = process.extract(nq, [r.get('n') or norm(r['t']) for r in cand],
                           scorer=fuzz.token_set_ratio, limit=limit,
                           score_cutoff=60)
    return [cand[i] for _, _, i in hits]


def result_embed(title, rows):
    e = discord.Embed(title=title[:256], colour=0xC8A24B)

    def link(r):
        t = discord.utils.escape_markdown(r['t']).replace('[', '\\[').replace(']', '\\]')
        out = f'• [{t}]({r["l"]}) — *{r["f"]}*'
        if r.get('c'):
            out += f' · {r["c"]}'
        return out + f' · {r["s"]}'
    e.description = '\n'.join(link(r) for r in rows)
    return e


@tree.command(name='ara', description='Arşivde kayıt ara')
@app_commands.describe(sorgu='Aranacak kayıt adı', sunucu='Yalnızca bu sunucuda ara')
@app_commands.choices(sunucu=[app_commands.Choice(name=m['name'], value=s)
                            for m in GUILDS.values() for s in [m['slug']]])
async def ara(inter, sorgu: str, sunucu: app_commands.Choice[str] = None):
    gid = None
    if sunucu:
        gid = next(g for g, m in GUILDS.items() if m['slug'] == sunucu.value)
    rows, total = search(sorgu, gid)
    if not rows:
        msg = f'**{sorgu[:100]}** için kayıt bulunamadı.'
        hits = suggest(norm(sorgu), gid)
        if hits:
            msg += '\nBunu mu demek istediniz?\n' + '\n'.join(
                f'• [{r["t"][:80]}]({r["l"]})' for r in hits)
        await inter.response.send_message(msg, ephemeral=True)
        return
    await inter.response.send_message(
        embed=result_embed(f'“{sorgu[:200]}” — {len(rows)}/{total} sonuç', rows))


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
    if not pool:
        await inter.response.send_message('İndeks boş.', ephemeral=True)
        return
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


# /sor — soru kelimelerinden en iyi paragrafı çıkarır (LLM yok, saf puanlama)
_STOP = {'bir', 've', 'ya', 'veya', 'ile', 'icin', 'gibi', 'de', 'da', 'ki',
         'ne', 'bu', 'su', 'o', 'nasil', 'neden', 'nicin', 'nedir', 'kim',
         'kimdir', 'kac', 'hangi', 'hangisi', 'mi', 'mu', 'var', 'yok', 'en',
         'cok', 'az', 'diye', 'kadar', 'hakkinda', 'konusunda', 'nerede',
         'kimse', 'sey', 'olan', 'olur', 'olarak', 'arasinda'}


def question_terms(q):
    return {t for t in norm(q).split() if t not in _STOP and len(t) > 2}


def thread_id_of(r):
    return r.get('i') or str(r.get('l', '')).rsplit('/', 1)[-1]


_FTS_DB = os.path.join(DATA, 'lexicanum.db')


def fts_search(terms, gid=None, limit=3):
    """data/lexicanum.db varsa gövde FTS5 araması -> [(r, orig)]; yoksa []."""
    if not os.path.exists(_FTS_DB) or not terms:
        return []
    from lib.ftsdb import connect
    from lib.ftsdb import search as fts_q
    slug = GUILDS.get(str(gid), {}).get('slug') if gid else None
    db = connect(_FTS_DB)
    try:
        rows = fts_q(db, list(terms), server=slug, limit=limit)
    finally:
        db.close()
    sname = {m['slug']: m['name'] for m in GUILDS.values()}
    return [{'t': d, 'l': u, 'f': f, 's': sname.get(s, s), '_orig': o}
            for d, u, f, s, o in rows]


async def thread_text(r):
    try:
        th = await bot.fetch_channel(int(thread_id_of(r)))
    except (discord.HTTPException, ValueError):
        return ''
    if not hasattr(th, 'history'):
        return ''
    return '\n\n'.join(m.content async for m in th.history(limit=None, oldest_first=True))


def best_excerpt(text, terms, limit=1500):
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    paras = [p for p in paras if not p.startswith(('#', '-#', '---', '!['))]
    if not paras:
        return ''

    def score(i, p):
        words = norm(p).split()
        if not words:
            return -i * 0.01
        hits = sum(1 for t in terms if t in words)
        cov = hits / len(terms) if terms else 0.0
        return cov * 10 + hits / len(words) - i * 0.01

    out = paras[max(range(len(paras)), key=lambda i: score(i, paras[i]))]
    if len(out) > limit:
        out = out[:out.rfind(' ', 0, limit)].rstrip() + '…'
    return out


@tree.command(name='sor', description='Arşive soru sor (örn: astartes nedir)')
@app_commands.describe(soru='Sorunuz', sunucu='Yalnızca bu sunucuda ara')
@app_commands.choices(sunucu=[app_commands.Choice(name=m['name'], value=s)
                            for m in GUILDS.values() for s in [m['slug']]])
async def sor(inter, soru: str, sunucu: app_commands.Choice[str] = None):
    gid = None
    if sunucu:
        gid = next(g for g, m in GUILDS.items() if m['slug'] == sunucu.value)
    elif inter.guild_id:
        gid = str(inter.guild_id)
    await inter.response.defer()
    terms = question_terms(soru)
    slug = GUILDS.get(str(gid), {}).get('slug') if gid else None
    for r in fts_search(terms, slug):
        ex = best_excerpt(r.pop('_orig'), terms)
        if ex:
            await inter.followup.send(embed=sor_embed(soru, r, ex))
            return
    q = ' '.join(sorted(terms)) or soru
    rows, _ = search(q, gid)
    if not rows and gid:
        rows, _ = search(q, None)
    if not rows:
        msg = f'**{soru[:100]}** için kayıt bulunamadı.'
        hits = suggest(norm(soru), gid)
        if hits:
            msg += '\nBunu mu demek istediniz?\n' + '\n'.join(
                f'• [{r["t"][:80]}]({r["l"]})' for r in hits)
        await inter.followup.send(msg, ephemeral=True)
        return
    for r in rows[:3]:
        ex = best_excerpt(await thread_text(r), terms)
        if ex:
            await inter.followup.send(embed=sor_embed(soru, r, ex))
            return
    await inter.followup.send(embed=result_embed(f'“{soru[:200]}”', rows[:3]))


def sor_embed(soru, r, ex):
    e = discord.Embed(title=f'“{soru[:200]}”', colour=0xC8A24B,
                      description=ex[:4096])
    src = f'[{r["t"][:80]}]({r["l"]})' if r.get('l') else r['t'][:80]
    e.add_field(name='Kaynak', inline=False,
                value=f'{src} — {r["f"]} · {r["s"]}')
    return e


def is_admin(inter):
    return (isinstance(inter.user, discord.Member)
            and inter.user.guild_permissions.manage_messages)


async def forum_ac(inter, cur: str):
    g = inter.guild
    if not g:
        return []
    try:
        chans = await g.fetch_channels()
    except discord.HTTPException:
        chans = g.channels
    return [app_commands.Choice(name=c.name, value=str(c.id))
            for c in chans
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
        if not name:
            await inter.response.send_message('Kayıt adı boş olamaz.', ephemeral=True)
            return
        try:
            chunks = [body[i:i + 2000] for i in range(0, len(body), 2000)] or ['—']
            th = await self.forum.create_thread(name=name, content=chunks[0])
            for c in chunks[1:]:
                await th.send(c)
            # on_thread_create event'iyle yarışır — upsert dedupe'ları;
            # event kaybolsa bile indeks kalıcı (kilit + diske yazma).
            async with INDEX_LOCK:
                await upsert_thread(th)
                save_index()
            await inter.response.send_message(
                f'Kayıt açıldı: {th.jump_url}', ephemeral=True)
        except discord.Forbidden:
            await inter.response.send_message('İzin hatası — forumda yazma yetkim yok.', ephemeral=True)
        except discord.HTTPException as e:
            await inter.response.send_message(f'Discord hatası: {e.status}', ephemeral=True)
        except Exception:
            log.exception('kayit-ekle hatası')
            await inter.response.send_message('Beklenmedik hata — loga bak.', ephemeral=True)


@tree.command(name='kayit-ekle', description='Foruma yeni kayıt aç (yönetici)')
@app_commands.guild_only()
@app_commands.describe(forum='Kaydın açılacağı forum')
@app_commands.autocomplete(forum=forum_ac)
async def kayit_ekle(inter, forum: str):
    if not is_admin(inter):
        await inter.response.send_message('Yetkin yok.', ephemeral=True)
        return
    try:
        ch = await inter.guild.fetch_channel(int(forum))
    except (discord.NotFound, discord.HTTPException, ValueError):
        ch = None
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
        rows = [r for r in rows if nq in (r.get('n') or norm(r['t']))]
    return [app_commands.Choice(
                name=r['t'][:100],
                value=r.get('i') or str(r.get('l', '')).rsplit('/', 1)[-1])
            for r in rows[:25]]


def join_body(contents):
    """Thread mesaj içeriklerini tek metne birleştirir.

    Modal'dan açılan kayıtlar 2000'de sert bölünür → ayraçsız birleştirme;
    build_server `chunks()` paragraf sınırından (≤1950) böler → '\\n\\n'.
    """
    if len(contents) > 1 and all(len(c) == 2000 for c in contents[:-1]):
        return ''.join(contents)
    return '\n\n'.join(contents)


def split_for_modal(old, limit=4000):
    """Modal gövdesi için (gösterilen, korunan-tail) çifti üretir.
    Kesim paragraf sınırında yapılır — orta-kelime yapışması önlenir."""
    if len(old) <= limit:
        return old, ''
    cut = old.rfind('\n\n', 0, limit)
    if cut < limit // 4:
        cut = old.rfind('\n', 0, limit)
    if cut < 1:
        cut = limit
    return old[:cut], old[cut:]


class DuzenleModal(discord.ui.Modal):
    def __init__(self, thread, shown, tail=''):
        super().__init__(title='Kaydı düzenle')
        self.thread, self.tail = thread, tail
        label = 'Kayıt metni' if not tail else f'Kayıt metni — ilk {len(shown)} kr.'
        self.govde = discord.ui.TextInput(
            label=label, style=discord.TextStyle.paragraph,
            default=shown, max_length=4000)
        self.add_item(self.govde)

    async def on_submit(self, inter):
        # tail zaten kendi başındaki ayıracı taşır; rstrip('\n') kullanıcının
        # gövde sonuna eklediği boş satırları tail'le çakışmadan temizler.
        body = self.govde.value.rstrip('\n') + self.tail
        try:
            await self.thread.edit(archived=False)
            msgs = [m async for m in self.thread.history(limit=None, oldest_first=True)]
            own = [m for m in msgs if m.author.id == bot.user.id]
            foreign = len(msgs) - len(own)
            if not own:
                await inter.response.send_message(
                    "Bu thread'de düzenleyebileceğim mesaj yok.", ephemeral=True)
                return
            chunks = [body[i:i + 2000] for i in range(0, len(body), 2000)] or ['—']
            await own[0].edit(content=chunks[0])
            for i, c in enumerate(chunks[1:], 1):
                if i < len(own):
                    await own[i].edit(content=c)
                else:
                    await self.thread.send(c)
            for m in own[len(chunks):]:
                await m.delete()
            await self.thread.edit(archived=self.was_archived)
            note = f' ({foreign} yabancı mesaj korundu)' if foreign else ''
            await inter.response.send_message(f'Kayıt güncellendi.{note}', ephemeral=True)
        except discord.Forbidden:
            await inter.response.send_message('İzin hatası — thread düzenleyemiyorum.', ephemeral=True)
        except discord.NotFound:
            await inter.response.send_message('Kayıt mesajı bulunamadı.', ephemeral=True)
        except discord.HTTPException as e:
            await inter.response.send_message(f'Discord hatası: {e.status}', ephemeral=True)
        except Exception:
            log.exception('kayit-duzenle hatası')
            await inter.response.send_message('Beklenmedik hata — loga bak.', ephemeral=True)


@tree.command(name='kayit-duzenle', description='Kayıt metnini düzenle (yönetici)')
@app_commands.guild_only()
@app_commands.describe(kayit='Düzenlenecek kayıt')
@app_commands.autocomplete(kayit=kayit_ac)
async def kayit_duzenle(inter, kayit: str):
    if not is_admin(inter):
        await inter.response.send_message('Yetkin yok.', ephemeral=True)
        return
    try:
        tid = int(kayit)
        th = await inter.guild.fetch_channel(tid)
    except (discord.NotFound, ValueError):
        await inter.response.send_message('Kayıt bulunamadı.', ephemeral=True)
        return
    except discord.HTTPException as e:
        await inter.response.send_message(f'Discord hatası: {e.status}', ephemeral=True)
        return
    if not isinstance(th, discord.Thread):
        await inter.response.send_message('Bu kanal bir forum kaydı değil.', ephemeral=True)
        return
    msgs = [m async for m in th.history(limit=None, oldest_first=True)]
    own = [m for m in msgs if m.author.id == bot.user.id]
    if not own:
        await inter.response.send_message(
            "Bu thread'de düzenleyebileceğim mesaj yok.", ephemeral=True)
        return
    old = join_body(m.content for m in own)
    shown, tail = split_for_modal(old)
    modal = DuzenleModal(th, shown, tail=tail)
    modal.was_archived = bool(th.archived)
    await inter.response.send_modal(modal)


@tree.command(name='index-yenile', description='Kayıt indeksini yeniden tara (yönetici)')
@app_commands.guild_only()
async def index_yenile(inter):
    if not is_admin(inter):
        await inter.response.send_message('Yetkin yok.', ephemeral=True)
        return
    await inter.response.send_message('İndeks taranıyor — birkaç dakika sürebilir…', ephemeral=True)
    if INDEX_LOCK.locked():
        await inter.followup.send('Zaten bir indeksleme sürüyor.', ephemeral=True)
        return
    import build_index as bi

    def run():
        bi.TOKEN = TOKEN
        bi.H = {'Authorization': 'Bot ' + TOKEN, 'Content-Type': 'application/json'}
        bi.main()

    async with INDEX_LOCK:
        try:
            await asyncio.to_thread(run)
        except Exception:
            log.exception('index-yenile hatası')
            await inter.followup.send('İndeksleme hata verdi — loga bak.', ephemeral=True)
            return
        INDEX[:] = load_index()
    log.info('İndeks yenilendi: %d kayıt', len(INDEX))
    # followup token'ı 15 dk yaşar — uzun taramalarda süre dolmuş olabilir;
    # o durumda sonucu kanala düş (kayıt kalıcı olsun).
    done = f'İndeksleme bitti — {len(INDEX)} kayıt indekslendi.'
    try:
        await inter.followup.send(done, ephemeral=True)
    except discord.HTTPException:
        if inter.channel:
            await inter.channel.send(f'{inter.user.mention} {done}')


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


async def forum_of(th):
    """Parent forum kanalı — önbellekte yoksa API'den çek."""
    ch = bot.get_channel(th.parent_id)
    if ch is None:
        try:
            ch = await bot.fetch_channel(th.parent_id)
        except discord.HTTPException:
            ch = None
    return ch


async def rec_of_thread(th):
    g = th.guild
    forum = await forum_of(th)
    cat = ''
    if forum is not None and forum.category_id:
        cch = bot.get_channel(forum.category_id)
        if cch is None:
            try:
                cch = await bot.fetch_channel(forum.category_id)
            except discord.HTTPException:
                cch = None
        cat = cch.name if cch else ''
    return {'t': th.name, 'g': str(g.id), 'i': str(th.id),
            'f': forum.name if forum else '', 'c': cat,
            'l': f'https://discord.com/channels/{g.id}/{th.id}',
            's': GUILDS.get(str(g.id), {}).get('name', '?'),
            'n': norm(th.name)}


async def upsert_thread(th):
    tid = str(th.id)
    rec = await rec_of_thread(th)
    for i, r in enumerate(INDEX):
        if (r.get('i') or str(r.get('l', '')).rsplit('/', 1)[-1]) == tid:
            INDEX[i] = rec
            return
    INDEX.append(rec)


async def forum_thread_in_scope(th):
    if str(th.guild.id) not in GUILDS:
        return False
    parent = await forum_of(th)
    return isinstance(parent, discord.ForumChannel)


@bot.event
async def on_thread_create(th):
    if not await forum_thread_in_scope(th):
        return
    async with INDEX_LOCK:
        await upsert_thread(th)
        save_index()
    log.info('Index +%s (%s)', th.name, th.id)


@bot.event
async def on_thread_update(before, after):
    if not await forum_thread_in_scope(after) or before.name == after.name:
        return
    async with INDEX_LOCK:
        await upsert_thread(after)
        save_index()
    log.info('Index ~%s (%s)', after.name, after.id)


@bot.event
async def on_thread_delete(th):
    if str(th.guild.id) not in GUILDS:
        return
    tid = str(th.id)
    async with INDEX_LOCK:
        before_n = len(INDEX)
        INDEX[:] = [r for r in INDEX
                    if (r.get('i') or str(r.get('l', '')).rsplit('/', 1)[-1]) != tid]
        if len(INDEX) != before_n:
            save_index()
            log.info('Index -%s (%s)', th.name, th.id)


async def member_log(m, join):
    cid = LOG_CHANNELS.get(str(m.guild.id))
    if not cid:
        return
    ch = bot.get_channel(int(cid))
    if ch is None:
        log.warning('Log kanalı bulunamadı: %s', cid)
        return
    await ch.send(embed=log_embed(m, join))


@bot.event
async def on_member_join(m):
    await member_log(m, True)


@bot.event
async def on_member_remove(m):
    await member_log(m, False)


@tree.error
async def on_app_error(inter, error):
    log.exception('Komut hatası (%s)', getattr(inter.command, 'name', '?'),
                  exc_info=error)
    msg = 'Beklenmedik bir hata oluştu.'
    try:
        if inter.response.is_done():
            await inter.followup.send(msg, ephemeral=True)
        else:
            await inter.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass


_TREE_SYNCED = False


@bot.event
async def on_ready():
    global _TREE_SYNCED
    if not _TREE_SYNCED:
        await tree.sync()
        _TREE_SYNCED = True
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching,
                                  name='arşivi · /ara'))
    log.info('Lexicanum çevrimiçi — %s · %d kayıt', bot.user, len(INDEX))


if __name__ == '__main__':
    bot.run(TOKEN)
