"""
Handler for image conversion and artistic effects.
Provides various image processing options via interactive buttons.
"""

import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.utils.image_processing import (
    create_spiral_image,
    create_square_grid_image,
    create_hexagon_grid_image,
    create_triangle_grid_image,
    create_diamond_grid_image,
    create_pentagon_grid_image,
    create_double_spiral_image,
    save_image_to_bytes
)

logger = logging.getLogger(__name__)
router = Router()


class ImageProcessingState(StatesGroup):
    """States for image processing workflow"""
    waiting_for_image = State()
    waiting_for_effect_choice = State()
    waiting_for_spiral_params = State()
    waiting_for_grid_params = State()
    waiting_for_second_image = State()


@router.message(Command("phone_converter"))
async def start_image_converter(message: Message, state: FSMContext):
    """Start the image converter command"""
    try:
        await message.answer(
            "🖼️ **Конвертер изображений**\n\n"
            "Отправьте изображение, которое вы хотите обработать.",
            parse_mode="Markdown"
        )
        await state.set_state(ImageProcessingState.waiting_for_image)
    except Exception as e:
        logger.error(f"Error in start_image_converter: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(ImageProcessingState.waiting_for_image, F.photo)
async def receive_image(message: Message, state: FSMContext):
    """Receive image from user"""
    try:
        # Download the photo
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        
        # Create temporary file
        temp_dir = "./downloads"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"temp_image_{message.from_user.id}.jpg")
        
        # Download file
        await message.bot.download_file(file_info.file_path, temp_file)
        
        # Store file path in state
        await state.update_data(image_path=temp_file)
        
        # Show effect options
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌀 Спиральная обработка", callback_data="effect_spiral")],
            [InlineKeyboardButton(text="⬜ Квадратная сетка", callback_data="effect_square")],
            [InlineKeyboardButton(text="⬡ Шестиугольная сетка", callback_data="effect_hexagon")],
            [InlineKeyboardButton(text="🔺 Треугольная сетка", callback_data="effect_triangle")],
            [InlineKeyboardButton(text="💎 Ромбовая сетка", callback_data="effect_diamond")],
            [InlineKeyboardButton(text="⬠ Пятиугольная сетка", callback_data="effect_pentagon")],
            [InlineKeyboardButton(text="🎨 Двойная спираль", callback_data="effect_double_spiral")],
        ])
        
        await message.answer(
            "✅ Изображение получено!\n\n"
            "Выберите тип обработки:",
            reply_markup=keyboard
        )
        await state.set_state(ImageProcessingState.waiting_for_effect_choice)
    
    except Exception as e:
        logger.error(f"Error in receive_image: {e}")
        await message.answer("❌ Ошибка при загрузке изображения. Попробуйте еще раз.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_spiral")
async def choose_spiral_params(callback: CallbackQuery, state: FSMContext):
    """Choose spiral parameters"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Тонкая (1)", callback_data="spiral_thick_1")],
            [InlineKeyboardButton(text="Средняя (2)", callback_data="spiral_thick_2")],
            [InlineKeyboardButton(text="Толстая (3)", callback_data="spiral_thick_3")],
            [InlineKeyboardButton(text="Очень толстая (4)", callback_data="spiral_thick_4")],
        ])
        
        await callback.message.edit_text(
            "🌀 **Спиральная обработка**\n\n"
            "Выберите толщину линии спирали:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(ImageProcessingState.waiting_for_spiral_params)
    except Exception as e:
        logger.error(f"Error in choose_spiral_params: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(ImageProcessingState.waiting_for_spiral_params, F.data.startswith("spiral_thick_"))
async def process_spiral_image(callback: CallbackQuery, state: FSMContext):
    """Process image with spiral effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        thickness_map = {
            "spiral_thick_1": 1,
            "spiral_thick_2": 2,
            "spiral_thick_3": 3,
            "spiral_thick_4": 4,
        }
        thickness = thickness_map.get(callback.data, 2)
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_spiral_image(
            image_path,
            spiral_thickness=thickness,
            spiral_turns=50,
            size=300,
            n_shades=16,
            invert=False
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Спиральная обработка завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_spiral_image: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_square")
async def process_square_grid(callback: CallbackQuery, state: FSMContext):
    """Process image with square grid effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_square_grid_image(
            image_path,
            grid_size=50,
            size=300,
            n_shades=16,
            invert=False
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Квадратная сетка завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_square_grid: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_hexagon")
async def process_hexagon_grid(callback: CallbackQuery, state: FSMContext):
    """Process image with hexagon grid effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_hexagon_grid_image(
            image_path,
            grid_size=50,
            size=300,
            n_shades=16,
            invert=False
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Шестиугольная сетка завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_hexagon_grid: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_triangle")
async def process_triangle_grid(callback: CallbackQuery, state: FSMContext):
    """Process image with triangle grid effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_triangle_grid_image(
            image_path,
            grid_size=50,
            size=300,
            n_shades=16,
            invert=False
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Треугольная сетка завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_triangle_grid: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_diamond")
async def process_diamond_grid(callback: CallbackQuery, state: FSMContext):
    """Process image with diamond grid effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_diamond_grid_image(
            image_path,
            grid_size=50,
            size=300,
            n_shades=16,
            invert=False
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Ромбовая сетка завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_diamond_grid: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_pentagon")
async def process_pentagon_grid(callback: CallbackQuery, state: FSMContext):
    """Process image with pentagon grid effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_pentagon_grid_image(
            image_path,
            grid_size=50,
            size=300,
            n_shades=16,
            invert=False
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Пятиугольная сетка завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_pentagon_grid: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.callback_query(ImageProcessingState.waiting_for_effect_choice, F.data == "effect_double_spiral")
async def process_double_spiral(callback: CallbackQuery, state: FSMContext):
    """Process image with double spiral effect"""
    try:
        await callback.message.edit_text("⏳ Обработка изображения...")
        
        data = await state.get_data()
        image_path = data.get("image_path")
        
        result_image = create_double_spiral_image(
            image_path,
            image_path2=None,
            spiral_thickness=2,
            spiral_turns=50,
            size=300,
            n_shades=16
        )
        
        image_bytes = save_image_to_bytes(result_image)
        
        await callback.message.bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(image_bytes, filename="processed_image.png"),
            caption="✅ Двойная спираль завершена!"
        )
        
        await callback.message.delete()
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in process_double_spiral: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке изображения.")
        await state.clear()


@router.message(ImageProcessingState.waiting_for_image)
async def invalid_input(message: Message):
    """Handle invalid input"""
    await message.answer("❌ Пожалуйста, отправьте изображение (фото).")

