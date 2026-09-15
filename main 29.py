import asyncio,logging,os,random
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from aiohttp import web
from aiogram import Bot,Dispatcher,Router,F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart,Command
from aiogram.types import Message,CallbackQuery,InlineKeyboardButton,InlineKeyboardMarkup,ChatJoinRequest
from sqlalchemy import String,Integer,BigInteger,Boolean,DateTime,Text,Numeric,select,func,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
logging.basicConfig(level=logging.INFO)
logging.warning("STARTING BOT BUILD: BIGINT-FIX-2026-09-04")
from config import BOT_TOKEN, ADMIN_IDS, DATABASE_URL
TOKEN=BOT_TOKEN; DB=DATABASE_URL; SUPER=set(ADMIN_IDS)
if DB.startswith("postgres://"):
    DB = "postgresql+asyncpg://" + DB[len("postgres://"):]
elif DB.startswith("postgresql://"):
    DB = "postgresql+asyncpg://" + DB[len("postgresql://"):]
if not DB.startswith("postgresql+asyncpg://"):
    raise RuntimeError("DATABASE_URL must be a PostgreSQL URL, not an https URL.")
eng=create_async_engine(DB,pool_pre_ping=True);S=async_sessionmaker(eng,expire_on_commit=False);r=Router()
PERMS={"superadmin":{"all"},"finance":{"payout","balance"},"support":{"ticket"},"moderator":{"user"},"content":{"content"}}
class B(DeclarativeBase):pass
class User(B):
 __tablename__="users";id:Mapped[int]=mapped_column(BigInteger,primary_key=True);username:Mapped[str|None]=mapped_column(String(64),nullable=True);referrer_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True);balance:Mapped[Decimal]=mapped_column(Numeric(12,2),default=0);captcha_ok:Mapped[bool]=mapped_column(Boolean,default=False);verified:Mapped[bool]=mapped_column(Boolean,default=False);blocked:Mapped[bool]=mapped_column(Boolean,default=False);ban_reason:Mapped[str|None]=mapped_column(String(500),nullable=True);is_worker:Mapped[bool]=mapped_column(Boolean,default=False);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Admin(B):__tablename__="admins";user_id:Mapped[int]=mapped_column(BigInteger,primary_key=True);role:Mapped[str]=mapped_column(String(20))
class Reward(B):__tablename__="rewards";id:Mapped[int]=mapped_column(Integer,primary_key=True);referrer_id:Mapped[int]=mapped_column(BigInteger);referral_id:Mapped[int]=mapped_column(BigInteger,unique=True);amount:Mapped[Decimal]=mapped_column(Numeric(12,2));status:Mapped[str]=mapped_column(String(20));hold_until:Mapped[datetime]=mapped_column(DateTime(timezone=True));last_ok:Mapped[bool]=mapped_column(Boolean,default=True)
class Ledger(B):__tablename__="ledger";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(BigInteger);amount:Mapped[Decimal]=mapped_column(Numeric(12,2));kind:Mapped[str]=mapped_column(String(40));description:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Withdrawal(B):__tablename__="withdrawals";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(BigInteger);amount:Mapped[Decimal]=mapped_column(Numeric(12,2));method:Mapped[str]=mapped_column(String(40));destination:Mapped[str]=mapped_column(Text);status:Mapped[str]=mapped_column(String(20),default="pending");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Ticket(B):__tablename__="tickets";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(BigInteger);status:Mapped[str]=mapped_column(String(20),default="open");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class TM(B):__tablename__="ticket_messages";id:Mapped[int]=mapped_column(Integer,primary_key=True);ticket_id:Mapped[int]=mapped_column(Integer);sender_id:Mapped[int]=mapped_column(BigInteger);text:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Setting(B):__tablename__="settings";key:Mapped[str]=mapped_column(String(100),primary_key=True);value:Mapped[str]=mapped_column(Text)
class JoinRequest(B):
 __tablename__="join_requests";user_id:Mapped[int]=mapped_column(BigInteger,primary_key=True);channel_key:Mapped[str]=mapped_column(String(50),primary_key=True);requested_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc));active:Mapped[bool]=mapped_column(Boolean,default=True)
class Media(B):__tablename__="media";key:Mapped[str]=mapped_column(String(100),primary_key=True);file_id:Mapped[str]=mapped_column(String(255))
class State(B):__tablename__="states";user_id:Mapped[int]=mapped_column(BigInteger,primary_key=True);action:Mapped[str]=mapped_column(String(50),default="");data:Mapped[str]=mapped_column(Text,default="")
class Notice(B):
 __tablename__="notices";id:Mapped[int]=mapped_column(Integer,primary_key=True);position:Mapped[int]=mapped_column(Integer,default=0);text:Mapped[str]=mapped_column(Text);enabled:Mapped[bool]=mapped_column(Boolean,default=True)
async def public_url(s): return await st(s,"public_url","")
async def private_url_1(s): return await st(s,"private_url_1",await st(s,"private_url",""))
async def private_url_2(s): return await st(s,"private_url_2","")
async def public_channel(s): return await st(s,"public_channel","")

async def join_kb(s):
 pu=await public_url(s); pr1=await private_url_1(s); pr2=await private_url_2(s)
 rows=[]
 if pu: rows.append([("📢 Канал",pu)])
 if pr1: rows.append([("🔒 Канал",pr1)])
 if pr2: rows.append([("🔒 Канал",pr2)])
 rows.append([("✅ Проверить подписку","check")])
 return kb(*rows)

def kb(*rows):
    keyboard = []
    for row in rows:
        buttons = []
        # Accept both [(text, data), ...] and ["🔙 Админ-панель","a:admin"]
        if len(row) == 2 and all(isinstance(v, str) for v in row):
            row = [tuple(row)]
        for x, y in row:
            if isinstance(y, str) and y.startswith(("http://", "https://", "tg://")):
                buttons.append(InlineKeyboardButton(text=x, url=y))
            else:
                buttons.append(InlineKeyboardButton(text=x, callback_data=y))
        keyboard.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def replace_message(c: CallbackQuery, text: str, **kwargs):
    try:
        await c.answer()
    except Exception:
        pass
    chat_id = c.message.chat.id
    try:
        await c.message.delete()
    except Exception:
        pass
    return await c.bot.send_message(chat_id, text, **kwargs)

async def send_screen(c: CallbackQuery, text: str, media_key: str | None = None, **kwargs):
    try:
        await c.answer()
    except Exception:
        pass
    try:
        await c.message.delete()
    except Exception:
        pass
    if media_key:
        async with S() as s:
            pic = await s.get(Media, "photo:" + media_key)
        if pic:
            return await c.bot.send_photo(c.message.chat.id, pic.file_id, caption=text, **kwargs)
    return await c.bot.send_message(c.message.chat.id, text, **kwargs)

async def st(s,k,d=""):
    x=await s.get(Setting,k);return x.value if x else d

async def setst(s,k,v):
    x=await s.get(Setting,k)
    if x:x.value=v
    else:s.add(Setting(key=k,value=v))

async def state(s,u,a=None,d=None):
    x=await s.get(State,u)
    if not x:x=State(user_id=u);s.add(x)
    if a is not None:x.action=a;x.data=d or ""
    return x

async def ledger(s,u,a,k,d):
    s.add(Ledger(user_id=u,amount=a,kind=k,description=d))

async def role(uid,p):
    if uid in SUPER:return True
    async with S() as s:
        x=await s.get(Admin,uid)
        return bool(x and (p in PERMS.get(x.role,set()) or "all" in PERMS.get(x.role,set())))

async def do_broadcast(bot,admin_id,ids,text_to_send):
    ok=0;fail=0
    for uid in ids:
        try:
            await bot.send_message(uid,text_to_send);ok+=1
        except Exception:
            fail+=1
        await asyncio.sleep(0.04)
    try:await bot.send_message(admin_id,f"📢 Рассылка завершена.\nУспешно: {ok}\nОшибок: {fail}")
    except Exception:pass

async def channel_member(bot, channel, uid):
    if not channel:return False
    try:
        member=await bot.get_chat_member(channel,uid)
        return member.status not in ("left","kicked")
    except Exception:
        return False

async def channel_request_exists(s, uid, key):
    x=await s.get(JoinRequest, {"user_id":uid,"channel_key":key})
    return bool(x and x.active)

async def required_channels_ok(bot, uid):
    # Проверяем частный канал №1: засчитывается поданная заявка,
    # либо уже принятое членство, либо админ/создатель канала.
    async with S() as s:
        p1 = await st(s, "private_channel_1", "")
        has_request = await channel_request_exists(s, uid, "private1")
    if not p1:
        return True
    if has_request:
        return True
    try:
        member = await bot.get_chat_member(p1, uid)
        if member.status in ("member", "administrator", "creator"):
            return True
    except Exception:
        pass
    return False

BOT_OPEN_ALLOWED_DATA={"home","bal","refs","wd"}
async def access(c,bot):
    async with S() as s:u=await s.get(User,c.from_user.id)
    if not u or u.blocked or not u.captcha_ok or not await required_channels_ok(bot,c.from_user.id):
        async with S() as s: markup=await join_kb(s)
        await replace_message(c, "⚠️ Нет доступа.\n\nПодпишитесь на канал и подайте заявку на вступление, затем нажмите «✅ Проверить подписку».", reply_markup=markup)
        return False
    if not (u.is_worker or c.from_user.id in SUPER):
        async with S() as s: thanks=await st(s,"text:thanks","🎉 Спасибо за подписку!")
        await replace_message(c, thanks)
        return False
    async with S() as s: closed = (await st(s,"bot_status","open"))=="closed"
    if closed:
        data=c.data or ""
        if data not in BOT_OPEN_ALLOWED_DATA and not data.startswith("wd:") and not data.startswith("wdbank:"):
            await c.answer("🛑 Бот временно приостановлен администрацией.\nДоступны только: Баланс, Мой трафик, Выплаты.",show_alert=True)
            return False
    return True

async def menu(target):
    async with S() as s:
        title = await st(s, "text:menu", "🏠 <b>Главное меню</b>")
        pic = await s.get(Media, "photo:menu")
        payout_url = await st(s,"payout_url","")
        closed = (await st(s,"bot_status","open"))=="closed"
    if closed:
        title = "🛑 <b>Бот временно приостановлен</b>\n\n"+title
        markup = kb([("💰 Баланс","bal"),("📊 Мой трафик","refs")],
                    [("💸 Выплаты",payout_url or "wd")])
    else:
        markup = kb([("💰 Баланс","bal"),("📊 Мой трафик","refs")],
                    [("🔗 Моя ссылка","link"),("💸 Выплаты",payout_url or "wd")],
                    [("🆘 Поддержка","sup"),("ℹ️ Информация","info")],
                    [("❓ FAQ","faq")])
    if isinstance(target, CallbackQuery):
        return await send_screen(target, title, "menu", reply_markup=markup)
    if pic:
        return await target.answer_photo(pic.file_id, caption=title, reply_markup=markup)
    return await target.answer(title, reply_markup=markup)

@r.message(CommandStart())
async def start(m:Message,bot:Bot):
 p=m.text.split();ref=int(p[1][4:]) if len(p)>1 and p[1].startswith("ref_") and p[1][4:].isdigit() else None
 async with S() as s:
  u=await s.get(User,m.from_user.id)
  if u is None and (await st(s,"bot_status","open"))=="closed":
   await m.answer("🛑 Бот временно приостановил свою работу. Пожалуйста, зайдите позже.")
   return
  if not u:s.add(User(id=m.from_user.id,username=m.from_user.username,referrer_id=ref if ref!=m.from_user.id else None));await s.commit();u=await s.get(User,m.from_user.id)
  if u.blocked:await m.answer("⛔ Доступ заблокирован.");return
  is_worker=u.is_worker or m.from_user.id in SUPER
  worker_ready=u.captcha_ok and await required_channels_ok(bot,u.id)
 if not is_worker:
  if await required_channels_ok(bot,m.from_user.id):
   async with S() as s: thanks=await st(s,"text:thanks","🎉 <b>Спасибо за подписку!</b>\n\nХорошего дня!")
   await m.answer(thanks)
  else:
   async with S() as s: markup=await join_kb(s)
   await m.answer("👋 <b>Добро пожаловать!</b>\n\nЧтобы продолжить, подпишитесь на наши каналы, а затем нажмите «✅ Я подписался».", reply_markup=markup)
  return
 if worker_ready:
  async with S() as s:u=await s.get(User,m.from_user.id);u.verified=True;await s.commit()
  await menu(m);return
 word,ok,other=random.choice([("солнце","☀️",["🌙","🍎"]),("яблоко","🍎",["🐟","🚗"]),("рыба","🐟",["🌳","⭐"])])
 z=[ok,*other];random.shuffle(z);await m.answer(f"🧩 Выберите эмодзи для слова <b>{word}</b>",reply_markup=kb(*[[(x,f"cap:{ok}:{x}") for x in z]]))
@r.callback_query(F.data.startswith("cap:"))
async def cap(c:CallbackQuery):
 _,ok,x=c.data.split(":")
 if x!=ok:await c.answer("Неверно.",show_alert=True);return
 async with S() as s:u=await s.get(User,c.from_user.id);u.captcha_ok=True;await s.commit()
 async with S() as s:
  markup = await join_kb(s)
 await replace_message(c, "Подпишитесь на каналы и затем нажмите «Я подписался».", reply_markup=markup)
@r.callback_query(F.data=="check")
async def check(c:CallbackQuery,bot:Bot):
    if not await required_channels_ok(bot,c.from_user.id):
        await c.answer("Вы ещё не подписались на все каналы.",show_alert=True)
        return
    async with S() as s:
        u=await s.get(User,c.from_user.id)
        first=not u.verified
        u.verified=True
        if first and u.referrer_id and await s.get(User,u.referrer_id):
            existing=await s.scalar(select(Reward).where(Reward.referral_id==u.id))
            if not existing:
                s.add(Reward(referrer_id=u.referrer_id,referral_id=u.id,amount=50,status="hold",
                             hold_until=datetime.now(timezone.utc)+timedelta(hours=30)))
            elif existing.status=="cancelled":
                existing.status="hold";existing.hold_until=datetime.now(timezone.utc)+timedelta(hours=30)
                existing.last_ok=True
        is_worker=u.is_worker or c.from_user.id in SUPER
        await s.commit()
    if not is_worker:
        async with S() as s: thanks=await st(s,"text:thanks","🎉 <b>Спасибо за подписку!</b>\n\nХорошего дня!")
        await replace_message(c, thanks)
        return
    async with S() as s:
        n=await s.scalar(select(Notice).where(Notice.enabled==True).order_by(Notice.position,Notice.id))
        if n:
            await state(s,c.from_user.id,"notice",str(n.position));await s.commit()
            await replace_message(c, n.text,reply_markup=kb([("➡️ Дальше","notice_next")]))
            return
    await menu(c)

@r.chat_join_request()
async def join_request(req:ChatJoinRequest):
    # Заявка учитывается только для обязательного частного канала №1.
    # Частный канал №2 бот не проверяет, поскольку доступа к нему нет.
    async with S() as s:
        p1=await st(s,"private_channel_1","")
        key="private1" if str(req.chat.id)==str(p1) else None
        if key:
            x=await s.get(JoinRequest, {"user_id":req.from_user.id,"channel_key":key})
            if x:
                x.active=True;x.requested_at=datetime.now(timezone.utc)
            else:
                s.add(JoinRequest(user_id=req.from_user.id,channel_key=key,active=True))
            await s.commit()

@r.callback_query(F.data=="notice_next")
async def notice_next(c:CallbackQuery):
 async with S() as s:
  x=await s.get(State,c.from_user.id); pos=int(x.data or "0")
  nxt=await s.scalar(select(Notice).where(Notice.enabled==True,Notice.position>pos).order_by(Notice.position,Notice.id))
  if nxt:
   await state(s,c.from_user.id,"notice",str(nxt.position));await s.commit()
   await c.answer("⚠️ Внимательно ознакомьтесь: это очень важно!",show_alert=True)
   await replace_message(c, nxt.text,reply_markup=kb([("➡️ Дальше","notice_next")]))
   return
  await state(s,c.from_user.id,"","");await s.commit()
 await c.answer("⚠️ Внимательно ознакомьтесь: это очень важно!",show_alert=True)
 await menu(c)

@r.callback_query(F.data=="home")
async def home(c:CallbackQuery): await menu(c)

@r.callback_query(F.data=="bal")
async def bal(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:
  u=await s.get(User,c.from_user.id);h=await s.scalar(select(func.coalesce(func.sum(Reward.amount),0)).where(Reward.referrer_id==u.id,Reward.status=="hold"))
 await send_screen(c, f"💰 Баланс: <b>{u.balance} ₽</b>\nВ холде: <b>{h} ₽</b>", media_key="bal", reply_markup=kb([("💸 Вывести","wd")],[("⬅️ Назад","home")]))
@r.callback_query(F.data=="refs")
async def refs(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:
  rows=(await s.scalars(select(User).where(User.referrer_id==c.from_user.id).order_by(User.created_at.desc()))).all()
 names="\n".join(f"• @{x.username}" if x.username else f"• ID: {x.id}" for x in rows) or "Нет рефералов."
 await send_screen(c, f"📊 Мой трафик: {len(rows)}\n\n{names}", media_key="refs", reply_markup=kb([("⬅️ Назад","home")]))
@r.callback_query(F.data=="link")
async def link(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 me=await bot.get_me();await send_screen(c, f"Ваша ссылка для приглашения:\nhttps://t.me/{me.username}?start=ref_{c.from_user.id}", media_key="link", reply_markup=kb([("⬅️ Назад","home")]))
FEES={"card":Decimal(45),"sbp":Decimal(0)}
METHOD_LABELS={"card":"💳 Карта","sbp":"📱 СБП"}
SBP_BANKS=[("sber","Сбербанк"),("tbank","Т-Банк"),("vtb","ВТБ"),("alfa","Альфа-Банк"),("gazprom","Газпромбанк"),("raif","Райффайзен"),("ozon","Озон Банк"),("other","Другой (ввести вручную)")]
def bank_kb():
 rows=[[(name,f"wdbank:{code}")] for code,name in SBP_BANKS]
 return kb(*rows)
@r.callback_query(F.data=="wd")
async def wd(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:
  manual=await st(s,"payout_manual","open")
 if manual=="closed":await c.answer("💸 Выплаты временно приостановлены администратором. Попробуйте позже.",show_alert=True);return
 await replace_message(c, "Выберите способ вывода:\n\n💳 Карта — комиссия 45 ₽\n📱 СБП (по номеру телефона) — без комиссии\n\nМинимальная сумма вывода — 100 ₽.",reply_markup=kb([("💳 Карта","wd:card"),("📱 СБП","wd:sbp")]))
@r.callback_query(F.data.startswith("wd:"))
async def wdm(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 method=c.data.split(":")[1]
 async with S() as s:await state(s,c.from_user.id,"wd_amount",method);await s.commit()
 hint="Комиссия 45 ₽ будет вычтена из суммы к получению." if method=="card" else "Без комиссии — вся сумма поступит на счёт."
 await replace_message(c, f"Введите сумму к выводу (минимум 100 ₽).\n{hint}")
@r.callback_query(F.data.startswith("wdbank:"))
async def wdbank(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 code=c.data.split(":")[1]
 async with S() as s:
  x=await s.get(State,c.from_user.id)
  if not x or x.action!="wd_bank":await c.answer("Сессия истекла, начните заново.",show_alert=True);return
  a,phone=x.data.split("|",1);a=Decimal(a)
  if code=="other":
   await state(s,c.from_user.id,"wd_bank_custom",f"{a}|{phone}");await s.commit()
   await replace_message(c, "Введите название банка вручную.");return
  bank_name=dict(SBP_BANKS).get(code,code)
  u=await s.get(User,c.from_user.id);u.balance-=a
  s.add(Withdrawal(user_id=u.id,amount=a,method="sbp",destination=f"{phone} ({bank_name})",status="pending"))
  await ledger(s,u.id,-a,"withdraw_hold","Заявка на вывод")
  await state(s,c.from_user.id,"","");await s.commit()
 await replace_message(c, f"✅ Заявка на вывод {a} ₽ создана.\nБанк: {bank_name}\nБез комиссии.")
@r.callback_query(F.data=="sup")
async def sup(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:await state(s,c.from_user.id,"ticket_new","");await s.commit()
 await send_screen(c, "Напишите сообщение для поддержки.", media_key="sup", reply_markup=kb([("⬅️ Назад","home")]))
@r.message(F.photo)
async def photo(m:Message):
 if not await role(m.from_user.id,"content"):return
 async with S() as s:
  x=await s.get(State,m.from_user.id)
  if x and x.action=="broadcast":
   await state(s,m.from_user.id,"",""); await s.commit()
   users=(await s.scalars(select(User.id).where(User.blocked==False))).all(); sent=failed=0
   for uid in users:
    try: await m.bot.copy_message(uid,m.chat.id,m.message_id); sent+=1
    except Exception: failed+=1
    await asyncio.sleep(0.04)
   await m.answer(f"📢 Рассылка завершена. Отправлено: {sent}, не доставлено: {failed}"); return
  if not x or x.action!="photo":return
  key=(m.caption or "").strip()
  if key not in ("menu","info","refs","link","sup","bal","faq"):await m.answer("Подпись: menu, info, refs, link, sup, bal или faq");return
  q=await s.get(Media,"photo:"+key);fid=m.photo[-1].file_id
  if q:q.file_id=fid
  else:s.add(Media(key="photo:"+key,file_id=fid))
  await state(s,m.from_user.id,"","");await s.commit()
 await m.answer("Фото сохранено.")
@r.message(F.text & ~F.text.startswith("/"))
async def on_text(m:Message):
 async with S() as s:
  x=await s.get(State,m.from_user.id)
  if x and x.action=="config_value":
   if m.from_user.id not in SUPER: return
   await setst(s,x.data,m.text.strip()); await state(s,m.from_user.id,"",""); await s.commit(); await m.answer("✅ Сохранено."); return
  if x and x.action=="broadcast":
   await state(s,m.from_user.id,"",""); await s.commit()
   users=(await s.scalars(select(User.id).where(User.blocked==False))).all()
   sent=failed=0
   for uid in users:
    try:
     await m.bot.copy_message(uid,m.chat.id,m.message_id); sent+=1
    except Exception: failed+=1
    await asyncio.sleep(0.04)
   await m.answer(f"📢 Рассылка завершена.\nОтправлено: {sent}\nНе доставлено: {failed}")
   return
  x=await s.get(State,m.from_user.id)
  if x and x.action=="edit_text":
   key=x.data
   await setst(s,"text:"+key,m.text)
   await state(s,m.from_user.id,"","")
   await s.commit()
   await m.answer(f"Текст «{key}» сохранён.")
   return
  if x and x.action=="ticket_new":
   t=Ticket(user_id=m.from_user.id);s.add(t);await s.flush();s.add(TM(ticket_id=t.id,sender_id=m.from_user.id,text=m.text));await state(s,m.from_user.id,"","");await s.commit()
   for a in SUPER:
    try:await m.bot.send_message(a,f"🆕 Тикет #{t.id} от {m.from_user.id}")
    except:pass
   await m.answer("Тикет создан.");return
  if x and x.action=="reply":
   tid=int(x.data);t=await s.get(Ticket,tid)
   if t:s.add(TM(ticket_id=tid,sender_id=m.from_user.id,text=m.text));await state(s,m.from_user.id,"","");await s.commit();await m.bot.send_message(t.user_id,f"🛠 Ответ по тикету #{tid}:\n{m.text}")
   return
  if x and x.action=="add_worker":
   try:wid=int(m.text.strip())
   except:await m.answer("Введите числовой Telegram ID.");return
   u=await s.get(User,wid)
   if not u:
    u=User(id=wid,is_worker=True);s.add(u)
   else:
    u.is_worker=True
   await state(s,m.from_user.id,"","");await s.commit()
   await m.answer(f"✅ Пользователь <code>{wid}</code> назначен работником.")
   try:await m.bot.send_message(wid,"🎉 Вам открыт полный доступ к боту!\nНажмите /start, чтобы начать.")
   except Exception:pass
   return
  if x and x.action=="ban_reason":
   uid=int(x.data);reason=m.text.strip()
   u=await s.get(User,uid)
   if not u:await m.answer("Пользователь не найден.");await state(s,m.from_user.id,"","");await s.commit();return
   u.blocked=True;u.ban_reason=reason
   await state(s,m.from_user.id,"","");await s.commit()
   try:await m.bot.send_message(uid,f"⛔ Вы заблокированы администрацией.\nПричина: {reason}")
   except Exception:pass
   await m.answer(f"⛔ Пользователь {uid} заблокирован.\nПричина: {reason}");return
  if x and x.action=="msg_user":
   uid=int(x.data);text_to_send=m.text
   await state(s,m.from_user.id,"","");await s.commit()
   try:
    await m.bot.send_message(uid,text_to_send);await m.answer(f"✅ Сообщение отправлено пользователю {uid}.")
   except Exception:
    await m.answer(f"❌ Не удалось отправить сообщение пользователю {uid} (возможно, он заблокировал бота).")
   return
  if x and x.action=="wd_amount":
   try:a=Decimal(m.text.replace(",","."))
   except:await m.answer("Введите число.");return
   if a<100:await m.answer("Минимальная сумма вывода — 100 ₽.");return
   method=x.data
   fee=FEES.get(method,Decimal(0))
   if a<=fee:await m.answer(f"Сумма должна быть больше комиссии ({fee} ₽).");return
   u=await s.get(User,m.from_user.id)
   if u.balance<a:await m.answer("Недостаточно средств.");return
   await state(s,m.from_user.id,"wd_dest",method+"|"+str(a));await s.commit()
   dest_hint="номер карты" if method=="card" else "номер телефона для СБП"
   await m.answer(f"Введите {dest_hint}.");return
  if x and x.action=="wd_dest":
   method,a=x.data.split("|");a=Decimal(a)
   if method=="sbp":
    await state(s,m.from_user.id,"wd_bank",f"{a}|{m.text}");await s.commit()
    await m.answer("Выберите банк получателя:",reply_markup=bank_kb());return
   fee=FEES.get(method,Decimal(0));net=a-fee
   u=await s.get(User,m.from_user.id);u.balance-=a
   s.add(Withdrawal(user_id=u.id,amount=a,method=method,destination=m.text,status="pending"))
   await ledger(s,u.id,-a,"withdraw_hold","Заявка на вывод")
   await state(s,m.from_user.id,"","");await s.commit()
   note=f"\nКомиссия: {fee} ₽\nК получению: {net} ₽" if fee else "\nБез комиссии."
   await m.answer(f"✅ Заявка на вывод {a} ₽ создана.{note}");return
  if x and x.action=="wd_bank_custom":
   a,phone=x.data.split("|",1);a=Decimal(a);bank=m.text.strip()
   u=await s.get(User,m.from_user.id);u.balance-=a
   s.add(Withdrawal(user_id=u.id,amount=a,method="sbp",destination=f"{phone} ({bank})",status="pending"))
   await ledger(s,u.id,-a,"withdraw_hold","Заявка на вывод")
   await state(s,m.from_user.id,"","");await s.commit()
   await m.answer(f"✅ Заявка на вывод {a} ₽ создана.\nБез комиссии.");return
  # user can continue latest open ticket
  t=await s.scalar(select(Ticket).where(Ticket.user_id==m.from_user.id,Ticket.status=="open").order_by(Ticket.id.desc()))
  if t:
   s.add(TM(ticket_id=t.id,sender_id=m.from_user.id,text=m.text));await s.commit()
   await m.answer("Сообщение добавлено в тикет.")
   for a in SUPER:
    try:await m.bot.send_message(a,f"✉️ Новое сообщение в тикете #{t.id} от {m.from_user.id}:\n{m.text}")
    except:pass
  else:
   await m.answer("У вас нет открытых тикетов. Чтобы написать в поддержку, нажмите «🆘 Поддержка» в главном меню.")
@r.message(Command("admin"))
async def admin(m:Message):
 if m.from_user.id not in SUPER and not any([await role(m.from_user.id,p) for p in ["user","ticket","payout","content"]]):return
 await m.answer("🛠 <b>АДМИН-ПАНЕЛЬ</b>",reply_markup=kb([("📊 Статистика","a:stats"),("👤 Пользователь","a:user")],[("👥 Все пользователи","a:users:all:0"),("👷 Работники","a:workers")],[("💸 Выплаты","a:payout"),("🆘 Тикеты","a:tickets")],[("📢 Рассылка","a:broadcast"),("🖼 Фото","a:photo")],[("⚙️ Каналы/ссылки","a:config")],
        [("📝 Тексты","a:texts")],
        [("⚠️ Важные сообщения","a:notices"),("🔓 Открыть выплаты","a:open"),("🔒 Закрыть выплаты","a:close")],
        [("🛑 Закрыть бота","a:botclose"),("▶️ Открыть бота","a:botopen_menu")]))
@r.callback_query(F.data=="a:texts")
async def atexts(c:CallbackQuery):
 if not await role(c.from_user.id,"content"):return
 await replace_message(c, "📝 <b>Редактирование текстов</b>\n\nВыберите экран, текст которого хотите изменить.", reply_markup=kb(
  [("🏠 Главное меню","a:text:menu")],
  [("ℹ️ Информация","a:text:info")],
  [("❓ FAQ","a:text:faq")],
  [("🎉 «Спасибо за подписку»","a:text:thanks")],
  [("🔙 Админ-панель","a:admin")]
 ))

@r.callback_query(F.data.startswith("a:text:"))
async def atext_pick(c:CallbackQuery):
 if not await role(c.from_user.id,"content"):return
 key=c.data.split(":",2)[2]
 if key not in {"menu","info","faq","thanks"}:return
 async with S() as s:
  current=await st(s,"text:"+key,"")
  await state(s,c.from_user.id,"edit_text",key)
  await s.commit()
 await replace_message(c, f"📝 <b>Текст: {key}</b>\n\nТекущий текст:\n{current or '— пока не задан —'}\n\nОтправьте мне следующим сообщением новый текст целиком. Он будет сохранён в PostgreSQL.")

@r.callback_query(F.data=="a:admin")
async def admin_back(c:CallbackQuery):
 if c.from_user.id not in SUPER and not any([await role(c.from_user.id,p) for p in ["user","ticket","payout","content"]]):return
 await replace_message(c, "🛠 <b>АДМИН-ПАНЕЛЬ</b>",reply_markup=kb([("📊 Статистика","a:stats"),("👤 Пользователь","a:user")],[("👥 Все пользователи","a:users:all:0"),("👷 Работники","a:workers")],[("💸 Выплаты","a:payout"),("🆘 Тикеты","a:tickets")],[("📢 Рассылка","a:broadcast"),("🖼 Фото","a:photo")],[("⚙️ Каналы/ссылки","a:config")],
        [("📝 Тексты","a:texts")],
        [("⚠️ Важные сообщения","a:notices"),("🔓 Открыть выплаты","a:open"),("🔒 Закрыть выплаты","a:close")],
        [("🛑 Закрыть бота","a:botclose"),("▶️ Открыть бота","a:botopen_menu")]))

@r.callback_query(F.data=="a:workers")
async def workers_screen(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 async with S() as s:
  rows=(await s.scalars(select(User).where(User.is_worker==True).order_by(User.created_at.desc()))).all()
 lines="\n".join(f"• {('@'+w.username) if w.username else 'ID '+str(w.id)} (<code>{w.id}</code>)" for w in rows) or "Пока нет ни одного работника."
 kb_rows=[[("❌ "+(('@'+w.username) if w.username else str(w.id)),f"a:unworker:{w.id}")] for w in rows[:20]]
 kb_rows.append([("➕ Добавить работника","a:addworker")])
 kb_rows.append([("🔙 Админ-панель","a:admin")])
 await replace_message(c, f"👷 <b>Работники</b>\n\nУ работников полный интерфейс бота (баланс, свой трафик, ссылка, выплаты). Обычные пользователи видят только подписку на каналы.\n\n{lines}", reply_markup=kb(*kb_rows))
@r.callback_query(F.data=="a:addworker")
async def addworker_start(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 async with S() as s:await state(s,c.from_user.id,"add_worker","");await s.commit()
 await replace_message(c, "Введите Telegram ID пользователя, которого нужно сделать работником.\n\nID можно узнать, например, через /find, если человек уже писал боту, либо попросить его прислать айди из @userinfobot.")
@r.callback_query(F.data.startswith("a:unworker:"))
async def unworker(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 wid=int(c.data.split(":")[2])
 async with S() as s:
  u=await s.get(User,wid)
  if u:u.is_worker=False
  await s.commit()
 try:await c.bot.send_message(wid,"ℹ️ Ваш статус работника снят администрацией.")
 except Exception:pass
 await workers_screen(c)
@r.callback_query(F.data=="a:user")
async def au(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 await replace_message(c, "Поиск: /find TELEGRAM_ID")
async def user_card(uid:int, back_data:str|None=None):
 async with S() as s:
  u=await s.get(User,uid)
  if not u: return None,None
  ref_label="—"
  if u.referrer_id:
   ref=await s.get(User,u.referrer_id)
   ref_label=(f"@{ref.username}" if ref.username else f"ID {ref.id}") if ref else f"ID {u.referrer_id} (удалён)"
  ref_count=await s.scalar(select(func.count()).select_from(User).where(User.referrer_id==uid)) or 0
  active_rewards=await s.scalar(select(func.count()).select_from(Reward).where(Reward.referrer_id==uid,Reward.status.in_(["hold","eligible"]))) or 0
 status_line="⛔ Заблокирован" + (f"\nПричина: {u.ban_reason}" if u.ban_reason else "") if u.blocked else "✅ Активен" if (u.captcha_ok and u.verified) else "🟡 Не завершил регистрацию"
 text_out=(f"👤 <b>{u.id}</b>  @{u.username or '—'}\n\n"
  f"Статус: {status_line}\n"
  f"Регистрация: {u.created_at.strftime('%d.%m.%Y %H:%M')}\n"
  f"Баланс: <b>{u.balance} ₽</b>\n"
  f"Пригласил: {ref_label}\n"
  f"Рефералов приведено: {ref_count} (активных наград: {active_rewards})")
 rows=[[("➕ Баланс","a:add:"+str(uid)),("➖ Баланс","a:sub:"+str(uid))],
       [("👥 Рефералы","a:refs:"+str(uid)),("✉️ Написать","a:msg:"+str(uid))]]
 rows.append([("✅ Разбанить","a:unban:"+str(uid))] if u.blocked else [("⛔ Заблокировать","a:banstart:"+str(uid))])
 if back_data:
  rows.append([("🔙 К списку пользователей",back_data)])
 return text_out,kb(*rows)
@r.message(Command("find"))
async def find(m:Message):
 if not await role(m.from_user.id,"user"):return
 try:uid=int(m.text.split()[1])
 except:await m.answer("Пример /find 123");return
 text_out,markup=await user_card(uid)
 if not text_out:await m.answer("Не найден.");return
 await m.answer(text_out,reply_markup=markup)
@r.callback_query(F.data.startswith("a:view:"))
async def view_user(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 parts=c.data.split(":")
 uid=int(parts[2])
 back_data=f"a:users:{parts[3]}:{parts[4]}" if len(parts)>=5 else None
 text_out,markup=await user_card(uid,back_data)
 if not text_out:
  await c.answer("Пользователь не найден.",show_alert=True);return
 await replace_message(c, text_out, reply_markup=markup)
USERS_PAGE_SIZE=10
@r.callback_query(F.data.startswith("a:users:"))
async def all_users(c:CallbackQuery):
 if not await role(c.from_user.id,"user"): return
 parts=c.data.split(":")
 flt=parts[2];offset=int(parts[3])
 cond=[]
 if flt=="active": cond=[User.captcha_ok==True,User.verified==True,User.blocked==False]
 async with S() as s:
  total=await s.scalar(select(func.count()).select_from(User).where(*cond))
  rows=(await s.scalars(select(User).where(*cond).order_by(User.created_at.desc()).offset(offset).limit(USERS_PAGE_SIZE))).all()
 title="👥 <b>Все пользователи</b>" if flt=="all" else "✅ <b>Активные пользователи</b>"
 header=f"{title}\nВсего: {total}, показаны {offset+1 if rows else 0}-{offset+len(rows)}\n\nНажмите на пользователя, чтобы открыть карточку."
 filter_row=[("🔎 Все" if flt!="all" else "• Все","a:users:all:0"),("✅ Активные" if flt!="active" else "• Активные","a:users:active:0")]
 user_rows=[]
 for u in rows:
  uname=f"@{u.username}" if u.username else f"ID {u.id}"
  flag=" ⛔" if u.blocked else (" ✅" if (u.captcha_ok and u.verified) else " 🟡")
  user_rows.append([(f"{uname}{flag} — {u.balance}₽",f"a:view:{u.id}:{flt}:{offset}")])
 nav=[]
 if offset>0: nav.append(("⬅️ Пред.",f"a:users:{flt}:{max(0,offset-USERS_PAGE_SIZE)}"))
 if offset+USERS_PAGE_SIZE<total: nav.append(("➡️ След.",f"a:users:{flt}:{offset+USERS_PAGE_SIZE}"))
 rows_kb=[filter_row]+user_rows+([nav] if nav else [])+[[("🔙 Админ-панель","a:admin")]]
 await replace_message(c, header, reply_markup=kb(*rows_kb))
@r.callback_query(F.data.startswith("a:refs:"))
async def admin_refs(c:CallbackQuery):
 if not await role(c.from_user.id,"user"): return
 uid=int(c.data.split(":")[2])
 async with S() as s:
  owner=await s.get(User,uid)
  rows=(await s.scalars(select(User).where(User.referrer_id==uid).order_by(User.created_at.desc()))).all()
  rewards={}
  if rows:
   rids=[u.id for u in rows]
   rw_rows=(await s.scalars(select(Reward).where(Reward.referral_id.in_(rids)))).all()
   rewards={rw.referral_id:rw for rw in rw_rows}
 owner_label=f"@{owner.username}" if owner and owner.username else f"ID: {uid}"
 status_map={"hold":"⏳ в холде","eligible":"✅ начислено","cancelled":"❌ отменено"}
 lines=[];kb_rows=[]
 shown=rows[:15]
 for u in shown:
  uname=f"@{u.username}" if u.username else f"ID: {u.id}"
  if u.blocked: uname+=" ⛔"
  rw=rewards.get(u.id)
  st_label=status_map.get(rw.status,rw.status) if rw else "—"
  lines.append(f"• {uname} — {st_label}")
  btn_row=[]
  if rw and rw.status=="hold":
   btn_row.append((f"🔓 Холд ({u.id})",f"a:relhold:{rw.id}"))
  btn_row.append((f"❌ Удалить ({u.id})",f"a:remref:{u.id}"))
  kb_rows.append(btn_row)
  if not u.blocked:
   kb_rows.append([(f"🚫 Заблокировать реферала ({u.id})",f"a:blockref:{u.id}")])
 if len(rows)>15: lines.append(f"…и ещё {len(rows)-15}")
 kb_rows.append([("🔙 К карточке пользователя",f"a:view:{uid}")])
 lines_txt="\n".join(lines) or "Нет рефералов."
 await replace_message(c, f"👥 Рефералы пользователя {owner_label}\nКоличество: {len(rows)}\n\n{lines_txt}", reply_markup=kb(*kb_rows))
@r.callback_query(F.data.startswith("a:relhold:"))
async def relhold(c:CallbackQuery):
 if not await role(c.from_user.id,"balance"): return
 rwid=int(c.data.split(":")[2])
 async with S() as s:
  rw=await s.get(Reward,rwid)
  if not rw or rw.status!="hold":
   await c.answer("Не найдено или уже обработано.",show_alert=True);return
  rw.status="eligible";rw.hold_until=datetime.now(timezone.utc)
  u=await s.get(User,rw.referrer_id)
  u.balance+=rw.amount
  await ledger(s,u.id,rw.amount,"referral_hold_released","Холд снят администратором")
  await s.commit()
 await replace_message(c, "✅ Холд снят, средства зачислены на баланс.")
@r.callback_query(F.data.startswith("a:remref:"))
async def remref(c:CallbackQuery):
 if not await role(c.from_user.id,"user"): return
 rid=int(c.data.split(":")[2])
 async with S() as s:
  ref_user=await s.get(User,rid)
  if not ref_user or not ref_user.referrer_id:
   await c.answer("У пользователя нет реферера.",show_alert=True);return
  owner_id=ref_user.referrer_id
  owner=await s.get(User,owner_id)
  rw=await s.scalar(select(Reward).where(Reward.referral_id==rid))
  amount=rw.amount if rw else Decimal(50)
  if owner:
   owner.balance-=amount
   await ledger(s,owner.id,-amount,"referral_removed",f"Реферал {rid} удалён администратором")
  if rw: await s.delete(rw)
  ref_user.referrer_id=None
  await s.commit()
 await replace_message(c, f"✅ Реферал удалён, с баланса списано {amount} ₽.")
@r.callback_query(F.data.startswith("a:blockref:"))
async def blockref(c:CallbackQuery):
 if not await role(c.from_user.id,"user"): return
 rid=int(c.data.split(":")[2])
 async with S() as s:
  ref_user=await s.get(User,rid)
  if not ref_user:
   await c.answer("Пользователь не найден.",show_alert=True);return
  owner=await s.get(User,ref_user.referrer_id) if ref_user.referrer_id else None
  rw=await s.scalar(select(Reward).where(Reward.referral_id==rid))
  amount=rw.amount if rw else Decimal(50)
  if owner:
   owner.balance-=amount
   await ledger(s,owner.id,-amount,"referral_blocked",f"Реферал {rid} заблокирован администратором")
  if rw: rw.status="cancelled"
  ref_user.blocked=True
  owner_id=owner.id if owner else None
  await s.commit()
 if owner_id:
  warn_text=("⚠️ <b>Предупреждение</b>\n\n"
   "Один из ваших рефералов заблокирован администрацией.\n"
   f"С вашего баланса списано {amount} ₽.\n\n"
   "Пожалуйста, не приглашайте девушек и не лейте ботов в бота — это нарушение правил.\n\n"
   "⛔ При повторном нарушении ваш аккаунт будет заблокирован.")
  try:await c.bot.send_message(owner_id,warn_text)
  except Exception:pass
 note=f" Пригласившему списано {amount} ₽ и отправлено предупреждение." if owner_id else " У реферала нет пригласившего, предупреждение не отправлено."
 await replace_message(c, "🚫 Реферал заблокирован."+note)

@r.callback_query(F.data.startswith("a:add:")|F.data.startswith("a:sub:"))
async def ab(c:CallbackQuery):
 if not await role(c.from_user.id,"balance"):return
 mode,uid=c.data.split(":")[1:];await replace_message(c, f"/balance {uid} {'+' if mode=='add' else '-'}50")
@r.message(Command("balance"))
async def bc(m:Message):
 if not await role(m.from_user.id,"balance"):return
 try:_,uid,d=m.text.split();uid=int(uid);d=Decimal(d)
 except:await m.answer("Формат /balance ID +50");return
 async with S() as s:
  u=await s.get(User,uid)
  if not u: await m.answer("Пользователь не найден."); return
  u.balance+=d; await ledger(s,uid,d,"manual","Изменение администратором"); await s.commit()
 await m.answer("Готово.")
@r.callback_query(F.data.startswith("a:banstart:"))
async def banstart(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 uid=int(c.data.split(":")[2])
 async with S() as s:await state(s,c.from_user.id,"ban_reason",str(uid));await s.commit()
 await replace_message(c, f"Введите причину блокировки пользователя <code>{uid}</code>.\nОн получит её текстом.")
@r.callback_query(F.data.startswith("a:unban:"))
async def unban(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 uid=int(c.data.split(":")[2])
 async with S() as s:
  u=await s.get(User,uid)
  if not u:await c.answer("Не найден.",show_alert=True);return
  u.blocked=False;u.ban_reason=None;await s.commit()
 try:await c.bot.send_message(uid,"✅ Вы разблокированы и снова можете пользоваться ботом.")
 except Exception:pass
 text_out,markup=await user_card(uid)
 await replace_message(c, "✅ Пользователь разблокирован.\n\n"+text_out, reply_markup=markup)
@r.callback_query(F.data.startswith("a:msg:"))
async def msg_start(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 uid=int(c.data.split(":")[2])
 async with S() as s:await state(s,c.from_user.id,"msg_user",str(uid));await s.commit()
 await replace_message(c, f"Введите текст сообщения для пользователя <code>{uid}</code>.")
@r.callback_query(F.data=="a:tickets")
async def ats(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 async with S() as s: rows=(await s.scalars(select(Ticket).where(Ticket.status=="open").order_by(Ticket.created_at.desc()))).all()
 if not rows:
  await replace_message(c,"Открытых тикетов нет.",reply_markup=kb([("🔙 Админ-панель","a:admin")]))
  return
 lines="\n".join(f"• #{t.id} — {t.user_id}" for t in rows[:20])
 more=f"\n…и ещё {len(rows)-20}" if len(rows)>20 else ""
 await replace_message(c,"🆘 <b>Открытые тикеты</b>\n"+lines+more,reply_markup=kb(*[[(f"Тикет #{t.id}",f"a:ticket:{t.id}")] for t in rows[:20]]+[["🔙 Админ-панель","a:admin"]]))
@r.callback_query(F.data.startswith("a:ticket:"))
async def ticket_open(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 tid=int(c.data.split(":")[2])
 async with S() as s:
  t=await s.get(Ticket,tid)
  msgs=(await s.scalars(select(TM).where(TM.ticket_id==tid).order_by(TM.created_at.desc()).limit(10))).all()
 if not t: await c.answer("Тикет не найден",show_alert=True); return
 body="\n\n".join(f"<b>{'Пользователь' if x.sender_id==t.user_id else 'Админ'}:</b> {x.text}" for x in reversed(msgs)) or "Сообщений нет."
 await replace_message(c,f"🆘 Тикет #{tid}\nПользователь: <code>{t.user_id}</code>\n\n{body}",reply_markup=kb([("💬 Ответить",f"a:reply:{tid}"),("🔒 Закрыть",f"a:closet:{tid}")],["🔙 Список","a:tickets"]))
@r.callback_query(F.data.startswith("a:reply:"))
async def ar(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 async with S() as s:await state(s,c.from_user.id,"reply",c.data.split(":")[2]);await s.commit()
 await replace_message(c, "Напишите ответ.")
@r.callback_query(F.data.startswith("a:closet:"))
async def ct(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 async with S() as s:t=await s.get(Ticket,int(c.data.split(":")[2]));t.status="closed";await s.commit()
 await replace_message(c, "Тикет закрыт.")
@r.callback_query(F.data=="a:payout")
async def ap(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 async with S() as s: rows=(await s.scalars(select(Withdrawal).where(Withdrawal.status=="pending").order_by(Withdrawal.created_at.desc()))).all()
 if not rows:
  await replace_message(c,"Заявок на выплату нет.",reply_markup=kb([("🔙 Админ-панель","a:admin")]))
  return
 await replace_message(c,"💸 <b>Заявки на выплату</b>",reply_markup=kb(*[[(f"#{w.id} — {w.amount}₽ ({METHOD_LABELS.get(w.method,w.method)})",f"a:payview:{w.id}")] for w in rows[:20]]+[["🔙 Админ-панель","a:admin"]]))
@r.callback_query(F.data.startswith("a:payview:"))
async def payout_view(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 wid=int(c.data.split(":")[2])
 async with S() as s:w=await s.get(Withdrawal,wid)
 if not w: await c.answer("Заявка не найдена",show_alert=True); return
 fee=FEES.get(w.method,Decimal(0));net=w.amount-fee
 method_label=METHOD_LABELS.get(w.method,w.method)
 await replace_message(c,f"#{w.id}\nПользователь: <code>{w.user_id}</code>\nСписано с баланса: <b>{w.amount} ₽</b>\nКомиссия: {fee} ₽\nК выплате: <b>{net} ₽</b>\nСпособ: {method_label}\nРеквизиты: <code>{w.destination}</code>",reply_markup=kb([("✅ Выплачено",f"a:paid:{w.id}"),("❌ Отклонить",f"a:rej:{w.id}")],["🔙 Список","a:payout"]))
@r.callback_query(F.data.startswith("a:paid:")|F.data.startswith("a:rej:"))
async def pd(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 act,wid=c.data.split(":")[1],int(c.data.split(":")[2])
 async with S() as s:
  w=await s.get(Withdrawal,wid)
  if not w or w.status!="pending":
   await c.answer("Заявка уже обработана или не найдена.",show_alert=True);return
  if act=="paid":w.status="paid";await ledger(s,w.user_id,-w.amount,"withdraw_paid",f"#{wid}")
  else:w.status="rejected";u=await s.get(User,w.user_id);u.balance+=w.amount;await ledger(s,u.id,w.amount,"withdraw_refund",f"#{wid}")
  await s.commit()
 await replace_message(c, "Готово.")
@r.callback_query(F.data.in_({"a:open","a:close"}))
async def toggle(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 async with S() as s:await setst(s,"payout_manual","open" if c.data=="a:open" else "closed");await s.commit()
 await replace_message(c, "Настройка выплат сохранена.")
@r.callback_query(F.data=="a:botclose")
async def bot_close(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 async with S() as s:await setst(s,"bot_status","closed");await s.commit()
 await replace_message(c, "🛑 Бот закрыт.\n\nОбычные пользователи теперь видят ограниченное меню: Баланс, Мой трафик, Выплаты. Новые пользователи (кто ещё не заходил в бота) при старте получают сообщение о временной приостановке работы.", reply_markup=kb([("🔙 Админ-панель","a:admin")]))
@r.callback_query(F.data=="a:botopen_menu")
async def bot_open_menu(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 await replace_message(c, "Как открыть бота?", reply_markup=kb(
  [("📢 С уведомлением всем","a:botopen:notify")],
  [("🔕 Без уведомления","a:botopen:silent")],
  [("🔙 Админ-панель","a:admin")]
 ))
@r.callback_query(F.data.startswith("a:botopen:"))
async def bot_open(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 mode=c.data.split(":")[2]
 async with S() as s:
  await setst(s,"bot_status","open");await s.commit()
  ids=(await s.scalars(select(User.id).where(User.blocked==False))).all() if mode=="notify" else []
 if mode=="notify":
  await replace_message(c, f"✅ Бот открыт. Рассылка уведомления запущена, получателей: {len(ids)}.\nОтчёт придёт по завершении.", reply_markup=kb([("🔙 Админ-панель","a:admin")]))
  asyncio.create_task(do_broadcast(c.bot,c.from_user.id,ids,"✅ Бот восстановил свою работу!"))
 else:
  await replace_message(c, "✅ Бот открыт без уведомления пользователей.", reply_markup=kb([("🔙 Админ-панель","a:admin")]))
@r.callback_query(F.data=="a:stats")
async def astats(c:CallbackQuery):
    if not await role(c.from_user.id,"user"): return
    async with S() as s:
        total_users=await s.scalar(select(func.count()).select_from(User)) or 0
        total_balance=await s.scalar(select(func.coalesce(func.sum(User.balance),0)).select_from(User)) or 0
        total_hold=await s.scalar(select(func.coalesce(func.sum(Reward.amount),0)).where(Reward.status=="hold")) or 0
        total_to_pay=await s.scalar(select(func.coalesce(func.sum(Withdrawal.amount),0)).where(Withdrawal.status=="pending")) or 0
        total_refs=await s.scalar(select(func.count()).select_from(Reward).where(Reward.status.in_(["hold","eligible"]))) or 0
        bot_status=await st(s,"bot_status","open")
    status_label="🟢 Открыт" if bot_status!="closed" else "🛑 Закрыт"
    await replace_message(c,
        f"📊 <b>Общая статистика</b>\n\n"
        f"Статус бота: <b>{status_label}</b>\n\n"
        f"👤 Пользователей: <b>{total_users}</b>\n"
        f"👥 Активных рефералов: <b>{total_refs}</b>\n"
        f"💰 На балансах: <b>{total_balance} ₽</b>\n"
        f"⏳ В холде: <b>{total_hold} ₽</b>\n"
        f"💸 Нужно выплатить: <b>{total_to_pay} ₽</b>",
        reply_markup=kb([("🔙 Админ-панель","a:admin")]))

@r.callback_query(F.data=="a:broadcast")
async def abroadcast(c:CallbackQuery):
    if not await role(c.from_user.id,"content"): return
    async with S() as s:
        await state(s,c.from_user.id,"broadcast","")
        await s.commit()
    await replace_message(c,"📢 Отправьте одним сообщением то, что нужно разослать всем пользователям.\nМожно использовать текст, фото, видео, документ и другие типы сообщений.")

@r.callback_query(F.data=="a:config")
async def aconfig(c:CallbackQuery):
    if c.from_user.id not in SUPER:return
    async with S() as s:
        pc=await public_channel(s); pu=await public_url(s)
        p1=await st(s,"private_channel_1",""); p1u=await private_url_1(s)
        p2=await st(s,"private_channel_2",""); p2u=await private_url_2(s)
        payout=await st(s,"payout_url","")
    await replace_message(c,
        "⚙️ <b>Каналы и ссылки</b>\n\n"
        f"📢 Публичный канал: <code>{pc or '—'}</code>\n🔗 {pu or '—'}\n\n"
        f"🔒 Частный №1: <code>{p1 or '—'}</code>\n🔗 {p1u or '—'}\n\n"
        f"🔒 Частный №2 (не проверяется): <code>{p2 or '—'}</code>\n🔗 {p2u or '—'}\n\n"
        f"💸 Выплаты: {payout or '—'}\n\n"
        "Выберите, что изменить:",
        reply_markup=kb(
            [("📢 ID публичного","a:setcfg:public_channel"),("🔗 Ссылка публичного","a:setcfg:public_url")],
            [("🔒 ID частного №1","a:setcfg:private_channel_1"),("🔗 Ссылка №1","a:setcfg:private_url_1")],
            [("🔒 ID частного №2","a:setcfg:private_channel_2"),("🔗 Ссылка №2","a:setcfg:private_url_2")],
            [("💸 Ссылка выплат","a:setcfg:payout_url")],
            [("🔙 Админ-панель","a:admin")
        ]))

@r.callback_query(F.data.startswith("a:setcfg:"))
async def setcfg_pick(c:CallbackQuery):
    if c.from_user.id not in SUPER:return
    key=c.data.split(":",2)[2]
    labels={
        "public_channel":"ID публичного канала (например -1001234567890)",
        "public_url":"ссылку публичного канала",
        "private_channel_1":"ID частного канала №1 (например -1001234567890)",
        "private_url_1":"ссылку частного канала №1",
        "private_channel_2":"ID частного канала №2 (например -1001234567890)",
        "private_url_2":"ссылку частного канала №2",
        "payout_url":"ссылку публичного канала выплат",
    }
    async with S() as s:
        await state(s,c.from_user.id,"config_value",key);await s.commit()
    await replace_message(c,f"Отправьте {labels.get(key,key)} одним сообщением.")

@r.callback_query(F.data=="a:notices")
async def anotices(c:CallbackQuery):
 if not await role(c.from_user.id,"content"):return
 await replace_message(c, "Управление важными сообщениями:\n/noticeadd Номер Текст\n/noticelist\n/noticedel ID")
@r.message(Command("noticeadd"))
async def noticeadd(m:Message):
 if not await role(m.from_user.id,"content"):return
 try:_,pos,text=m.text.split(maxsplit=2);pos=int(pos)
 except:await m.answer("Формат: /noticeadd 1 Текст");return
 async with S() as s:s.add(Notice(position=pos,text=text,enabled=True));await s.commit()
 await m.answer("Сообщение добавлено.")
@r.message(Command("noticelist"))
async def noticelist(m:Message):
 if not await role(m.from_user.id,"content"):return
 async with S() as s:rows=(await s.scalars(select(Notice).order_by(Notice.position,Notice.id))).all()
 await m.answer("\n".join(f"#{x.id} [{x.position}] {'ON' if x.enabled else 'OFF'} — {x.text}" for x in rows) or "Пусто.")
@r.message(Command("noticedel"))
async def noticedel(m:Message):
 if not await role(m.from_user.id,"content"):return
 try:i=int(m.text.split()[1])
 except:await m.answer("Формат /noticedel ID");return
 async with S() as s:
  x=await s.get(Notice,i)
  if x: await s.delete(x)
  await s.commit()
 await m.answer("Удалено.")

@r.callback_query(F.data=="a:photo")
async def aph(c:CallbackQuery):
 if not await role(c.from_user.id,"content"):return
 async with S() as s:await state(s,c.from_user.id,"photo","");await s.commit()
 await replace_message(c, "Отправьте фото с подписью: menu, info, refs, link, sup, bal или faq.")
@r.callback_query(F.data.in_({"info","faq"}))
async def content(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 default="Информация пока не добавлена." if c.data=="info" else "FAQ пока не заполнен."
 async with S() as s:txt=await st(s,"text:"+c.data,default);pic=await s.get(Media,"photo:"+c.data)
 if pic:
  try: await c.answer()
  except Exception: pass
  try: await c.message.delete()
  except Exception: pass
  await c.bot.send_photo(c.message.chat.id, pic.file_id, caption=txt, reply_markup=kb([("⬅️ Назад","home")]))
 else:await replace_message(c, txt, reply_markup=kb([("⬅️ Назад","home")]))
async def process_referral_state(s, bot, rw, now):
    ok = await required_channels_ok(bot, rw.referral_id)
    rw.last_ok = ok
    u = await s.get(User, rw.referrer_id)
    if not ok:
        if rw.status in ("hold","eligible"):
            # Remove currently credited reward only once. Cancelled rewards can
            # later be reactivated with a brand-new hold.
            if rw.status=="eligible" and u:
                u.balance -= rw.amount
                await ledger(s,u.id,-rw.amount,"referral_unsubscribed",
                             f"Реферал {rw.referral_id} отписался/не выполнил условия")
            rw.status="cancelled"
        return
    if rw.status=="cancelled":
        rw.status="hold"
        rw.hold_until=now+timedelta(hours=30)
        rw.last_ok=True
        return
    if rw.status=="hold" and now>=rw.hold_until and u:
        rw.status="eligible"
        u.balance += rw.amount
        await ledger(s,u.id,rw.amount,"referral","Подтверждённый реферал")

async def monitor(bot):
    while True:
        try:
            async with S() as s:
                rows=(await s.scalars(select(Reward).where(Reward.status.in_(["hold","eligible","cancelled"])))).all()
                now=datetime.now(timezone.utc)
                for q in rows:
                    await process_referral_state(s,bot,q,now)
                await s.commit()
        except Exception:
            logging.exception("monitor")
        await asyncio.sleep(300)


@r.message()
async def broadcast_other(m:Message):
    async with S() as s:
        x=await s.get(State,m.from_user.id)
        if not x or x.action!="broadcast": return
        await state(s,m.from_user.id,"",""); await s.commit()
        users=(await s.scalars(select(User.id).where(User.blocked==False))).all()
    sent=failed=0
    for uid in users:
        try:
            await m.bot.copy_message(uid,m.chat.id,m.message_id); sent+=1
        except Exception: failed+=1
        await asyncio.sleep(0.04)
    await m.answer(f"📢 Рассылка завершена. Отправлено: {sent}, не доставлено: {failed}")

async def migrate_bigint_columns(conn):
    # Safe PostgreSQL migration for Telegram IDs. Existing INTEGER columns are
    # upgraded before inserting any modern Telegram ID (> 2,147,483,647).
    columns = [
        ("users", "id"), ("users", "referrer_id"),
        ("admins", "user_id"),
        ("rewards", "referrer_id"), ("rewards", "referral_id"),
        ("ledger", "user_id"), ("withdrawals", "user_id"),
        ("tickets", "user_id"), ("ticket_messages", "sender_id"),
        ("states", "user_id"),
    ]
    for table_name, column_name in columns:
        result = await conn.execute(text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
              AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        current_type = result.scalar_one_or_none()
        if current_type == "integer":
            logging.warning("Migrating %s.%s from INTEGER to BIGINT", table_name, column_name)
            await conn.execute(text(
                f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" TYPE BIGINT USING "{column_name}"::BIGINT'
            ))
        elif current_type:
            logging.info("Schema OK: %s.%s is %s", table_name, column_name, current_type)


async def migrate_add_columns(conn):
    await conn.execute(text('ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "ban_reason" VARCHAR(500)'))
    await conn.execute(text('ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "is_worker" BOOLEAN NOT NULL DEFAULT FALSE'))

async def init_db():
    async with eng.begin() as conn:
        await conn.run_sync(B.metadata.create_all)
        await migrate_bigint_columns(conn)
        await migrate_add_columns(conn)
        check = await conn.execute(text("""
            SELECT data_type FROM information_schema.columns
            WHERE table_schema=current_schema()
              AND table_name='admins' AND column_name='user_id'
        """))
        admin_id_type = check.scalar_one_or_none()
        logging.warning("Database schema admins.user_id = %s", admin_id_type)
        if admin_id_type != "bigint":
            raise RuntimeError(
                f"Migration failed: admins.user_id is {admin_id_type!r}, expected bigint"
            )
    async with S() as s:
        for admin_id in SUPER:
            admin_id = int(admin_id)
            if await s.get(Admin, admin_id) is None:
                s.add(Admin(user_id=admin_id, role="superadmin"))
        await s.commit()


async def health(request):
    return web.Response(text="OK")


async def run():
    await init_db()

    bot = Bot(
        TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    dp.include_router(r)

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner,
        "0.0.0.0",
        int(os.getenv("PORT", "10000"))
    )
    await site.start()

    monitor_task = asyncio.create_task(monitor(bot))

    try:
        logging.info("Bot started successfully")
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        await runner.cleanup()
        await bot.session.close()
        await eng.dispose()


if __name__ == "__main__":
    asyncio.run(run())
