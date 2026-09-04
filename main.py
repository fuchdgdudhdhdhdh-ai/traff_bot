import asyncio,logging,os,random
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from aiohttp import web
from aiogram import Bot,Dispatcher,Router,F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart,Command
from aiogram.types import Message,CallbackQuery,InlineKeyboardButton,InlineKeyboardMarkup
from sqlalchemy import String,Integer,BigInteger,Boolean,DateTime,Text,Numeric,select,func,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
logging.basicConfig(level=logging.INFO)
logging.warning("STARTING BOT BUILD: BIGINT-FIX-2026-09-04")
from config import BOT_TOKEN, ADMIN_IDS, DATABASE_URL
TOKEN=BOT_TOKEN; DB=DATABASE_URL; SUPER=set(ADMIN_IDS)
eng=create_async_engine(DB,pool_pre_ping=True);S=async_sessionmaker(eng,expire_on_commit=False);r=Router()
PERMS={"superadmin":{"all"},"finance":{"payout","balance"},"support":{"ticket"},"moderator":{"user"},"content":{"content"}}
class B(DeclarativeBase):pass
class User(B):
 __tablename__="users";id:Mapped[int]=mapped_column(BigInteger,primary_key=True);username:Mapped[str|None]=mapped_column(String(64),nullable=True);referrer_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True);balance:Mapped[Decimal]=mapped_column(Numeric(12,2),default=0);captcha_ok:Mapped[bool]=mapped_column(Boolean,default=False);verified:Mapped[bool]=mapped_column(Boolean,default=False);blocked:Mapped[bool]=mapped_column(Boolean,default=False);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Admin(B):__tablename__="admins";user_id:Mapped[int]=mapped_column(BigInteger,primary_key=True);role:Mapped[str]=mapped_column(String(20))
class Reward(B):__tablename__="rewards";id:Mapped[int]=mapped_column(Integer,primary_key=True);referrer_id:Mapped[int]=mapped_column(BigInteger);referral_id:Mapped[int]=mapped_column(BigInteger,unique=True);amount:Mapped[Decimal]=mapped_column(Numeric(12,2));status:Mapped[str]=mapped_column(String(20));hold_until:Mapped[datetime]=mapped_column(DateTime(timezone=True));last_ok:Mapped[bool]=mapped_column(Boolean,default=True)
class Ledger(B):__tablename__="ledger";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(BigInteger);amount:Mapped[Decimal]=mapped_column(Numeric(12,2));kind:Mapped[str]=mapped_column(String(40));description:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Withdrawal(B):__tablename__="withdrawals";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(BigInteger);amount:Mapped[Decimal]=mapped_column(Numeric(12,2));method:Mapped[str]=mapped_column(String(40));destination:Mapped[str]=mapped_column(Text);status:Mapped[str]=mapped_column(String(20),default="pending");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Ticket(B):__tablename__="tickets";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(BigInteger);status:Mapped[str]=mapped_column(String(20),default="open");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class TM(B):__tablename__="ticket_messages";id:Mapped[int]=mapped_column(Integer,primary_key=True);ticket_id:Mapped[int]=mapped_column(Integer);sender_id:Mapped[int]=mapped_column(BigInteger);text:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Setting(B):__tablename__="settings";key:Mapped[str]=mapped_column(String(100),primary_key=True);value:Mapped[str]=mapped_column(Text)
class Media(B):__tablename__="media";key:Mapped[str]=mapped_column(String(100),primary_key=True);file_id:Mapped[str]=mapped_column(String(255))
class State(B):__tablename__="states";user_id:Mapped[int]=mapped_column(BigInteger,primary_key=True);action:Mapped[str]=mapped_column(String(50),default="");data:Mapped[str]=mapped_column(Text,default="")
class Notice(B):
 __tablename__="notices";id:Mapped[int]=mapped_column(Integer,primary_key=True);position:Mapped[int]=mapped_column(Integer,default=0);text:Mapped[str]=mapped_column(Text);enabled:Mapped[bool]=mapped_column(Boolean,default=True)
async def public_url(s): return await st(s,"public_url","")
async def private_url(s): return await st(s,"private_url","")
async def public_channel(s): return await st(s,"public_channel","")
async def join_kb(s):
 pu=await public_url(s); pr=await private_url(s)
 rows=[]
 if pr: rows.append([("🔒 Частный канал",pr)])
 if pu: rows.append([("📢 Публичный канал",pu)])
 rows.append([("✅ Я подписался","check")])
 return kb(*rows)
def kb(*rows):
    keyboard = []
    for row in rows:
        buttons = []
        for x, y in row:
            if isinstance(y, str) and y.startswith(("http://", "https://", "tg://")):
                buttons.append(InlineKeyboardButton(text=x, url=y))
            else:
                buttons.append(InlineKeyboardButton(text=x, callback_data=y))
        keyboard.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
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
async def ledger(s,u,a,k,d):s.add(Ledger(user_id=u,amount=a,kind=k,description=d))
async def role(uid,p):
 if uid in SUPER:return True
 async with S() as s:x=await s.get(Admin,uid);return bool(x and (p in PERMS.get(x.role,set()) or "all" in PERMS.get(x.role,set())))
async def sub(bot,uid):
 async with S() as s: channel=await public_channel(s)
 if not channel:return True
 try:return (await bot.get_chat_member(channel,uid)).status not in ("left","kicked")
 except:return False
async def access(c,bot):
 async with S() as s:u=await s.get(User,c.from_user.id)
 if not u or u.blocked or not u.captcha_ok or not await sub(bot,c.from_user.id):
  async with S() as s:
   markup = await join_kb(s)
  await c.message.answer("⚠️ Нет доступа. Подпишитесь на каналы и нажмите «Я подписался».", reply_markup=markup)
  return False
 return True
async def menu(m):
 await m.answer("🏠 <b>Главное меню</b>",reply_markup=kb([("💰 Баланс","bal"),("👥 Рефералы","refs")],[("🔗 Моя ссылка","link"),("🆘 Поддержка","sup")],[("ℹ️ Информация","info"),("❓ Помощь","help")]))
@r.message(CommandStart())
async def start(m:Message,bot:Bot):
 p=m.text.split();ref=int(p[1][4:]) if len(p)>1 and p[1].startswith("ref_") and p[1][4:].isdigit() else None
 async with S() as s:
  u=await s.get(User,m.from_user.id)
  if not u:s.add(User(id=m.from_user.id,username=m.from_user.username,referrer_id=ref if ref!=m.from_user.id else None));await s.commit();u=await s.get(User,m.from_user.id)
  if u.blocked:await m.answer("⛔ Доступ заблокирован.");return
  if u.captcha_ok and await sub(bot,u.id):u.verified=True;await s.commit();await menu(m);return
 word,ok,other=random.choice([("солнце","☀️",["🌙","🍎"]),("яблоко","🍎",["🐟","🚗"]),("рыба","🐟",["🌳","⭐"])])
 z=[ok,*other];random.shuffle(z);await m.answer(f"🧩 Выберите эмодзи для слова <b>{word}</b>",reply_markup=kb(*[[(x,f"cap:{ok}:{x}") for x in z]]))
@r.callback_query(F.data.startswith("cap:"))
async def cap(c:CallbackQuery):
 _,ok,x=c.data.split(":")
 if x!=ok:await c.answer("Неверно.",show_alert=True);return
 async with S() as s:u=await s.get(User,c.from_user.id);u.captcha_ok=True;await s.commit()
 async with S() as s:
  markup = await join_kb(s)
 await c.message.answer("Подпишитесь на каналы и затем нажмите «Я подписался».", reply_markup=markup)
@r.callback_query(F.data=="check")
async def check(c:CallbackQuery,bot:Bot):
 if not await sub(bot,c.from_user.id):await c.answer("Подписка не найдена.",show_alert=True);return
 async with S() as s:
  u=await s.get(User,c.from_user.id);first=not u.verified;u.verified=True
  if first and u.referrer_id and await s.get(User,u.referrer_id):s.add(Reward(referrer_id=u.referrer_id,referral_id=u.id,amount=50,status="hold",hold_until=datetime.now(timezone.utc)+timedelta(days=3)))
  await s.commit()
 async with S() as s:
  n=await s.scalar(select(Notice).where(Notice.enabled==True).order_by(Notice.position,Notice.id))
  if n:
   await state(s,c.from_user.id,"notice",str(n.position));await s.commit()
   await c.message.answer(n.text,reply_markup=kb([("➡️ Дальше","notice_next")]))
   return
 await menu(c.message)
@r.callback_query(F.data=="notice_next")
async def notice_next(c:CallbackQuery):
 async with S() as s:
  x=await s.get(State,c.from_user.id); pos=int(x.data or "0")
  nxt=await s.scalar(select(Notice).where(Notice.enabled==True,Notice.position>pos).order_by(Notice.position,Notice.id))
  if nxt:
   await state(s,c.from_user.id,"notice",str(nxt.position));await s.commit()
   await c.answer("⚠️ Внимательно ознакомьтесь: это очень важно!",show_alert=True)
   await c.message.answer(nxt.text,reply_markup=kb([("➡️ Дальше","notice_next")]))
   return
  await state(s,c.from_user.id,"","");await s.commit()
 await c.answer("⚠️ Внимательно ознакомьтесь: это очень важно!",show_alert=True)
 await menu(c.message)

@r.callback_query(F.data=="home")
async def home(c:CallbackQuery): await menu(c.message)

@r.callback_query(F.data=="bal")
async def bal(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:
  u=await s.get(User,c.from_user.id);h=await s.scalar(select(func.coalesce(func.sum(Reward.amount),0)).where(Reward.referrer_id==u.id,Reward.status=="hold"))
 await c.message.answer(f"💰 Баланс: <b>{u.balance} ₽</b>\nВ холде: <b>{h} ₽</b>",reply_markup=kb([("💸 Вывести","wd")],[("⬅️ Назад","home")]))
@r.callback_query(F.data=="refs")
async def refs(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:
  rows=(await s.scalars(select(User).where(User.referrer_id==c.from_user.id).order_by(User.created_at.desc()))).all()
 names="\n".join(f"• @{x.username}" if x.username else f"• ID: {x.id}" for x in rows) or "Нет рефералов."
 await c.message.answer(f"👥 Рефералов 1 уровня: {len(rows)}\n\n{names}")
@r.callback_query(F.data=="link")
async def link(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 me=await bot.get_me();await c.message.answer(f"https://t.me/{me.username}?start=ref_{c.from_user.id}")
@r.callback_query(F.data=="wd")
async def wd(c:CallbackQuery):
 async with S() as s:
  manual=await st(s,"payout_manual","auto");open_=manual=="open" or (manual=="auto" and datetime.now(timezone.utc).weekday() in (5,6))
 if not open_:await c.answer("Выплаты закрыты.",show_alert=True);return
 await c.message.answer("Способ:",reply_markup=kb([("💳 Карта","wd:card"),("📱 Телефон","wd:phone")],[("₮ USDT","wd:usdt"),("🎫 Чек","wd:check")]))
@r.callback_query(F.data.startswith("wd:"))
async def wdm(c:CallbackQuery):
 async with S() as s:await state(s,c.from_user.id,"wd_amount",c.data.split(":")[1]);await s.commit()
 await c.message.answer("Введите сумму (минимум 500).")
@r.callback_query(F.data=="sup")
async def sup(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:await state(s,c.from_user.id,"ticket_new","");await s.commit()
 await c.message.answer("Напишите сообщение для поддержки.")
@r.message(F.photo)
async def photo(m:Message):
 if not await role(m.from_user.id,"content"):return
 async with S() as s:
  x=await s.get(State,m.from_user.id)
  if not x or x.action!="photo":return
  key=(m.caption or "").strip()
  if key not in ("menu","info","help"):await m.answer("Подпись menu/info/help");return
  q=await s.get(Media,"photo:"+key);fid=m.photo[-1].file_id
  if q:q.file_id=fid
  else:s.add(Media(key="photo:"+key,file_id=fid))
  await state(s,m.from_user.id,"","");await s.commit()
 await m.answer("Фото сохранено.")
@r.message(F.text & ~F.text.startswith("/"))
async def on_text(m:Message):
 async with S() as s:
  x=await s.get(State,m.from_user.id)
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
  if x and x.action=="wd_amount":
   try:a=Decimal(m.text.replace(",","."))
   except:await m.answer("Число.");return
   if a<500:await m.answer("Минимум 500.");return
   u=await s.get(User,m.from_user.id)
   if u.balance<a:await m.answer("Недостаточно средств.");return
   await state(s,m.from_user.id,"wd_dest",x.data+"|"+str(a));await s.commit();await m.answer("Введите реквизиты.");return
  if x and x.action=="wd_dest":
   method,a=x.data.split("|");a=Decimal(a);u=await s.get(User,m.from_user.id);u.balance-=a;s.add(Withdrawal(user_id=u.id,amount=a,method=method,destination=m.text,status="pending"));await ledger(s,u.id,-a,"withdraw_hold","Заявка на вывод");await state(s,m.from_user.id,"","");await s.commit();await m.answer("Заявка создана.");return
  # user can continue latest open ticket
  t=await s.scalar(select(Ticket).where(Ticket.user_id==m.from_user.id,Ticket.status=="open").order_by(Ticket.id.desc()))
  if t:s.add(TM(ticket_id=t.id,sender_id=m.from_user.id,text=m.text));await s.commit();await m.answer("Сообщение добавлено в тикет.")
@r.message(Command("admin"))
async def admin(m:Message):
 if m.from_user.id not in SUPER and not any([await role(m.from_user.id,p) for p in ["user","ticket","payout","content"]]):return
 await m.answer("🛠 <b>АДМИН-ПАНЕЛЬ</b>",reply_markup=kb([("👤 Пользователь","a:user"),("💸 Выплаты","a:payout")],[("🆘 Тикеты","a:tickets"),("🖼 Фото","a:photo")],
        [("⚙️ Каналы/ссылки","a:config"),("📝 Тексты","a:texts")],
        [("⚠️ Важные сообщения","a:notices"),("🔓 Открыть","a:open"),("🔒 Закрыть","a:close")]))
@r.callback_query(F.data=="a:user")
async def au(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 await c.message.answer("Поиск: /find TELEGRAM_ID")
@r.message(Command("find"))
async def find(m:Message):
 if not await role(m.from_user.id,"user"):return
 try:uid=int(m.text.split()[1])
 except:await m.answer("Пример /find 123");return
 async with S() as s:u=await s.get(User,uid)
 if not u:await m.answer("Не найден.");return
 await m.answer(f"👤 {u.id}\n@{u.username or '-'}\nБаланс {u.balance}\nБлок {u.blocked}",reply_markup=kb([("➕ Баланс","a:add:"+str(uid)),("➖ Баланс","a:sub:"+str(uid))],[("👥 Рефералы","a:refs:"+str(uid)),("⛔ Блок","a:block:"+str(uid))]))
@r.callback_query(F.data.startswith("a:refs:"))
async def admin_refs(c:CallbackQuery):
 if not await role(c.from_user.id,"user"): return
 uid=int(c.data.split(":")[2])
 async with S() as s:
  owner=await s.get(User,uid)
  rows=(await s.scalars(select(User).where(User.referrer_id==uid).order_by(User.created_at.desc()))).all()
 owner_label=f"@{owner.username}" if owner and owner.username else f"ID: {uid}"
 lines="\n".join(f"• @{u.username}" if u.username else f"• ID: {u.id}" for u in rows) or "Нет рефералов."
 await c.message.answer(f"👥 Рефералы пользователя {owner_label}\nКоличество: {len(rows)}\n\n{lines}")

@r.callback_query(F.data.startswith("a:add:")|F.data.startswith("a:sub:"))
async def ab(c:CallbackQuery):
 if not await role(c.from_user.id,"balance"):return
 mode,uid=c.data.split(":")[1:];await c.message.answer(f"/balance {uid} {'+' if mode=='add' else '-'}50")
@r.message(Command("balance"))
async def bc(m:Message):
 if not await role(m.from_user.id,"balance"):return
 try:_,uid,d=m.text.split();uid=int(uid);d=Decimal(d)
 except:await m.answer("Формат /balance ID +50");return
 async with S() as s:u=await s.get(User,uid);u.balance+=d;await ledger(s,uid,d,"manual","Изменение администратором");await s.commit()
 await m.answer("Готово.")
@r.callback_query(F.data.startswith("a:block:"))
async def block(c:CallbackQuery):
 if not await role(c.from_user.id,"user"):return
 async with S() as s:u=await s.get(User,int(c.data.split(":")[2]));u.blocked=not u.blocked;await s.commit()
 await c.message.answer("Статус изменён.")
@r.callback_query(F.data=="a:tickets")
async def ats(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 async with S() as s:rows=(await s.scalars(select(Ticket).where(Ticket.status=="open"))).all()
 for t in rows:await c.message.answer(f"Тикет #{t.id} пользователь {t.user_id}",reply_markup=kb([("💬 Ответить",f"a:reply:{t.id}"),("🔒 Закрыть",f"a:closet:{t.id}")]))
@r.callback_query(F.data.startswith("a:reply:"))
async def ar(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 async with S() as s:await state(s,c.from_user.id,"reply",c.data.split(":")[2]);await s.commit()
 await c.message.answer("Напишите ответ.")
@r.callback_query(F.data.startswith("a:closet:"))
async def ct(c:CallbackQuery):
 if not await role(c.from_user.id,"ticket"):return
 async with S() as s:t=await s.get(Ticket,int(c.data.split(":")[2]));t.status="closed";await s.commit()
 await c.message.answer("Тикет закрыт.")
@r.callback_query(F.data=="a:payout")
async def ap(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 async with S() as s:rows=(await s.scalars(select(Withdrawal).where(Withdrawal.status=="pending"))).all()
 for w in rows:await c.message.answer(f"#{w.id} {w.amount} {w.method}\n{w.destination}",reply_markup=kb([("✅ Выплачено",f"a:paid:{w.id}"),("❌ Отклонить",f"a:rej:{w.id}")]))
@r.callback_query(F.data.startswith("a:paid:")|F.data.startswith("a:rej:"))
async def pd(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 act,wid=c.data.split(":")[1],int(c.data.split(":")[2])
 async with S() as s:
  w=await s.get(Withdrawal,wid)
  if act=="paid":w.status="paid";await ledger(s,w.user_id,-w.amount,"withdraw_paid",f"#{wid}")
  else:w.status="rejected";u=await s.get(User,w.user_id);u.balance+=w.amount;await ledger(s,u.id,w.amount,"withdraw_refund",f"#{wid}")
  await s.commit()
 await c.message.answer("Готово.")
@r.callback_query(F.data.in_({"a:open","a:close"}))
async def toggle(c:CallbackQuery):
 if not await role(c.from_user.id,"payout"):return
 async with S() as s:await setst(s,"payout_manual","open" if c.data=="a:open" else "closed");await s.commit()
 await c.message.answer("Настройка выплат сохранена.")
@r.callback_query(F.data=="a:config")
async def aconfig(c:CallbackQuery):
 if c.from_user.id not in SUPER:return
 await c.message.answer("Настройка без правки кода:\n/config public_channel @channel\n/config public_url https://t.me/...\n/config private_url https://t.me/+...\n/config captcha_text Текст")
@r.message(Command("config"))
async def configcmd(m:Message):
 if m.from_user.id not in SUPER:return
 try:_,key,value=m.text.split(maxsplit=2)
 except:await m.answer("Формат: /config ключ значение");return
 allowed={"public_channel","public_url","private_url","captcha_text"}
 if key not in allowed:await m.answer("Недопустимый ключ.");return
 async with S() as s:await setst(s,key,value);await s.commit()
 await m.answer("Сохранено в PostgreSQL.")
@r.callback_query(F.data=="a:notices")
async def anotices(c:CallbackQuery):
 if not await role(c.from_user.id,"content"):return
 await c.message.answer("Управление важными сообщениями:\n/noticeadd Номер Текст\n/noticelist\n/noticedel ID")
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
 async with S() as s:x=await s.get(Notice,i);await s.delete(x) if x else None;await s.commit()
 await m.answer("Удалено.")

@r.callback_query(F.data=="a:photo")
async def aph(c:CallbackQuery):
 if not await role(c.from_user.id,"content"):return
 async with S() as s:await state(s,c.from_user.id,"photo","");await s.commit()
 await c.message.answer("Отправьте фото с подписью menu, info или help.")
@r.callback_query(F.data.in_({"info","help"}))
async def content(c:CallbackQuery,bot:Bot):
 if not await access(c,bot):return
 async with S() as s:txt=await st(s,"text:"+c.data,c.data);pic=await s.get(Media,"photo:"+c.data)
 if pic:await c.message.answer_photo(pic.file_id,caption=txt)
 else:await c.message.answer(txt)
async def monitor(bot):
 while True:
  try:
   async with S() as s:
    rows=(await s.scalars(select(Reward).where(Reward.status.in_(["hold","eligible"])))).all();now=datetime.now(timezone.utc)
    for q in rows:
     ok=await sub(bot,q.referral_id);q.last_ok=ok
     if not ok:q.status="cancelled"
     elif q.status=="hold" and now>=q.hold_until:q.status="eligible";u=await s.get(User,q.referrer_id);u.balance+=q.amount;await ledger(s,u.id,q.amount,"referral","Подтверждённый реферал")
    await s.commit()
  except Exception:logging.exception("monitor")
  await asyncio.sleep(86400)
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


async def init_db():
    async with eng.begin() as conn:
        await conn.run_sync(B.metadata.create_all)
        await migrate_bigint_columns(conn)
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
