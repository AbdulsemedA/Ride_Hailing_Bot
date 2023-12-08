import asyncio
from datetime import datetime, timedelta
import logging
import random
import sys

import redis
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    CallbackQuery,
    InlineKeyboardButton
)

# my token 
API_TOKEN = '6650141775:AAFBHVWRKyP-V9icr7TH1Se55gmwEuvfukA'

# redis connection
REDIS_CLOUD_HOST = 'redis-12770.c274.us-east-1-3.ec2.cloud.redislabs.com'
REDIS_CLOUD_PORT = 12770
REDIS_CLOUD_PASSWORD = 'viO8MRnsgS8D1MeA9cHx6r3s08Tc2qg9'

redis_conn = redis.StrictRedis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    decode_responses=True,
    )

form_router = Router()

class Form(StatesGroup):
    Register = State()
    Contact_info = State()
    Role = State()
    EditFullname = State()
    Menu_Passenger = State()
    Menu_Driver = State()
    Book = State()
    BookLocation = State()
    BookDestination = State()
    DriverStatus = State()
    RideComplete = State()
    RideAccept = State()
    DriverReview = State()
    PassengerReview = State()
    Rating = State()


@form_router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_key = f"user:{user_id}"

    if not redis_conn.exists(user_key):
        menu_Passenger = ReplyKeyboardMarkup(resize_keyboard=True,
            keyboard=[[KeyboardButton(text="Register")]])
        await state.set_state(Form.Register)
        await message.answer("Welcome to the Ride Hailing bot!", reply_markup=menu_Passenger)
    else:
        menu_Passenger = get_menu_Passenger_markup()
        menu_Driver = get_menu_Driver_markup()

        user_data = redis_conn.hgetall(user_key)

        if user_data.get('role') == "driver":
            await message.answer(f"Welcome back, {user_data['name']}! What would you like to do today?", reply_markup=menu_Driver)
            await state.set_state(Form.Menu_Driver)
        else:
            await message.answer(f"Welcome back, {user_data['name']}! What would you like to do today?", reply_markup=menu_Passenger)
            await state.set_state(Form.Menu_Passenger)

@form_router.message(Form.Register, F.text.casefold() == "register")
async def process_Contact_info(message: Message, state: FSMContext):
    await state.set_state(Form.Contact_info)
    Contact = ReplyKeyboardMarkup(resize_keyboard=True,
        keyboard=[[KeyboardButton(text="Share Contact", request_contact=True)]])
    await message.answer("please share you contact info:", reply_markup=Contact)


@form_router.message(Form.Contact_info)
async def process_Contact_info(message: Message, state: FSMContext):
    name = phone = ''
    if message.contact and message.contact.phone_number:
        if message.contact.first_name:
            name = message.contact.first_name
        if message.contact.last_name:
            name += " " + message.contact.last_name
        phone = message.contact.phone_number

    await state.update_data(name=name, phone=phone)
    await state.set_state(Form.Role)
    menu_Passenger = ReplyKeyboardMarkup(resize_keyboard=True,
        keyboard=[
                    [KeyboardButton(text="Driver")],
                    [KeyboardButton(text="Passenger")]
                ])
    await message.answer("Great! Lastly, please specify your role..", reply_markup=menu_Passenger)

    
@form_router.message(Form.Role, F.text.casefold() == "driver")
async def process_role(message: Message, state: FSMContext):
    await state.update_data(role='driver')
    user_data = await state.get_data()

    await register_user(message.from_user.id, user_data)
    await state.clear()
    await message.answer("Registration successful! You can now use the /start command to access the bot features.")


@form_router.message(Form.Role, F.text.casefold() == "passenger")
async def process_role(message: Message, state: FSMContext):
    await state.update_data(role='passenger')
    user_data = await state.get_data()

    await register_user(message.from_user.id, user_data)
    await state.clear()
    await message.answer("Registration successful! You can now use the /start command to access the bot features.")


async def register_user(id, data):
    user_key = f"user:{id}"
    name = data['name']
    phone = data['phone']
    role = data['role']
    redis_conn.hset(user_key, mapping= {
        'id': id,
        "name": name,
        "phone": phone,
        "role": role,
        "status": "available"
        })


###########################################
# Menus
###########################################

def get_menu_Passenger_markup():
    menu_Passenger = ReplyKeyboardMarkup(resize_keyboard=True,
        keyboard=[
                    [KeyboardButton(text="Book Ride")],
                    [KeyboardButton(text="Cancel Book")],
                    [KeyboardButton(text="View Book History")],
                    [KeyboardButton(text="Edit Profile")],
                    [KeyboardButton(text="Review")]
                ])
    return menu_Passenger

def get_menu_Driver_markup():
    menu_Driver = ReplyKeyboardMarkup(resize_keyboard=True,
        keyboard=[
                    [KeyboardButton(text="List Books")],
                    [KeyboardButton(text="Active Books")],
                    [KeyboardButton(text="Set Status")],
                    [KeyboardButton(text="View Book History")],
                    [KeyboardButton(text="Edit Profile")],
                    [KeyboardButton(text="Review")]
                ])
    return menu_Driver

def get_rating_markup():
    rating = ReplyKeyboardMarkup(resize_keyboard=True,
        keyboard=[
                    [KeyboardButton(text="1")],
                    [KeyboardButton(text="2")],
                    [KeyboardButton(text="3")],
                    [KeyboardButton(text="4")],
                    [KeyboardButton(text="5")]
                ]) 
    return rating

def get_instant_alert_markup(book_id):
    menu = InlineKeyboardBuilder()
    menu.add(InlineKeyboardButton(text="Accept", callback_data=f"accept:{book_id}"))
    menu.add(InlineKeyboardButton(text="Cancel", callback_data="cancel_instant"))
    menu = menu.as_markup()
    return menu

#############################################
# Edit profile
#############################################
def get_edit_profile_markup():
    menu = InlineKeyboardBuilder()
    menu.add(InlineKeyboardButton(text="Full name", callback_data="full name"))
    menu.add(InlineKeyboardButton(text="Role", callback_data="role"))
    menu = menu.as_markup()
    return menu


@form_router.message(Form.Menu_Passenger, F.text.casefold() == "edit profile")
async def edit_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_key = f"user:{user_id}"
    
    if redis_conn.exists(user_key):
        await message.answer("You are about to edit your profile. Please choose what you want to edit:",
                             reply_markup=get_edit_profile_markup())
    else:
        await message.answer("You need to register first. Use /start to register.")


@form_router.message(Form.Menu_Driver, F.text.casefold() == "edit profile")
async def edit_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_key = f"user:{user_id}"
    
    if redis_conn.exists(user_key):
        await message.answer("You are about to edit your profile. Please choose what you want to edit:",
                             reply_markup=get_edit_profile_markup())
    else:
        await message.answer("You need to register first. Use /start to register.")


@form_router.callback_query(lambda c: c.data in ["full name", "role"])
async def process_profile(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "full name":
        await callback_query.message.answer("please provide your full name.")
        await state.set_state(Form.EditFullname)
    elif callback_query.data == "role":
        role = ''
        U_id = callback_query.from_user.id
        user_key = f"user:{U_id}"
        user_data = redis_conn.hgetall(user_key)
        if user_data.get('role') == "driver":
            role = "passenger"
        else:
            role = "driver"
        redis_conn.hset(user_key, "role", role)
        await state.clear()
        books = redis_conn.keys("book:*")
        if books:
            for book in books:
                book_data = redis_conn.hgetall(book)
                print(book_data)
                if book_data.get('passenger_id') == str(U_id) or book_data.get('driver_id') == str(U_id):
                    print('deleting book')
                    redis_conn.delete(book)
        menu = ''
        if redis_conn.hget(user_key, "role") == "driver":
            await state.set_state(Form.Menu_Driver)
            menu = get_menu_Driver_markup()
        else:
            await state.set_state(Form.Menu_Passenger)
            menu = get_menu_Passenger_markup()
        await callback_query.message.answer(f"Your role has been updated to {role}. Your previous books history has been deleted.", reply_markup=menu)


@form_router.message(Form.EditFullname)
async def process_Contact_info(message: Message, state: FSMContext):
    Contact_info = message.text.strip()
    U_id = message.from_user.id
    user_key = f"user:{U_id}"
    redis_conn.hset(user_key, "name", Contact_info)
    await state.clear()
    menu = ''
    if redis_conn.hget(user_key, "role") == "driver":
        await state.set_state(Form.Menu_Driver)
        menu = get_menu_Driver_markup()
    else:
        await state.set_state(Form.Menu_Passenger)
        menu = get_menu_Passenger_markup()
    await message.answer("Your full name has been updated.", reply_markup=menu)
    

###################################
# Booking - Passenger
###################################

@form_router.message(Form.Menu_Passenger, F.text.casefold() == "book ride")
async def book(message: Message, state: FSMContext):
    await state.set_state(Form.BookLocation)
    await message.answer("Please specify your location:")

@form_router.message(Form.BookLocation)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location = message.text.strip())
    await state.set_state(Form.BookDestination)
    await message.answer("Please specify your destination:")


@form_router.message(Form.BookDestination)
async def process_destination(message: Message, state: FSMContext):
    await state.update_data(destination=message.text.strip())
    menu_confirm= InlineKeyboardBuilder()
    menu_confirm.add(InlineKeyboardButton(text="Confirm", callback_data="confirm"))
    menu_confirm.add(InlineKeyboardButton(text="Cancel", callback_data="cancel"))
    menu_confirm = menu_confirm.as_markup()
    await message.answer("Please confirm your booking:", reply_markup=menu_confirm)
    

@form_router.callback_query(lambda c: c.data in ["confirm", "cancel"])
async def process_callback_button(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "confirm":
        await callback_query.message.answer("Your booking has been confirmed!")
        await state.set_state(Form.Menu_Passenger)
        menu = get_menu_Passenger_markup()
        res = await estimate_time_distance()
        await callback_query.message.answer(f"Estimated distance: {res[0]}")
        await callback_query.message.answer(f"Estimated arrival time: {res[1]}", reply_markup=menu)

        data = await state.get_data()
        store_key = "metric"
        store = redis_conn.hgetall(store_key)
        last_book_id = int(store.get("last_book_id", 0))
        last_book_id += 1
        book_key = f"book:{last_book_id}"

        redis_conn.hset(book_key, mapping = {
                "location": data["location"],
                "destination": data["destination"],
                "book_id": last_book_id,
                "status": "pending",
                "passenger_id": callback_query.from_user.id,
                "driver_id": 0
                })
        redis_conn.hset(store_key, mapping={'last_book_id': last_book_id})

        drivers = await get_all_drivers()
        bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
        for driver_id in drivers:
            await bot.send_message(chat_id=driver_id, text="New ride alert! Someone has booked a ride.", reply_markup=get_instant_alert_markup(last_book_id))
    else:
        await state.set_state(Form.Menu_Passenger)
        menu = get_menu_Passenger_markup()
        await callback_query.message.answer("Your booking has been cancelled!", reply_markup=menu)
  

@form_router.message(Form.Menu_Passenger, F.text.casefold() == "cancel book")
async def process_cancel(message: Message, state: FSMContext):
    u_id = message.from_user.id
    books = redis_conn.keys("book:*")
    menu = get_menu_Passenger_markup()
    await state.set_state(Form.Menu_Passenger)
    if len(books) == 0:
        await message.answer("You didn't have any books.", reply_markup=menu)
    else:
        found = False
        bok = ''
        for bk in books:
            book_data = redis_conn.hgetall(bk)
            if book_data.get('passenger_id') == str(u_id) and (book_data.get('status') == 'pending' or book_data.get('status') == 'accepted'):
                if book_data.get('status') == 'accepted':
                    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
                    await bot.send_message(chat_id=book_data.get('driver_id'), text="Your ride has been cancelled. please check your active books.")
                found = True
                bok = bk
                break

        if not found:
            await message.answer("You didn't have any active or pending books.", reply_markup=menu)
        else:
            redis_conn.delete(bok)
            await message.answer("Your booking has been cancelled!", reply_markup=menu)


###################################
# see all books - Driver
###################################

@form_router.message(Form.Menu_Driver, F.text.casefold() == "list books")
async def list_books(message: Message, state: FSMContext):
    books = redis_conn.keys("book:*")
    menu = get_menu_Driver_markup()
    id = message.from_user.id
    user_key = f"user:{id}"
    user_data = redis_conn.hgetall(user_key)
    if user_data.get('status') == "not available":
        await state.set_state(Form.Menu_Driver)
        await message.answer("Please set your status to available first.", reply_markup=menu)
    elif len(books) == 0:
        await state.set_state(Form.Menu_Driver)
        await message.answer("There are no books at the moment.", reply_markup=menu)
    else:
        Keys = []
        for book in books:
            book_data = redis_conn.hgetall(book)
            button = KeyboardButton(text=f"Book Id: {book_data['book_id']}\nLocation: {book_data['location']}\nDestination: {book_data['destination']}")
            if book_data['status'] == "pending":
                Keys.append(button)
        keyBoard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[Keys])
        if len(Keys) == 0:
            await message.answer("There are no books at the moment.")
        else:
            await message.answer("Here are the list of books:", reply_markup=keyBoard)
            await state.set_state(Form.RideAccept)


###################################
# set status - Driver
###################################

@form_router.message(Form.Menu_Driver, F.text.casefold() == "set status")
async def set_status(message: Message, state: FSMContext):
    menu_Driver = ReplyKeyboardMarkup(resize_keyboard=True,
        keyboard=[
                    [KeyboardButton(text="Available")],
                    [KeyboardButton(text="Not Available")]
                ])
    await message.answer("Please set your status:", reply_markup=menu_Driver)
    await state.set_state(Form.DriverStatus)


@form_router.message(Form.DriverStatus, F.text.casefold() == "available")
async def set_status(message: Message, state: FSMContext):
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    await message.answer("Your status has been set to available.", reply_markup=menu)
    id = message.from_user.id
    user_key = f"user:{id}"
    redis_conn.hset(user_key, "status", "available")

@form_router.message(Form.DriverStatus, F.text.casefold() == "not available")
async def set_status(message: Message, state: FSMContext):
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    await message.answer("Your status has been set to not available.", reply_markup=menu)
    id = message.from_user.id
    user_key = f"user:{id}"
    redis_conn.hset(user_key, "status", "not available")



###################################
# see active books - Driver
###################################

@form_router.message(Form.Menu_Driver, F.text.casefold() == "active books")
async def list_books(message: Message, state: FSMContext):
    books = redis_conn.keys("book:*")
    menu = get_menu_Driver_markup()
    id = message.from_user.id
    user_key = f"user:{id}"
    user_data = redis_conn.hgetall(user_key)

    if user_data.get('status') == "not available":
        await state.set_state(Form.Menu_Driver)
        await message.answer("Please set your status to available first.", reply_markup=menu)
    elif len(books) == 0:
        await state.set_state(Form.Menu_Driver)
        await message.answer("There are no books at the moment.", reply_markup=menu)
    else:
        Keys = []
        for book in books:
            book_data = redis_conn.hgetall(book)
            button = KeyboardButton(text=f"Book Id: {book_data['book_id']}\nLocation: {book_data['location']}\nDestination: {book_data['destination']}")
            if book_data['status'] == "accepted" and book_data['driver_id'] == str(message.from_user.id):
                Keys.append(button)
        keyBoard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[Keys])
        if len(Keys) == 0:
            await message.answer("There are no active books at the moment.")
        else:
            await message.answer("Here are the list of active books waiting for you:", reply_markup=keyBoard)
            await state.set_state(Form.RideComplete)


###################################
# accept instant rides
###################################
@form_router.callback_query(lambda c: c.data.startswith("accept:"))
async def instant_book(callback_query: CallbackQuery, state: FSMContext):
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    booking_id = callback_query.data.split(":")[1]
    book_key = f"book:{booking_id}"
    booking_details = redis_conn.hgetall(book_key)
    if booking_details['status'] == 'accepted':
        await callback_query.message.answer("Ride already accepted by other driver.", reply_markup=menu)
    else:
        await callback_query.message.answer("You have accepted the ride!", reply_markup=menu)
        bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
        id = callback_query.from_user.id
        pass_id = booking_details['passenger_id']
        redis_conn.hset(book_key, 'status', 'accepted')
        redis_conn.hset(book_key, 'driver_id', id)
        await bot.send_message(chat_id=pass_id, text="Your ride has been accepted. Please wait for the driver to arrive.")
    
###################################
# cancel instant ride
###################################

@form_router.callback_query(lambda c: c.data.startswith("cancel_instant"))
async def instant_book(callback_query: CallbackQuery, state: FSMContext):
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    await callback_query.message.answer("Great call, No need to rush!", reply_markup=menu)

###################################
# accept ride - Driver
###################################
@form_router.message(Form.RideAccept)
async def process_accept(message: Message, state: FSMContext):
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    id = message.from_user.id
    await message.answer("You have accepted the ride!", reply_markup=menu)
    book_id = message.text.split("\n")[0].split(":")[1].strip()
    book_key = f"book:{book_id}"
    print("book key", book_key)
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    book = redis_conn.hgetall(book_key)
    pass_id = book['passenger_id']
    redis_conn.hset(book_key, 'status', 'accepted')
    redis_conn.hset(book_key, 'driver_id', id)
    await bot.send_message(chat_id=pass_id, text="Your ride has been accepted. Please wait for the driver to arrive.")


###################################
# complete book - Driver
###################################

@form_router.message(Form.RideComplete)
async def process_complete(message: Message, state: FSMContext):
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    await message.answer("Thank you for riding with us! We hope to see you again soon.", reply_markup=menu)
    book_id = message.text.split("\n")[0].split(":")[1].strip()
    book_key = f"book:{book_id}"
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    book = redis_conn.hgetall(book_key)
    passenger_id = book["passenger_id"]
    redis_conn.hset(book_key, 'status', 'completed')
    await bot.send_message(chat_id=passenger_id, text="Your ride has been completed. Thank you for riding with us!")



####################################
# Review Drivers
####################################

@form_router.message(Form.Menu_Passenger, F.text.casefold() == "review")
async def review(message: Message, state: FSMContext):
    drivers = await get_all_drivers()
    Key = []
    for driver_id in drivers:
        user_key = f"user:{driver_id}"
        user_data = redis_conn.hgetall(user_key)
        Key.append(KeyboardButton(text=f"Driver Id: {driver_id}\nName: {user_data['name']}\nPhone: {user_data['phone']}"))
    
    if len(Key) == 0:
        menu = get_menu_Passenger_markup()
        await state.set_state(Form.Menu_Passenger)
        await message.answer("There are no drivers at the moment.", reply_markup=menu)
    else:
        keyBoard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[Key])
        await message.answer("Please choose a driver to review:", reply_markup=keyBoard)
        await state.set_state(Form.DriverReview)
    
@form_router.message(Form.Menu_Driver, F.text.casefold() == "review")
async def review(message: Message, state: FSMContext):
    passengers = await get_all_passengers()
    Key = []
    for passenger_id in passengers:
        user_key = f"user:{passenger_id}"
        user_data = redis_conn.hgetall(user_key)
        Key.append(KeyboardButton(text=f"Passenger Id: {passenger_id}\nName: {user_data['name']}\nPhone: {user_data['phone']}"))
    
    if len(Key) == 0:
        menu = get_menu_Driver_markup()
        await state.set_state(Form.Menu_Driver)
        await message.answer("There are no passengers at the moment.", reply_markup=menu)
    else:
        keyBoard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[Key])
        await message.answer("Please choose a passenger to review:", reply_markup=keyBoard)
        await state.set_state(Form.PassengerReview)


@form_router.message(Form.DriverReview)
async def process_review(message: Message, state: FSMContext):
    rating = get_rating_markup()
    reviewee_id = message.text.split("\n")[0].split(":")[1].strip()
    await state.update_data(reviewee = reviewee_id)
    if redis_conn.exists(f"rating:{message.from_user.id}:{reviewee_id}"):
        menu = ''
        user_key = f'user:{message.from_user.id}'
        user_data = redis_conn.hgetall(user_key)
        await state.clear()
        
        if user_data.get('role') == "driver":
            menu = get_menu_Driver_markup()
            await state.set_state(Form.Menu_Driver)
        else:
            menu = get_menu_Passenger_markup()
            await state.set_state(Form.Menu_Passenger)

        await message.answer("You have already reviewed this user.", reply_markup=menu)
    else:
        await message.answer("Please rate the driver from 1-5:", reply_markup=rating)
        await state.set_state(Form.Rating)


@form_router.message(Form.PassengerReview)
async def process_review(message: Message, state: FSMContext):
    rating = get_rating_markup()
    reviewee_id = message.text.split("\n")[0].split(":")[1].strip()
    await state.update_data(reviewee = reviewee_id)
    if redis_conn.exists(f"rating:{message.from_user.id}:{reviewee_id}"):
        menu = ''
        user_key = f'user:{message.from_user.id}'
        user_data = redis_conn.hgetall(user_key)
        await state.clear()
        
        if user_data.get('role') == "driver":
            menu = get_menu_Driver_markup()
            await state.set_state(Form.Menu_Driver)
        else:
            menu = get_menu_Passenger_markup()
            await state.set_state(Form.Menu_Passenger)

        await message.answer("You have already reviewed this user.", reply_markup=menu)
    await message.answer("Please rate the passenger from 1-5:", reply_markup=rating)
    await state.set_state(Form.Rating)


@form_router.message(Form.Rating)
async def process_rating(message: Message, state: FSMContext):
    reviewer_id = message.from_user.id
    data = await state.get_data()
    reviewee_id = data['reviewee']
    rating_key = f"rating:{reviewer_id}:{reviewee_id}"
    menu = ''
    user_key = f'user:{reviewer_id}'
    user_data = redis_conn.hgetall(user_key)
    await state.clear()
    
    if user_data.get('role') == "driver":
        menu = get_menu_Driver_markup()
        await state.set_state(Form.Menu_Driver)
    else:
        menu = get_menu_Passenger_markup()
        await state.set_state(Form.Menu_Passenger)

    await message.answer("Thank you for your feedback!", reply_markup=menu)
    redis_conn.hset(rating_key, "rating", message.text.strip())


####################################
# View Book History - driver
####################################

@form_router.message(Form.Menu_Driver, F.text.casefold() == "view book history")
async def view_book_history(message: Message, state: FSMContext):
    books = redis_conn.keys("book:*")
    menu = get_menu_Driver_markup()
    await state.set_state(Form.Menu_Driver)
    if len(books) == 0:
        await message.answer("There are no books at the moment.",reply_markup=menu)
    else:
        Keys = []
        
        for book in books:
            book_data = redis_conn.hgetall(book)
            button = KeyboardButton(text=f"Book Id: {book_data['book_id']}\nLocation: {book_data['location']}\nDestination: {book_data['destination']}")
            if book_data['driver_id'] == str(message.from_user.id) and book_data['status'] == "completed":
                Keys.append(button)
        
        if len(Keys) == 0:
            await message.answer("There are no books at the moment.")
        else:
            await message.answer("Here are the list of books you have completed:")
            for key in Keys:
                await message.answer(key.text + "\n")

        
        await message.answer("======================", reply_markup=menu)


####################################
# View Book History - passenger
####################################

@form_router.message(Form.Menu_Passenger, F.text.casefold() == "view book history")
async def view_book_history(message: Message, state: FSMContext):
    books = redis_conn.keys("book:*")
    menu = get_menu_Passenger_markup()
    await state.set_state(Form.Menu_Passenger)
    if len(books) == 0:
        await message.answer("There are no books at the moment.", reply_markup=menu)
    else:
        Keys = []
        for book in books:
            book_data = redis_conn.hgetall(book)
            button = KeyboardButton(text=f"Book Id: {book_data['book_id']}\nLocation: {book_data['location']}\nDestination: {book_data['destination']}")
            if book_data['passenger_id'] == str(message.from_user.id) and book_data['status'] == "completed":
                Keys.append(button)
        
        if len(Keys) == 0:
            await message.answer("There are no books at the moment.")
        else:
            await message.answer("Here are the list of books you have completed:")
            for key in Keys:
                await message.answer(key.text + "\n")
        
    
    await message.answer("======================", reply_markup=menu)


async def estimate_time_distance():
    distance = random.randint(5, 100)
    curr = datetime.now()
    minu = random.randint(1, 60)
    delta = timedelta(minutes=minu)
    estim = curr + delta
    return distance, estim.strftime("%I:%M %p")

async def get_all_drivers():
    drivers = []
    all_keys = redis_conn.keys("user:*")
    
    for key in all_keys:
        user_data = redis_conn.hgetall(key)
        if user_data.get("role") == "driver" and user_data.get("status") == "available":
            drivers.append(int(user_data["id"]))

    return drivers

async def get_all_passengers():
    passengers = []
    all_keys = redis_conn.keys("user:*")
    
    for key in all_keys:
        user_data = redis_conn.hgetall(key)
        if user_data.get("role") == "passenger":
            passengers.append(int(user_data["id"]))

    return passengers

async def main():
    bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    logging.basicConfig(level=logging.INFO)
    dp.include_router(form_router)

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())