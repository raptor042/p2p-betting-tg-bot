import os
from dotenv import load_dotenv
from datetime import datetime

from enum import Enum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from services.db.db import connect_db
from services.db.users import get_user, set_user, update_user, delete_user
from services.db.fixtures import set_fixture, get_fixture
from services.db.bets import set_bet, update_bet, get_bet
from services.db.pool import set_pool, update_pool, get_pool
from services.db.transactions import set_transaction, update_transaction

from services.apis.flutterwave import init_payment, verify_payment, banks, branches, beneficiary, transfer, transfer_fee, transaction_fee
from services.apis.sports import fixtures

from controllers.crypto.cryptic import _encrypt, _decrypt
from controllers.crypto.keys import loadKeyPair

from constants import CURRENCY_LIST, LEAGUE_IDs, P2P_BET_LIST, NAIJA_BANKS

import logging
from random import randint

logging.basicConfig(format="%(asctime)s -%(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class State(Enum):
    INACTIVE = 0
    OPEN = 1
    LOCKED = 2
    CLOSED = 3
SIGNUP, SETTINGS, END = range(3)
db = None

def random_id(username, type) -> str:
    random_num = "".join([str(randint(0, 9)) for _ in range(10)])

    return f"{username}-{type}-{random_num}"

def end_time(time):
    _time = time[:8]
    pre = int(time[8:10]) + 2
    pro = int(time[10:12]) + 30
    print(time, _time, pre, pro)

    if pro >= 60:
        pro -= 60
        pre += 1
        print(pre, pro)

    if len(str(pre)) == 1:
        pre = f"0{pre}"
        print(pre)

    if int(pre) >= 24:
        diff = pre - 24
        pre = f"0{diff}"

    if pro == 0:
        pro = "00"

    return f"{_time}{pre}{pro}00"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.username)

    _query = { "username" : user.username }
    _user = get_user(db=db, query=_query)

    if _user:
        reply_msg = "Hello <b>{} \U0001F601</b>, Seems you already have an account with us, hence you cannot start this conversation again. if you are having any issues, Enter the command <b>'/help'</b> and contact us.".format(user.username)
        await update.message.reply_html(text=reply_msg)

        return SIGNUP
    else:
        if user.username:
            keyboard = [
                [InlineKeyboardButton("Begin SignUp", callback_data="sign-up")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = "Hello <b>{}</b>\n\n<b>Welcome to P2P-Bet, the home of peer-to-peer betting</b>\n\n<i>This is a platform which seeks to open up a new style of betting. Unlike traditional betting systems which provide odds which are usually stacked against you, P2P-Bet supports and provide free and decentralized system of betting where you can stake bets with your peers in a flexible way. Our motto is simply <b>'No Odds'</b></i> \n\n<strong>P2P-Bet is avaliable only in Nigeria, Ghana, Kenya, Uganda and Tanzania for now, we will soon support other countries and their curencies</strong>".format(user.username)

            await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

            _user = set_user(db=db, value={"username" : user.username})
            print(_user)

            return SIGNUP
        else:
            reply_msg = "Hello <b>{}</b>, Seems you don't have a telegram username, hence you cannot start this conversation again. Please create a username to continue. if you are having any issues, Enter the command <b>'/help'</b> and contact us.".format(user.first_name)
            await update.message.reply_html(text=reply_msg)

            return SIGNUP

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Enter Account Details", callback_data="account")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<strong>Enter the details of your Bank account and other information which would be used for pocessing your cashout; This includes your phone number and email address.</strong>\n\n<i>Make sure your account details are correct else you will have issues with your cashout.</i>\n\n<i>If you encounter any issues or need more clarification, Enter the command <b>'/help'</b>, We would gladly help you through the process</i>"

    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return SIGNUP

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.message.reply_text("Enter your email address")

    return SIGNUP

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Enter your phone number")

    query = { "username" : update.message.from_user.username }
    value = {"$set" : {"email" : update.message.text.strip()}}
    user = update_user(db=db, query=query , value=value)
    print(user)

    return SIGNUP

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["user"] = update.message.from_user.username
    keyboard = []

    for country in CURRENCY_LIST:
        _country = CURRENCY_LIST.index(country)
        keyboard.append([InlineKeyboardButton(f"{country[0]}({country[3]})", callback_data=f"country-{_country}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select your country</b>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    keys = loadKeyPair()
    phone_number = _encrypt(text=update.message.text.strip(), key=keys[0])
    query = { "username" : update.message.from_user.username }
    value = {"$set" : {"phone" : phone_number}}
    user = update_user(db=db, query=query , value=value)
    print(user)

    return SIGNUP

async def bankz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    [_, _country] = query.data.split("-", 1)
    context.user_data["country"] = int(_country)
    country = int(_country)
    print(country)
    bank_list = None

    if country == 0:
        bank_list = NAIJA_BANKS
    else:
        _banks = banks(country=CURRENCY_LIST[country][1])
        bank_list = _banks["banks"]

    user = update_user(db=db, query={"username" : context.user_data["user"]}, value={"$set" : {"country" : f"{CURRENCY_LIST[country][0]}({CURRENCY_LIST[country][1]})"}})
    user = update_user(db=db, query={"username" : context.user_data["user"]}, value={"$set" : {"currency" : f"{CURRENCY_LIST[country][3]}"}})
    print(user)

    keyboard = []

    for bank in bank_list:
        keyboard.append([InlineKeyboardButton(f"{bank['name']}", callback_data=f"bank-{bank['code']}-{CURRENCY_LIST[country][3]}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select your preferred BANK</b>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return SIGNUP

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    [_, code, currency] = query.data.split("-", 2)
    username = context.user_data["user"]
    context.user_data["bank"] = code

    user = update_user(db=db, query={"username" : username}, value={"$set" : {"bank-code" : code}})
    print(user)

    if currency != "NGN":
        banks = context.user_data["banks"]
        id = None

        for bank in banks:
            if bank["code"] == code:
                id = bank["id"]
                break
            else:
                continue

        branch_list = branches(id=id)

        keyboard = []

        for branch in branch_list["branch"]:
            keyboard.append([InlineKeyboardButton(f"{branch['branch_name']}", callback_data=f"branch-{branch['branch_code']}")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your BANK branch</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    else:
        reply_msg = f"<strong>Enter the details of your Bank account name.</strong>\n\n<i>Please when entering your account name use this format; Firstly enter <b>'AccountName:'</b>, followed by your account name and no whitespaces</i>\n\n<i>Make sure you enter your account name in this format else you will have issues with your cashout.</i>"
        await query.message.reply_html(text=reply_msg)

    return SIGNUP

async def branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    [_, code] = query.data.split("-", 1)
    username = context.user_data["user"]

    user = update_user(db=db, query={"username" : username}, value={"$set" : {"branch-code" : code}})
    print(user)

    reply_msg = f"<strong>Enter the details of your Bank account name.</strong>\n\n<i>Please when entering your account name use this format; Firstly enter <b>'AccountName:'</b>, followed by your account name and no whitespaces</i>\n\n<i>Make sure you enter your account name in this format else you will have issues with your cashout.</i>"
    await query.message.reply_html(text=reply_msg)

    return SIGNUP

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    [_, name] = update.message.text.split(":", 1)
    username = context.user_data["user"]
    context.user_data["name"] = name

    user = update_user(db=db, query={"username" : username}, value={"$set" : {"account-name" : name}})
    print(user)

    reply_msg = f"<strong>Enter the details of your Bank account number.</strong>\n\n<i>Please when entering your account number use this format; Firstly enter <b>'AccountNumber:'</b>, followed by your account number and no whitespaces</i>\n\n<i>Make sure you enter your account number in this format else you will have issues with your cashout.</i>"
    await update.message.reply_html(text=reply_msg)

    return SIGNUP

async def number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    [_, number] = update.message.text.split(":", 1)
    username = context.user_data["user"]
    country = context.user_data["country"]

    params = {
        "name" : context.user_data["name"],
        "number" : number,
        "code" : context.user_data["bank"],
        "currency" : CURRENCY_LIST[country][3]
    }
    _beneficiary = beneficiary(params=params)
    print(_beneficiary)

    keys = loadKeyPair()
    account_number = _encrypt(text=number.strip(), key=keys[0])

    user = update_user(db=db, query={"username" : username}, value={"$set" : {"account-number" : account_number}})
    user = update_user(db=db, query={"username" : username}, value={"$set" : { "balance" : "0.00" }})
    user = update_user(db=db, query={"username" : username}, value={"$set" : { "id" : _beneficiary["id"] }})
    print(user)

    keyboard = [
        [InlineKeyboardButton("End", callback_data="end")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<i>Congratulations your account setup is complete.</i>\n\n<b>May the odds always be in your favour</b>\n\n<i>You can always change the details of your account, just Enter the command <b>'/dashboard'</b> to edit your account details.</i>\n\n<i>If you need any help through the process, Enter the command <b>'/help'</b></i>\n\n<b>Click the button below to end our conversation</b>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

    return SIGNUP

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.message.reply_html("See you soon.")

    return ConversationHandler.END

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await query.message.reply_html("See you next time.")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user.username
    context.user_data["user"] = user

    keyboard = [
        [InlineKeyboardButton("Fund Account", callback_data="fund")],
        [InlineKeyboardButton("Check Balance", callback_data=f"balance-{user}")],
        [InlineKeyboardButton("Withdraw Funds", callback_data=f"withdraw-{user}")],
        [InlineKeyboardButton("Edit Account", callback_data="edit")],
        [InlineKeyboardButton("Delete Account", callback_data="delete")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>You can fund your account make changes to initals settings like email, phone number and bank details by clicking the buttons below.</b>\n\n<b>You can also delete your account by clicking the button below.</b>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = get_user(db=db, query={"username" : context.user_data["user"]})
    balance = user["balance"]

    reply_msg = f"<b>Your account balance is {balance}. Enter the amount you would like to withdraw</b>\n\n<i>Please enter this format, ie Firstly enter 'Withdraw:' followed by the amount.</i>"
    await query.message.reply_html(text=reply_msg)

async def withdraw_funds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _amount = update.message.text.split(":", 1)[1]
    _user = update.message.from_user.username

    user = get_user(db=db, query={"username" : _user})
    ref = random_id(username=_user, type="transfer")
    _balance = float(user["balance"])
    balance = _balance - float(_amount)
    print("{:.2f}".format(balance))

    fee = transfer_fee(amount=_amount, currency=user["currency"])
    print(fee)
    amount = float(_amount) - float(fee)
    key = loadKeyPair()
    account_number = _decrypt(data=user["account-number"], key=key[1])
    params = None

    if user["currency"] == "NGN":
        params = {
            "code" : user["bank-code"],
            "number" : account_number,
            "amount" : amount,
            "username" : user["username"],
            "ref" : ref,
            "currency" : user["currency"]
        }
    elif user["currency"] == "KES":
        params = {
            "code" : user["bank-code"],
            "number" : account_number,
            "amount" : amount,
            "username" : user["username"],
            "ref" : ref,
            "currency" : user["currency"],
            "meta" : {
                "sender" : "Chromium Tech Studio",
                "sender_country" : "NG",
                "mobile_number" : "+2348089672675"
            }
        }
    else:
        params = {
            "code" : user["bank-code"],
            "number" : account_number,
            "amount" : amount,
            "username" : user["username"],
            "ref" : ref,
            "currency" : user["currency"],
            "branch" : user["branch-code"],
            "name" : user["account-name"]
        }
    _transfer = transfer(params=params)
    print(_transfer)
    transaction = set_transaction(db=db, value={"type" : "transfer", "user" : _user, "amount" : _amount, "ref" : ref, "id" : _transfer["id"], "completed" : False, "status" : "NEW"})
    print(transaction)

    reply_msg = f"<b>Your withdrawal of {_amount}{user['currency']} has been queued successfully.</b>\n\n<i>You will be charged {fee}{user['currency']} as transfer fee.</i>"
    await update.message.reply_html(text=reply_msg)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = get_user(db=db, query={"username" : context.user_data["user"]})
    balance = user["balance"]

    reply_msg = f"<b>Your account balance is {balance}</b>\n\n<i>If you want to fund your account, enter the command '/dashboard' to access your account dashboard, then you proceed to fund your account</i>"
    await query.message.reply_html(text=reply_msg)

async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    reply_msg = "<b>Fund your account here \U0001f911.</b>\n\n<i>Please enter this format, ie Firstly enter 'Fund:' followed by the amount.</i>"
    await query.message.reply_html(text=reply_msg)

async def fund_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    amount = update.message.text.split(":", 1)[1]

    keyboard = [
        [InlineKeyboardButton("Begin Payment", callback_data=f"payment:{amount}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = f"<b>Proceed to make the payment of {amount}.</b>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_msg = "<i>Seems you help with something</i>\n\n<b>These are some instructions that you should follow to avoid any issue and successfully complete the process of creating your bot:</b>\n<i>1. Firstly to start the bot conversation, enter the command <b>'/start'</b></i>\n<i>2. During the process of entering your account details, instructions are given on how to enter your bank details. Make sure you follow those instructions</i>\n<i>3. During the process of editing your account details, instructions are given on how to enter your new account details</i>\n<i>4. To ensure that your cashout is processed, make sure your account details are correct. If you made any mistakes go to settings by entering the command <b>'/dashboard'</b> and edit your account details</i>\n<i>5. When you are asked to select, please click only one button to choose that option</i>\n\n<b>For more guidance and support:</b>\n<i>Call : 09151984731</i>\n<i>Email : chromiumtechstudios@gmail.com</i>"
    await update.message.reply_html(text=reply_msg)

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Edit Email", callback_data="edit_email")],
        [InlineKeyboardButton("Edit Phone Number", callback_data="edit_phone")],
        [InlineKeyboardButton("Edit Bank", callback_data="edit_bank")],
        [InlineKeyboardButton("Edit Bank Account Name", callback_data="edit_name")],
        [InlineKeyboardButton("Edit Bank Account Number", callback_data="edit_number")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>You can make changes to following settings by clicking the buttons below.</b>\n\n<i>When entering your new credentials, please enter the credentials using the format : <b>'New:ADGGHNGRGJK'</b>. Note, Replace these characters with your actual credentials and No whitespaces between the characters</i>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def edits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "edit_email": 
        reply_msg = "<i>Enter your new email address using the following format:</i>\n\n<b>Must begin with 'New-Email:', followed by your new email address and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_phone":
        reply_msg = "<i>Enter your new phone number using the following format:</i>\n\n<b>Must begin with 'New-PhoneNumber:', followed by your new phone number and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_name":
        reply_msg = "<i>Enter your new bank account name using the following format:</i>\n\n<b>Must begin with 'New-AccountName:', followed by your new account name and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_number":
        reply_msg = "<i>Enter your new bank account number using the following format:</i>\n\n<b>Must begin with 'New-AccountNumber:', followed by your new account number and no whitespaces</b>"
        await query.message.reply_html(text=reply_msg)
    elif query.data == "edit_bank":
        context.user_data["bank_count"] = 0
        keyboard = []

        for country in CURRENCY_LIST:
            _country = CURRENCY_LIST.index(country)
            keyboard.append([InlineKeyboardButton(f"{country[0]}({country[3]})", callback_data=f"country-{_country}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your country</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def edit_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "New-Email:" in update.message.text:
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"email" : update.message.text.split(":", 1)[1].strip()}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your email address have been changed")
    elif "New-PhoneNumber:" in update.message.text:
        key = loadKeyPair()
        phone_number = _encrypt(text=update.message.text.split(":", 1)[1].strip(), key=key[0])
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"phone" : phone_number}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your phone number have been changed")
    if "New-AccountName:" in update.message.text:
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"account-name" : update.message.text.split(":", 1)[1].strip()}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your account name have been changed")
    elif "New-AccountNumber:" in update.message.text:
        key = loadKeyPair()
        account_number = _encrypt(text=update.message.text.split(":", 1)[1].strip(), key=key[0])
        query = { "username" : update.message.from_user.username }
        value = {"$set" : {"account-number" : account_number}}
        user = update_user(db=db, query=query , value=value)
        print(user)

        await update.message.reply_text("Your account number have been changed")

async def edit_banks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    [_, _country] = query.data.split("-", 1)
    context.user_data["country"] = int(_country)
    country = int(_country)

    if country == 1:
        bank_list = NAIJA_BANKS
    else:
        _banks = banks(country=CURRENCY_LIST[country][1])
        bank_list = _banks["banks"]

    user = update_user(db=db, query={"username" : context.user_data["user"]}, value={"$set" : {"country" : f"{CURRENCY_LIST[country][0]}({CURRENCY_LIST[country][1]})"}})
    user = update_user(db=db, query={"username" : context.user_data["user"]}, value={"$set" : {"currency" : f"{CURRENCY_LIST[country][3]}"}})
    print(user)

    keyboard = []

    for bank in bank_list:
        keyboard.append([InlineKeyboardButton(f"{bank['name']}", callback_data=f"bank-{bank['code']}-{CURRENCY_LIST[country][3]}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select your preferred BANK</b>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def edit_bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    [_, code, currency] = query.data.split("-", 2)
    username = context.user_data["user"]

    user = update_user(db=db, query={"username" : username}, value={"$set" : {"bank-code" : code}})
    print(user, code, currency)

    if currency != "NGN":
        banks = context.user_data["banks"]
        id = None

        for bank in banks:
            if bank["code"] == code:
                id = bank["id"]
                break
            else:
                continue

        branch_list = branches(id=id)

        keyboard = []

        for branch in branch_list["branch"]:
            keyboard.append([InlineKeyboardButton(f"{branch['branch_name']}", callback_data=f"edit-branch-{branch['branch_code']}")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your BANK branch</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    else:
        await query.message.reply_text("Your bank have been changed")

async def edit_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    [_, code] = query.data.split("-", 1)
    username = context.user_data["user"]

    user = update_user(db=db, query={"username" : username}, value={"$set" : {"branch-code" : code}})
    print(user)

    await query.message.reply_text("Your bank have been changed")

async def del_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data="del:yes"),
            InlineKeyboardButton("No", callback_data="del:no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("This action is permanent, Are you sure?", reply_markup=reply_markup)

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "del:yes":
        _query = { "username" : query.from_user.username }
        user = delete_user(db=db, query=_query)
        print(user)

        await query.message.reply_text("Account deleted permanently.")
    elif query.data == "del:no":
        await query.message.reply_text("No action has been taken.")

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    types = ["1v1", "FBP"]
    query = { "username" : username }
    user = get_user(db=db, query=query)

    if user:
        if "Date:" in update.message.text:
            time = update.message.text.split(":", 1)[1]
            keyboard = [
                [InlineKeyboardButton("1v1 P2P Betting", callback_data=f"bookdate-{time}-{username}-{types[0]}")],
                [InlineKeyboardButton("FanBasePool P2P Betting", callback_data=f"bookdate-{time}-{username}-{types[1]}")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = f"<b>Hello {username}</b>\n\n<b>Welcome to P2P Betting. There are two betting systems available ie 1v1 and FanBasePool P2P Betting</b>\n\n<i>The 1v1 P2P betting system is the basic system of betting between two peers(Booker and Marquee). A Peer(Booker) makes a prediction and creates/books a bet which is then played by another peer(Marquee). Both Peers wagers against each other.</i>\n\n<i>The FanBasePool P2P betting system is created for the big games in soccer where there are opposing large fanbases. The system is simple, a pool is created for a big match between two teams and multiple people supporting each team wagers a certain amount in the pool. The creator of the pool selects the range of wagers and participants of the pool. The minimum wager in a pool is 1,000 Naira and the minimum amount of paticipants in a pool is 5.</i>"
            await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)
        else:
            keyboard = [
                [InlineKeyboardButton("1v1 P2P Betting", callback_data=f"booking-{username}-{types[0]}")],
                [InlineKeyboardButton("FanBasePool P2P Betting", callback_data=f"booking-{username}-{types[1]}")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = f"<b>Hello {username}</b>\n\n<b>Welcome to P2P Betting. There are two betting systems available ie 1v1 and FanBasePool P2P Betting</b>\n\n<i>The 1v1 P2P betting system is the basic system of betting between two peers(Booker and Marquee). A Peer(Booker) makes a prediction and creates/books a bet which is then played by another peer(Marquee). Both Peers wagers against each other.</i>\n\n<i>The FanBasePool P2P betting system is created for the big games in soccer where there are opposing large fanbases. The system is simple, a pool is created for a big match between two teams and multiple people supporting each team wagers a certain amount in the pool. The creator of the pool selects the range of wagers and participants of the pool. The minimum wager in a pool is 1,000 Naira and the minimum amount of paticipants in a pool is 10.</i>"
            await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    else:
        reply_msg = f"Hello <b>{username}</b>, Seems you do not have an account with us, hence you cannot proceed to booking a bet. Please create an account by entering the command '/start'. This process is important for gathering your bank details smooth for cashout processing. If you are having any issues, Enter the command <b>'/help'</b> and contact us."
        await update.message.reply_html(text=reply_msg)

async def booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    date = datetime.now()
    time = f"{date.strftime('%Y')}{date.strftime('%m')}{date.strftime('%d')}"
    print(date, time)

    [_, username, type] = query.data.split("-", 2)

    game = get_fixture(db=db, query={ "date" : time })

    if game:
        keyboard = []

        for league in LEAGUE_IDs:
            keyboard.append([InlineKeyboardButton(f"{league[0]}", callback_data=f"lg:{type}:{username}:{league[1]}:{league[2]}:{time}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your league</b>\n<i>If you want to see games at future dates, Enter the command '/date' and proceed.</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    else:
        await query.message.reply_text("Give me a second while I gather some data")

        games = fixtures(time)
        value = {
            "date" : f"{time}",
            "premier-league" : games["epl"],
            "laliga" : games["la_liga"],
            "serie-a" : games["seria_a"],
            "bundesliga" : games["bundesliga"],
            "ligue-1" : games["ligue_1"],
            "uefa-champions-league" : games["uefa_champions_league"],
            "uefa-europa-league" : games["uefa_europa_league"]
        }

        _fixtures = set_fixture(db=db, value=value)
        print(_fixtures)

        keyboard = []

        for league in LEAGUE_IDs:
            keyboard.append([InlineKeyboardButton(f"{league[0]}", callback_data=f"lg:{type}:{username}:{league[1]}:{league[2]}:{time}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your league</b>\n<i>If you want to see games at future dates, Enter the command '/date' and proceed.</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    query = { "username" : username }
    user = get_user(db=db, query=query)
    if user:
        reply_msg = "<b>Enter the date for the match you want to book.</b>\n\n<i>Please enter this format, ie Firstly enter 'Date:' followed by the date in this format: 'YYYYMMDD'.</i>\n<b>Example:</b>\n<i>12th August 2023 is written as '20230812'</i>"
        await update.message.reply_html(text=reply_msg)
    else:
        reply_msg = f"Hello <b>{username}</b>, Seems you do not have an account with us, hence you cannot proceed to booking a bet. Please create an account by entering the command '/start'. This process is important for gathering your bank details smooth for cashout processing. If you are having any issues, Enter the command <b>'/help'</b> and contact us."
        await update.message.reply_html(text=reply_msg)

async def booking_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, time, username, type] = query.data.split("-", 3)
    
    date = datetime.now()
    _time = f"{date.strftime('%Y')}{date.strftime('%m')}{date.strftime('%d')}"
    print(date, time, _time)

    if int(time) < int(_time):
        reply_msg = "<b>Cannot retrieve matches on this date.</b>"
        await query.message.reply_html(text=reply_msg)
    elif len(time) > 8 or int(time) > int("20240000"):
        reply_msg = "<b>Cannot retrieve matches on this date.</b>"
        await query.message.reply_html(text=reply_msg)
    else:
        game = get_fixture(db=db, query={ "date" : time })
        if game:
            keyboard = []

            for league in LEAGUE_IDs:
                keyboard.append([InlineKeyboardButton(f"{league[0]}", callback_data=f"lg:{type}:{username}:{league[1]}:{league[2]}:{time}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = "<b>Select your league</b>"
            await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
        else:
            await query.message.reply_text("Give me a second while I gather some data")

            games = fixtures(time)
            value = {
                "date" : f"{time}",
                "premier-league" : games["epl"],
                "laliga" : games["la_liga"],
                "serie-a" : games["seria_a"],
                "bundesliga" : games["bundesliga"],
                "ligue-1" : games["ligue_1"],
                "uefa-champions-league" : games["uefa_champions_league"],
                "uefa-europa-league" : games["uefa_europa_league"]
            }

            _fixtures = set_fixture(db=db, value=value)
            print(_fixtures)

            keyboard = []

            for league in LEAGUE_IDs:
                keyboard.append([InlineKeyboardButton(f"{league[0]}", callback_data=f"lg:{type}:{username}:{league[1]}:{league[2]}:{time}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = "<b>Select your league</b>"
            await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def fixture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    print(query.data.split(':', 5))
    [_, type, username, _league, league_id, time] = query.data.split(':', 5)
    date = datetime.now()
    _time = f"{date.strftime('%Y')}{date.strftime('%m')}{date.strftime('%d')}{date.strftime('%H')}{date.strftime('%M')}{date.strftime('%S')}"
    print(date, _time)

    games = get_fixture(db=db, query={ "date" : time })
    league = games[f"{_league}"]
    print(league)
    
    if league == "None" or league["Events"] == []:
        reply_msg = "<b>There are no games available for this league at the moment.</b>\n\n<i>If you want to see games at future dates, Enter the command '/date' and proceed.</i>"
        await query.message.reply_html(text=reply_msg)
    else:
        keyboard = []
        events = "None"

        for event in league["Events"]:
            event_time = str(event["Esd"])
            event_end_time = end_time(event_time)
            if int(event_end_time) <= int(_time):
                continue
            else:
                events = "All"
                home_team = event["T1"][0]["Nm"]
                away_team =  event["T2"][0]["Nm"]
                eid = event['Eid']
                keyboard.append([InlineKeyboardButton(f"{home_team} Vs {away_team}", callback_data=f"bk:{type}:{eid}:{_league}:{league_id}:{username}:{time}")])

        if events == "All":
            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = "<b>Select your fixture</b>\n<i>If you want to see games at future dates, Enter the command '/date' and proceed.</i>"
            await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
        elif events == "None":
            reply_msg = "<b>There are no games available for this league at the moment.</b>\n\n<i>If you want to see games at future dates, Enter the command '/date' and proceed.</i>"
            await query.message.reply_html(text=reply_msg)

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    date = datetime.now()
    _time = f"{date.strftime('%Y')}{date.strftime('%m')}{date.strftime('%d')}{date.strftime('%H')}{date.strftime('%M')}{date.strftime('%S')}"

    print(query.data.split(":", 6))
    [_, type, eid, league, league_id, username, time] = query.data.split(":", 6)

    games = get_fixture(db=db, query={ "date" : time })
    events = games[f"{league}"]
    match = ""
    event_time = ""

    for event in events["Events"]:
        if event["Eid"] == eid:
            print(event)
            home_team = event["T1"][0]["Nm"]
            away_team =  event["T2"][0]["Nm"]
            match = f"{home_team} Vs {away_team}"
            event_time = str(event["Esd"])
        else:
            continue
    
    event_end_time = end_time(event_time)
    print(event_time, _time, event_end_time)

    if type == "1v1":
        betId = random_id(username=username, type=type)
        print(betId)
        value = {
            "betId" : betId,
            "league-id" : league_id,
            "eid" : eid,
            "match" : match,
            "booker" : username,
            "event-start-time" : event_time,
            "event-end-time" : event_end_time,
            "time-of-creation" : _time,
            "state" : State.INACTIVE.value
        }

        bet = set_bet(db=db, value=value)
        print(bet)

        context.user_data["betId"] = betId

        keyboard = []

        for bets in P2P_BET_LIST:
            keyboard.append([InlineKeyboardButton(f"{bets['name']}", callback_data=f"bets-{bets['name']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your prediction</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif type == "FBP":
        poolId = random_id(username=username, type=type)
        print(poolId)
        value = {
            "poolId" : poolId,
            "league-id" : league_id,
            "eid" : eid,
            "match" : match,
            "creator" : username,
            "event-start-time" : event_time,
            "event-end-time" : event_end_time,
            "time-of-creation" : _time,
            "state" : State.INACTIVE.value
        }

        pool = set_pool(db=db, value=value)
        print(pool)

        context.user_data["poolId"] = poolId

        keyboard = [
            [InlineKeyboardButton("Home Team", callback_data=f"fbp-home")],
            [InlineKeyboardButton("Away Team", callback_data=f"fbp-away")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the team you support.</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def bets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, category] = query.data.split("-", 1)
    betId = context.user_data.get("betId")

    if category == "1X2":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "1X2"}})
        print(bet)

        keyboard = []

        for bets in P2P_BET_LIST[0]["options"]:
            keyboard.append([InlineKeyboardButton(f"{bets['name']}", callback_data=f"1X2-{bets['name']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your prediction</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif category == "GG/NG":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "GG/NG"}})
        print(bet)

        keyboard = []

        for bets in P2P_BET_LIST[1]["options"]:
            keyboard.append([InlineKeyboardButton(f"{bets['name']}", callback_data=f"GG/NG-{bets['name']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your prediction</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif category == "Over/Under":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "Over/Under"}})
        print(bet)

        keyboard = []

        for bets in P2P_BET_LIST[2]["options"]:
            keyboard.append([InlineKeyboardButton(f"{bets['name']}", callback_data=f"Over/Under-{bets['name']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your prediction</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif category == "1st Goal":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "1st Goal"}})
        print(bet)

        keyboard = []

        for bets in P2P_BET_LIST[6]["options"]:
            keyboard.append([InlineKeyboardButton(f"{bets['name']}", callback_data=f"1stGoal-{bets['name']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your prediction</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif category == "Odd/Even":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "Odd/Even"}})
        print(bet)

        keyboard = []

        for bets in P2P_BET_LIST[7]["options"]:
            keyboard.append([InlineKeyboardButton(f"{bets['name']}", callback_data=f"Odd/Even-{bets['name']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your prediction</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif category == "Player to Score":
        options = P2P_BET_LIST[3]['options']
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "Player to Score"}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : "Player to Score"}})
        print(bet)

        reply_msg = f"<b>Enter your prediction of the name of the player to score</b>\n\n<i>Please enter this format, ie Firstly enter 'PlayerToScore:' followed by the name of the player</i>"
        await query.message.reply_html(text=reply_msg)
    elif category == "Correct Score":
        options = P2P_BET_LIST[4]['options']
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "Correct Score"}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : "Correct Score"}})
        print(bet)

        reply_msg = f"<b>Enter your prediction of the correct score</b>\n\n<i>Please enter this format, ie Firstly enter 'CorrectScore:' followed by your prediction of the correct score</i>"
        await query.message.reply_html(text=reply_msg)
    elif category == "Exact Goals":
        options = P2P_BET_LIST[5]['options']
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"category" : "Exact Goals"}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : "Exact Goals"}})
        print(bet)

        reply_msg = f"<b>Enter your prediction of the exact amount of goals to be scored</b>\n\n<i>Please enter this format, ie Firstly enter 'ExactGoals:' followed by your prediction of the exact aamount of goals to be scored.</i>"
        await query.message.reply_html(text=reply_msg)

async def _1x2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, sub_category] = query.data.split("-", 1)
    betId = context.user_data.get("betId")
    options = P2P_BET_LIST[0]['options']

    if sub_category == "1":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[0]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[0]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "X":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[1]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[1]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "2":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[2]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[2]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def gg_ng(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, sub_category] = query.data.split("-", 1)
    betId = context.user_data.get("betId")
    options = P2P_BET_LIST[1]['options']

    if sub_category == "GG":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[0]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[0]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "NG":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[1]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[1]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def over_under(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, sub_category] = query.data.split("-", 1)
    betId = context.user_data.get("betId")
    options = P2P_BET_LIST[2]['options']

    if sub_category == "Over 0.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[0]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[0]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 0.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[1]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[1]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Over 1.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[2]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[2]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 1.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[3]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[3]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    if sub_category == "Over 2.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[4]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[4]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 2.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[5]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[5]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Over 3.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[6]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[6]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 3.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[7]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[7]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Over 4.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[8]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[8]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 4.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[9]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[9]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Over 5.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[10]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[10]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 5.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[11]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[11]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Over 6.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[12]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[12]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Under 6.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[13]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[13]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def _1st_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, sub_category] = query.data.split("-", 1)
    betId = context.user_data.get("betId")
    options = P2P_BET_LIST[6]['options']

    if sub_category == "1":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[0]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[0]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "2":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[1]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[1]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def odd_even(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, sub_category] = query.data.split("-", 1)
    betId = context.user_data.get("betId")
    options = P2P_BET_LIST[7]['options']

    if sub_category == "Odd":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[0]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[0]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif sub_category == "Even":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : sub_category}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"description" : options[1]['description']}})
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquee-options" : options[1]['options']}})
        print(bet)

        keyboard = [
            [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
            [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
            [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def correct_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, score] = update.message.text.split(":", 1)
    betId = context.user_data.get("betId")

    prediction = f"{score} will be the correct score of the match."
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : prediction}})
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"score" : score}})
    print(bet)

    keyboard = [
        [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
        [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
        [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def exact_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, goals] =  update.message.text.split(":", 1)
    betId = context.user_data.get("betId")

    prediction = f"{goals} goals will be scored in the match."
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : prediction}})
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"goals" : goals}})
    print(bet)

    keyboard = [
        [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
        [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
        [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def player_to_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, player] = update.message.text.split(":", 1)
    betId = context.user_data.get("betId")

    prediction = f"{player} will score a goal in the match."
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-bet" : prediction}})
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"player" : player}})
    print(bet)

    keyboard = [
        [InlineKeyboardButton("Equal Wager", callback_data=f"equal")],
        [InlineKeyboardButton("Handicap Wager", callback_data=f"handicap")],
        [InlineKeyboardButton("Reverse Handicap Wager", callback_data=f"reverse_handicap")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select the Wager system for your bet by clicking one of the buttons below.</b>\n\n<i>Equal wager system means that both you, the booker and the marquee must wager equal amounts in Naira</i>\n<i>Handicap wager system means that you, the booker wagers a higher amount in Naira to the marquee's wager. It is graded in ratios ie 2:1 or 3:1</i>\n\n<i>Reverse Handicap wager system means that you, the booker wagers a lower amount in Naira to the marquee's wager. It is graded in ratios ie 1:2 or 1:3</i>"
    await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def fbp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, info] = query.data.split("-", 1)
    poolId = context.user_data.get("poolId")
    print(info)

    pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : {"home" : []}})
    pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : {"away" : []}})
    pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : {"participant-count" : 1}})

    if info == "home":
        pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : {"creator-supports" : "home"}})
        print(pool)
    elif info == "away":
        pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : {"creator-supports" : "away"}})
        print(pool)

    reply_msg = f"<b>Enter your wager for this pool.</b>\n\n<i>Please enter this format, ie Firstly enter 'PoolWager:' followed by your wager amount.</i>"
    await query.message.reply_html(text=reply_msg)

async def equal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    betId = context.user_data.get("betId")
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"system" : "Equal Wager"}})
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "None"}})
    print(bet)

    reply_msg = f"<b>Enter your wager for this bet.</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
    await query.message.reply_html(text=reply_msg)

async def handicap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    info = query.data
    betId = context.user_data.get("betId")
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"system" : "Handicap Wager"}})
    print(bet)

    if info =="handicap:1.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "1.5 : 1"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    elif info == "handicap:2":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "2 : 1"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    elif info =="handicap:2.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "2.5 : 1"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    elif info == "handicap:3":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "3 : 1"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    else:
        keyboard = [
            [InlineKeyboardButton("1.5 : 1", callback_data=f"handicap:1.5")],
            [InlineKeyboardButton("2 : 1", callback_data=f"handicap:2")],
            [InlineKeyboardButton("2.5 : 1", callback_data=f"handicap:2.5")],
            [InlineKeyboardButton("3 : 1", callback_data=f"handicap:3")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your Handicap wager sytem.</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def reverse_handicap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    info = query.data
    betId = context.user_data.get("betId")
    bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"system" : "Reverse Handicap Wager"}})
    print(bet)

    if info =="reverse_handicap:1.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "1 : 1.5"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    elif info =="reverse_handicap:2":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "1 : 2"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    elif info =="reverse_handicap:2.5":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "1 : 2.5"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    elif info =="reverse_handicap:3":
        bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"ratio" : "1 : 3"}})
        print(bet)

        reply_msg = f"<b>Enter your wager for this bet</b>\n\n<i>Please enter this format, ie Firstly enter 'Wager:' followed by your wager amount</i>"
        await query.message.reply_html(text=reply_msg)
    else:
        keyboard = [
            [InlineKeyboardButton("1 : 1.5", callback_data=f"reverse_handicap:1.5")],
            [InlineKeyboardButton("1 : 2", callback_data=f"reverse_handicap:2")],
            [InlineKeyboardButton("1 : 2.5", callback_data=f"reverse_handicap:2.5")],
            [InlineKeyboardButton("1 : 3", callback_data=f"reverse_handicap:3")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Select your Reverse Handicap wager sytem.</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def wager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, wager] = update.message.text.split(":", 1)
    betId = context.user_data.get("betId")
    user = get_user(db=db, query={ "username" : update.message.from_user.username })
    _balance = float(user["balance"])
    balance = _balance - float(wager)

    if int(wager) < 0:
        reply_msg = "<b>Your wager Naira is below the miniumum limit allowed for P2P betting. Please enter a new amount.</b>"
        await update.message.reply_html(text=reply_msg)
    elif float(wager) > _balance:
        reply_msg = f"<b>Your account balance is insufficent.</b>\n\n<b>If you want to fund your account, enter the command '/dashboard' to access your account dashboard, then you proceed to fund your account</b>"
        await update.message.reply_html(text=reply_msg)
    else:
        bet = get_bet(db=db, query={"betId" : betId})
        user = update_user(db=db, query={ "username" : update.message.from_user.username }, value={"$set" : {"balance" : "{:.2f}".format(balance)}})
        _bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"state" : State.OPEN.value}})
        print(bet, _bet)

        if bet["system"] == "Equal Wager":
            bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
            bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : wager}})
            print(bet)
        elif bet["system"] == "Handicap Wager":
            if bet["ratio"] == "1.5 : 1":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) / 1.5))}})
                print(bet)
            elif bet["ratio"] == "2 : 1":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) / 2))}})
                print(bet)
            elif bet["ratio"] == "2.5 : 1":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) / 2.5))}})
                print(bet)
            elif bet["ratio"] == "3 : 1":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) / 3))}})
                print(bet)
        elif bet["system"] == "Reverse Handicap Wager":
            if bet["ratio"] == "1 : 1.5":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) * 1.5))}})
                print(bet)
            elif bet["ratio"] == "1 : 2":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) * 2))}})
                print(bet)
            elif bet["ratio"] == "1 : 2.5":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) * 2.5))}})
                print(bet)
            elif bet["ratio"] == "1 : 3":
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"bookers-wager" : wager}})
                bet = update_bet(db=db, query={ "betId" : betId }, value={"$set" : {"marquees-wager" : str(round(int(wager) * 3))}})
                print(bet)

        keyboard = [
            [InlineKeyboardButton("View Bet Details", callback_data=f"view-1v1")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<i>Congratulations your Bet is now open</i>\n\n<b>May the OddZ always be in your favour</b>\n\n<i>Share your betId and bet details with your peers so they can play and engage. To view your bet details, click the button below.</i>"
        await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def pool_wager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, wager] = update.message.text.split(":", 1)
    poolId = context.user_data.get("poolId")
    print(wager, poolId)

    query = { "username" : update.message.from_user.username }
    _user = get_user(db=db, query=query)
    _balance = float(_user["balance"])
    balance = _balance - float(wager)
    user = {
        "wager" : wager,
        "email" : _user["email"],
        "username" : _user["username"]
    }
    print(user)

    pool = get_pool(db=db, query={"poolId" : poolId})
    print(pool)

    if int(wager) < 0:
        reply_msg = "<b>Your wager is below the miniumum limit allowed for FanBasePool P2P betting. Please enter a new amount.</b>"
        await update.message.reply_html(text=reply_msg)
    elif float(wager) > _balance:
        reply_msg = f"<b>Your account balance is insufficent.</b>\n\n<b>If you want to fund your account, enter the command '/dashboard' to access your account dashboard, then you proceed to fund your account</b>"
        await update.message.reply_html(text=reply_msg)
    else:
        _user = update_user(db=db, query={ "username" : update.message.from_user.username }, value={"$set" : {"balance" : "{:.2f}".format(balance)}})
        _pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : {"state" : State.OPEN.value}})
        print(_pool, _user)

        if pool["creator-supports"] == "home":
            pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$push" : { "home" : user }})
            print(pool)
        elif pool["creator-supports"] == "away":
            pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$push" : { "away" : user }})
            print(pool)

        keyboard = [
            [InlineKeyboardButton("View Pool Details", callback_data=f"view-FBP")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<i>Congratulations your pool is now open</i>\n\n<b>May the OddZ always be in your favour</b>\n\n<i>Share your poolId and pool details with your peers so they can join. To view your pool details, click the button below.</i>"
        await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, _amount] = query.data.split(":", 1)

    _query = { "username" : context.user_data["user"] }
    user = get_user(db=db, query=_query)
    ref = random_id(username=user["username"], type="payment")

    fee = transaction_fee(amount=_amount, currency=user["currency"])
    print(fee)

    payment = init_payment(email=user["email"], amount=_amount, ref=ref, currency=user["currency"])
    print(payment)

    link = payment["uri"]
    transaction = set_transaction(db=db, value={"type" : "payment", "user" : user["username"], "amount" : _amount, "ref" : ref, "uri" : link, "completed" : False, "status" : "NEW"})
    print(transaction)

    keyboard = [
        [InlineKeyboardButton("Paid", callback_data=f"paid:{_amount}:{ref}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = f"<i>Click the link below, you will be redirected to the payment portal where you will make the payment of {_amount}{user['currency']}</i>\n\n<i>You will be charged a fee of {fee}{user['currency']} from the payment gateway (Flutterwave).</i>\n\n<i>Link : {link}</i>\n\n<b>Once you have completed payment you will be redirected back to this chat. Click the button below to confirm payment</b>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, amount, ref] = query.data.split(":", 2)
    _query = { "username" : context.user_data["user"] }
    _user = get_user(db=db, query=_query)
    _balance = float(_user["balance"])
    balance = _balance + float(amount)
    print("{:.2f}".format(balance))

    payment = verify_payment(ref=ref)
    print(payment)

    if payment == "successful":
        user = update_user(db=db, query={ "username" : context.user_data["user"] }, value={"$set" : {"balance" : "{:.2f}".format(balance)}})
        transaction = update_transaction(db=db, query={"ref" : ref}, value={"$set" : {"completed" : True}})
        transaction = update_transaction(db=db, query={"ref" : ref}, value={"$set" : {"status" : "SUCCESSFUL"}})
        print(transaction, user)

        reply_msg = f"<b>You have Successfully funded your account with {amount} Naira.</b>"
        await query.message.reply_html(text=reply_msg)
    else:
        transaction = update_transaction(db=db, query={"ref" : ref}, value={"$set" : {"status" : "FAILED"}})
        print(transaction)

        keyboard = [
            [InlineKeyboardButton("Begin Payment", callback_data=f"payment:{amount}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>Payment not Successful</b>\n\n<i>Kindly repeat the payment procedure to fund your account</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, type] = query.data.split("-", 1)
    poolId = context.user_data.get("poolId")
    betId = context.user_data.get("betId")
    if type == "1v1":
        print(betId)
        bet = get_bet(db=db, query={"betId" : betId})
        print(bet)
        sub = bet["bookers-bet"]
        ratio = bet["ratio"]

        keyboard = [
            [InlineKeyboardButton("Done", callback_data="done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = f"<b>Here are your Bet details</b>\n\n<i>BetID : <a href='#'>{betId}</a></i>\n<i>Match : {bet['match']}</i>\n<i>Category : {bet['category']}</i>\n<i>Booker's Bet : {sub}</i>\n<i>Description : {bet['description']}</i>\n<i>Wager System : {bet['system']}</i>\n<i>Ratio : {ratio}</i>\n<i>Booker's Wager : {bet['bookers-wager']}</i>\n<i>Marquee Options : {bet['marquee-options']}</i>\n<i>Marquee's Wager : {bet['marquees-wager']}</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)
    elif type == "FBP":
        print(poolId)
        pool = get_pool(db=db, query={"poolId" : poolId})
        print(pool)

        keyboard = [
            [InlineKeyboardButton("Done", callback_data="done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = f"<b>Here are your pool details</b>\n\n<i>PoolID : <a href='#'>{poolId}</a></i>\n<i>Match : {pool['match']}</i>\n<i>Particpant-Count : {pool['participant-count']}</i>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def place(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    context.user_data["_username"] = username
    query = { "username" : username }
    user = get_user(db=db, query=query)

    if user:
        reply_msg = "<b>Enter a BetID</b>\n\n<i>Please enter the BetID using this format, firstly enter 'BetID:' then type in the BetID</i>"
        await update.message.reply_html(text=reply_msg)
    else:
        reply_msg = f"Hello <b>{username}</b>, Seems you do not have an account with us, hence you cannot proceed to booking a bet. Please create an account by entering the command '/start'. This process is important for gathering your bank details smooth for cashout processing. If you are having any issues, Enter the command <b>'/help'</b> and contact us."
        await update.message.reply_html(text=reply_msg)

async def place_1v1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, betId] = update.message.text.split(":", 1)
    bet = get_bet(db=db, query={"betId" : betId})
    print(bet, betId)

    if bet['state'] == State.INACTIVE.value:
        reply_msg ="<b>Cannot place this bet because the booker have not made the deposit payment to open the bet</b>"
        await update.message.reply_html(text=reply_msg)
    elif bet['state'] == State.LOCKED.value:
        reply_msg ="<b>Cannot place this bet because the bet is already placed by another marquee.</b>"
        await update.message.reply_html(text=reply_msg)
    elif bet['state'] == State.CLOSED.value:
        reply_msg ="<b>Cannot place this bet because the bet is closed. The match is probably over</b>"
        await update.message.reply_html(text=reply_msg)
    elif bet["state"] == State.OPEN.value:
        context.user_data["_betId"] = betId
        wager = bet["marquees-wager"]

        sub = bet["bookers-bet"]
        ratio = bet["ratio"]

        keyboard = [
            [InlineKeyboardButton("Continue", callback_data=f"continue:{wager}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = f"<b>Here are your Bet details</b>\n\n<i>BetID : {betId}</i>\n<i>Match : {bet['match']}</i>\n<i>Category : {bet['category']}</i>\n<i>Booker's Bet : {sub}</i>\n<i>Description : {bet['description']}</i>\n<i>Wager-System : {bet['system']}</i>\n<i>Ratio : {ratio}</i>\n<i>Booker's Wager : {bet['bookers-wager']}</i>\n<i>Marquee Options : {bet['marquee-options']}</i>\n<i>Marquee's Wager : {bet['marquees-wager']}</i>"
        await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def marquee_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    betId = context.user_data["_betId"]
    bet = get_bet(db=db, query={"betId" : betId})
    options = bet["marquee-options"]
    context.user_data["options"] = options
    print(bet)
    [_, wager] = query.data.split(":", 1)

    keyboard = []

    for option in options:
        keyboard.append([InlineKeyboardButton(f"{option}", callback_data=f"place-1v1:{wager}:{option}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Based on the bookers bet, these are your options</b>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def marquee_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, wager, option] = query.data.split(":", 2)
    username = context.user_data["_username"]
    _query = { "username" : username }
    user = get_user(db=db, query=_query)
    _balance = float(user["balance"])
    balance = _balance - float(wager)

    _betId = context.user_data.get("_betId")
    options = context.user_data["options"]
    print(options, option)
    void_bet = "None"
    for opt in options:
        if opt != option:
            void_bet = opt
        else:
            continue

    if float(wager) > _balance:
        reply_msg = f"<b>Your account balance is insufficent.</b>\n\n<b>If you want to fund your account, enter the command '/dashboard' to access your account dashboard, then you proceed to fund your account</b>"
        await query.message.reply_html(text=reply_msg)
    else:
        user = update_user(db=db, query={ "username" : username }, value={"$set" : {"balance" : "{:.2f}".format(balance)}})

        _query = { "betId" : _betId }
        bet = update_bet(db=db, query=_query , value={"$set" : {"state" : State.LOCKED.value}})
        bet = update_bet(db=db, query=_query , value={"$set" : {"marquees-bet" : option}})
        bet = update_bet(db=db, query=_query , value={"$set" : {"marquee" : context.user_data["_username"]}})
        bet = update_bet(db=db, query=_query , value={"$set" : {"void-bet" : void_bet}})
        print(bet)

        reply_msg = "<i>Congratulations you have placed the bet.</i>\n\n<b>May the OddZ always be in your favour</b>"
        await query.message.reply_html(text=reply_msg)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    context.user_data["_username"] = username
    query = { "username" : username }
    user = get_user(db=db, query=query)

    if user:
        reply_msg = "<b>Enter a PoolID</b>\n\n<i>Please enter the PoolID using this format, firstly enter 'PoolID:' then type in the PoolID</i>"
        await update.message.reply_html(text=reply_msg)
    else:
        reply_msg = f"Hello <b>{username}</b>, Seems you do not have an account with us, hence you cannot proceed to booking a bet. Please create an account by entering the command '/start'. This process is important for gathering your bank details smooth for cashout processing. If you are having any issues, Enter the command <b>'/help'</b> and contact us."
        await update.message.reply_html(text=reply_msg)

async def join_fbp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, poolId] = update.message.text.split(":", 1)
    pool = get_pool(db=db, query={"poolId" : poolId})
    print(pool, poolId)

    if pool['state'] == State.INACTIVE.value:
        reply_msg ="<b>Cannot place this pool because the booker have not made the deposit payment to open the pool</b>"
        await update.message.reply_html(text=reply_msg)
    elif pool['state'] == State.LOCKED.value:
        reply_msg ="<b>Cannot place this pool because the pool is already locked. The match has probably started.</b>"
        await update.message.reply_html(text=reply_msg)
    elif pool['state'] == State.CLOSED.value:
        reply_msg ="<b>Cannot place this pool because the pool is closed. The match is probably over.</b>"
        await update.message.reply_html(text=reply_msg)
    elif pool["state"] == State.OPEN.value:
        context.user_data["_poolId"] = poolId

        keyboard = [
            [InlineKeyboardButton("Continue", callback_data="join-FBP")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = f"<b>Here are your pool details</b>\n\n<i>PoolID : {poolId}</i>\n<i>Match : {pool['match']}</i>\n<i>Particpant-Count : {pool['participant-count']}</i>"
        await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def join_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Home Team", callback_data=f"join-home")],
        [InlineKeyboardButton("Away Team", callback_data=f"join-away")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_msg = "<b>Select the team you support.</b>"
    await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

async def join_wager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    [_, support] = query.data.split("-", 1)
    context.user_data["support"] = support

    reply_msg ="<b>Enter your wager.</b>\n\n<i>Please enter this format, ie Firstly enter 'JoinPoolWager:' followed by your wager amount.</i>"
    await query.message.reply_html(text=reply_msg)

async def join_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    [_, wager] = update.message.text.split(":", 1)
    poolId = context.user_data.get("_poolId")

    pool = get_pool(db=db, query={"poolId" : poolId})
    print(pool)

    support = context.user_data["support"]
    _query = { "username" : context.user_data["_username"] }
    user = get_user(db=db, query=_query)
    _balance = float(user["balance"])
    balance = _balance - float(wager)
    user = {
        "wager" : wager,
        "email" : user["email"],
        "username" : user["username"]
    }
    print(user)
    pool = get_pool(db=db, query={"poolId" : poolId})
    print(pool, poolId)
    count = pool["participant-count"]

    if int(wager) < 1000:
        reply_msg = "<b>Your wager is below the minimum requirement for FanBasePool P2P Betting. Please enter a new amount.</b>"
        await update.message.reply_html(text=reply_msg)
    elif float(wager) > _balance:
        reply_msg = f"<b>Your account balance is insufficent.</b>\n\n<b>If you want to fund your account, enter the command '/dashboard' to access your account dashboard, then you proceed to fund your account</b>"
        await update.message.reply_html(text=reply_msg)
    else:
        _user = update_user(db=db, query={ "username" : context.user_data["_username"] }, value={"$set" : {"balance" : "{:.2f}".format(balance)}})
        print(_user)

        if support == "home":
            pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$push" : { "home" : user }})
            print(pool)
        elif support == "away":
            pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$push" : { "away" : user }})
            print(pool)

        pool = update_pool(db=db, query={ "poolId" : poolId }, value={"$set" : { "participant-count" : count + 1 }})
        print(pool)

        reply_msg = "<i>Congratulations you have joined the pool</i>\n\n<b>May the OddZ always be in your favour</b>\n\n<i>Share the poolId and pool details with your peers so they can join.</i>"
        await update.message.reply_html(text=reply_msg)

def main() -> None:
    global db
    db = connect_db(uri=MONGO_URI)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SIGNUP: [
                CallbackQueryHandler(signup, pattern="^sign-up$"),
                CallbackQueryHandler(account, pattern="^account$"),
                MessageHandler(filters.Regex(".com$"), email),
                MessageHandler(filters.Regex("^0(7|8|9)\d{9}"), phone),
                CallbackQueryHandler(bankz, pattern="^country-"),
                CallbackQueryHandler(bank, pattern="^bank-"),
                CallbackQueryHandler(branch, pattern="^branch-"),
                MessageHandler(filters.Regex("^AccountName:"), name),
                MessageHandler(filters.Regex("^AccountNumber:"), number),
            ]
        },
        fallbacks=[CallbackQueryHandler(end, pattern="^end$")]
    )
    dashboard_handler = CommandHandler("dashboard", dashboard)
    help_handler = CommandHandler("help", help)
    fund_handler = CallbackQueryHandler(fund, pattern="^fund$")
    balance_handler = CallbackQueryHandler(balance, pattern="^balance-")
    fund_account_handler = MessageHandler(filters.Regex("^Fund:"), fund_account)
    withdraw_handler = CallbackQueryHandler(withdraw, pattern="^withdraw-")
    withdraw_funds_handler = MessageHandler(filters.Regex("^Withdraw:"), withdraw_funds)
    edit_handler = CallbackQueryHandler(edit, pattern="^edit$")
    done_handler = CallbackQueryHandler(done, pattern="^done$")
    edits_handler = CallbackQueryHandler(edits, pattern="^edit_")
    banks_handler = CallbackQueryHandler(edit_banks, pattern="^country-")
    bank_handler = CallbackQueryHandler(edit_bank, pattern="^edit:bank-")
    branch_handler = CallbackQueryHandler(edit_branch, pattern="^edit-branch-")
    edit_account_handler= MessageHandler(filters.Regex("^New-"), edit_account)
    del_handler = CallbackQueryHandler(del_account, pattern="^delete$")
    delete_handler = CallbackQueryHandler(delete_account, pattern="^del:")
    book_handler = CommandHandler("book", book)
    date_handler = CommandHandler("date", date)
    book_date_handler = MessageHandler(filters.Regex("^Date:"), book)
    booking_handler = CallbackQueryHandler(booking, pattern="^booking-")
    booking_by_date_handler = CallbackQueryHandler(booking_by_date, pattern="^bookdate-")
    fixture_handler = CallbackQueryHandler(fixture, pattern="^lg:")
    create_handler = CallbackQueryHandler(create, pattern="^bk:")
    bets_handler = CallbackQueryHandler(bets, pattern="^bets-")
    _1x2_handler = CallbackQueryHandler(_1x2, pattern="^1X2-")
    gg_ng_handler = CallbackQueryHandler(gg_ng, pattern="^GG/NG-")
    over_under_handler = CallbackQueryHandler(over_under, pattern="^Over/Under-")
    _1st_goal_handler = CallbackQueryHandler(_1st_goal, pattern="^1stGoal-")
    odd_even_handler = CallbackQueryHandler(odd_even, pattern="^Odd/Even-")
    correct_score_handler = MessageHandler(filters.Regex("^CorrectScore:"), correct_score)
    exact_goals_handler = MessageHandler(filters.Regex("^ExactGoals:"), exact_goals)
    pts_handler = MessageHandler(filters.Regex("^PlayerToScore:"), player_to_score)
    equal_handler = CallbackQueryHandler(equal, pattern="^equal")
    handicap_handler = CallbackQueryHandler(handicap, pattern="^handicap")
    reverse_handler = CallbackQueryHandler(reverse_handicap, pattern="^reverse_handicap")
    wager_handler = MessageHandler(filters.Regex("^Wager:"), wager)
    payment_handler = CallbackQueryHandler(payment, pattern="^payment:")
    paid_handler = CallbackQueryHandler(paid, pattern="^paid:")
    view_handler = CallbackQueryHandler(view, pattern="^view-")
    fbp_handler = CallbackQueryHandler(fbp, pattern="^fbp-")
    pool_wager_handler = MessageHandler(filters.Regex("^PoolWager:"), pool_wager)
    place_handler = CommandHandler("place", place)
    place_bet_handler = MessageHandler(filters.Regex("^BetID:"), place_1v1)
    marquee_options_handler = CallbackQueryHandler(marquee_options, pattern="^continue:")
    marquee_payment_handler = CallbackQueryHandler(marquee_payment, pattern="^place-1v1:")
    join_handler = CommandHandler("join", join)
    join_fbp_handler = MessageHandler(filters.Regex("^PoolID:"), join_fbp)
    join_support_handler = CallbackQueryHandler(join_support, pattern="^join-FBP$")
    join_wager_handler = CallbackQueryHandler(join_wager, pattern="^join-")
    join_payment_handler = MessageHandler(filters.Regex("^JoinPoolWager:"), join_payment)

    app.add_handler(conv_handler)
    app.add_handler(dashboard_handler)
    app.add_handler(fund_handler)
    app.add_handler(balance_handler)
    app.add_handler(fund_account_handler)
    app.add_handler(help_handler)
    app.add_handler(done_handler)
    app.add_handler(edit_handler)
    app.add_handler(edits_handler)
    app.add_handler(edit_account_handler)
    app.add_handler(withdraw_handler)
    app.add_handler(withdraw_funds_handler)
    app.add_handler(banks_handler)
    app.add_handler(bank_handler)
    app.add_handler(branch_handler)
    app.add_handler(delete_handler)
    app.add_handler(del_handler)
    app.add_handler(book_handler)
    app.add_handler(date_handler)
    app.add_handler(book_date_handler)
    app.add_handler(booking_handler)
    app.add_handler(booking_by_date_handler)
    app.add_handler(fixture_handler)
    app.add_handler(create_handler)
    app.add_handler(bets_handler)
    app.add_handler(_1x2_handler)
    app.add_handler(gg_ng_handler)
    app.add_handler(over_under_handler)
    app.add_handler(_1st_goal_handler)
    app.add_handler(odd_even_handler)
    app.add_handler(correct_score_handler)
    app.add_handler(exact_goals_handler)
    app.add_handler(pts_handler)
    app.add_handler(equal_handler)
    app.add_handler(handicap_handler)
    app.add_handler(reverse_handler)
    app.add_handler(wager_handler)
    app.add_handler(payment_handler)
    app.add_handler(paid_handler)
    app.add_handler(view_handler)
    app.add_handler(fbp_handler)
    app.add_handler(pool_wager_handler)
    app.add_handler(place_handler)
    app.add_handler(place_bet_handler)
    app.add_handler(marquee_options_handler)
    app.add_handler(marquee_payment_handler)
    app.add_handler(join_handler)
    app.add_handler(join_fbp_handler)
    app.add_handler(join_support_handler)
    app.add_handler(join_wager_handler)
    app.add_handler(join_payment_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()