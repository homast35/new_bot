import asyncio
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from googletrans import Translator
from random import choices

translator = Translator()

# FSM
class RecipeStates(StatesGroup):
    waiting_for_category_count = State()
    waiting_for_category_choice = State()
    waiting_for_recipes = State()

API_BASE = "https://www.themealdb.com/api/json/v1/1/"

# ----------  Первый обработчик ----------
async def category_search_random(message: types.Message, state: FSMContext):
    try:
        count = int(message.get_args())
    except ValueError:
        await message.answer("Пожалуйста, укажите число рецептов после команды.")
        return

    await state.update_data(recipe_count=count)

    # Получаем список категорий
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}list.php?c=list") as resp:
            data = await resp.json()
            categories = [c['strCategory'] for c in data['meals']]

    # Создаём клавиатуру
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[KeyboardButton(c) for c in categories])

    await message.answer("Выберите категорию:", reply_markup=keyboard)
    await RecipeStates.waiting_for_category_choice.set()


# ----------  Второй обработчик ----------
async def choose_category(message: types.Message, state: FSMContext):
    category = message.text
    data = await state.get_data()
    count = data.get('recipe_count', 1)

    # Получаем рецепты по категории
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}filter.php?c={category}") as resp:
            data = await resp.json()
            meals = data['meals']

    selected_meals = choices(meals, k=min(count, len(meals)))
    ids = [m['idMeal'] for m in selected_meals]
    names = [translator.translate(m['strMeal'], dest='ru').text for m in selected_meals]

    await state.update_data(recipe_ids=ids)

    # Создаём сообщение с рецептом
    response_text = "\n".join(names)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Получить рецепты"))

    await message.answer(f"Выбранные рецепты:\n{response_text}", reply_markup=keyboard)
    await RecipeStates.waiting_for_recipes.set()


# ----------  Третий обработчик ----------
async def send_recipes(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ids = data.get('recipe_ids', [])

    async with aiohttp.ClientSession() as session:
        tasks = []
        for recipe_id in ids:
            tasks.append(fetch_recipe(session, recipe_id))
        recipes = await asyncio.gather(*tasks)

    for recipe in recipes:
        # Переводим название и инструкцию
        name = translator.translate(recipe['strMeal'], dest='ru').text
        instructions = translator.translate(recipe['strInstructions'], dest='ru').text

        # Список ингредиентов
        ingredients = []
        for i in range(1, 21):
            ing = recipe.get(f"strIngredient{i}")
            measure = recipe.get(f"strMeasure{i}")
            if ing and ing.strip():
                translated_ing = translator.translate(ing, dest='ru').text
                ingredients.append(f"{translated_ing} - {measure.strip()}")

        ingredients_text = ", ".join(ingredients)
        await message.answer(f"<b>{name}</b>\n\nРецепт:\n{instructions}\n\nИнгредиенты: {ingredients_text}")

    await state.finish()


async def fetch_recipe(session, recipe_id):
    async with session.get(f"{API_BASE}lookup.php?i={recipe_id}") as resp:
        data = await resp.json()
        return data['meals'][0]


# ---------- Регистрация обработчиков ----------
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(category_search_random, commands=['category_search_random'], state="*")
    dp.register_message_handler(choose_category, state=RecipeStates.waiting_for_category_choice)
    dp.register_message_handler(send_recipes, lambda message: message.text == "Получить рецепты", state=RecipeStates.waiting_for_recipes)