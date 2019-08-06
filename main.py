# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import db
import helpers
import constants as c
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    update.message.reply_text(c.TEXTS['START'])


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def connect(bot, update):
    update.message.reply_text(c.TEXTS['INSTRUCTION'], disable_web_page_preview=True)


def enable_categories_button(chat_id=None, callback_query=None, bot=None):
    keyboard = [[InlineKeyboardButton(c.TEXTS['CATEGORIES_OFFER_BUTTON'], callback_data='categories_enable')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if callback_query:
        callback_query.edit_message_text(text=c.TEXTS['CATEGORIES_OFFER'], reply_markup=reply_markup)
    else:
        bot.send_message(chat_id=chat_id, text=c.TEXTS['CATEGORIES_OFFER'], reply_markup=reply_markup)


def list_categories(chat_id, callback_query=None, bot=None):
    categories = db.get_user_categories(chat_id)

    keyboard = [
        [
            InlineKeyboardButton('[x] {title}'.format(title=category['title']),
                                 callback_data='categories_del_{id}'.format(id=category['id']))
        ] for category in categories
        ]
    keyboard.append([InlineKeyboardButton(c.TEXTS['CATEGORIES_ADD_BUTTON'], callback_data='categories_add')])
    keyboard.append([InlineKeyboardButton(c.TEXTS['CATEGORIES_DISABLE_BUTTON'], callback_data='categories_disable')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = c.TEXTS['CATEGORIES_LIST'].format(total_categories=len(categories))

    if callback_query:
        callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def registration_completed(chat_id=None, callback_query=None, bot=None):
    if callback_query:
        callback_query.edit_message_text(text=c.TEXTS['REGISTRATION_COMPLETED'], reply_markup=None)
    else:
        bot.send_message(chat_id=chat_id, text=c.TEXTS['REGISTRATION_COMPLETED'])

    bot.send_message(chat_id=chat_id, text=c.TEXTS['TEXT_MESSAGE_EXAMPLE'])
    return enable_categories_button(chat_id=chat_id, bot=bot)


def on_message(bot, update):
    chat_id = update.message.chat_id
    text = update.message.text

    user_data = db.get_user_data(chat_id)
    state = user_data.get('state', None)

    if state is None:
        state = c.DEFAULT_STATE
        db.set_user_state(chat_id, state)

    state = state.decode('utf-8')

    if state == 'sheet_registration':
        worksheets = helpers.get_worksheets(text)

        if worksheets is not None:
            db.set_user_field(chat_id, 'document', text)
            db.set_user_state(chat_id, 'worksheet_selection')

            keyboard = [[InlineKeyboardButton(ws.title, callback_data=ws.id)] for ws in worksheets]
            keyboard.append([InlineKeyboardButton(c.TEXTS['CREATE_NEW_WORKSHEET'], callback_data='None')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            return update.message.reply_text(c.TEXTS['WORKSHEET_SELECTION'], reply_markup=reply_markup)
        else:
            return update.message.reply_text(c.TEXTS['DOCUMENT_VALIDATION_ERROR'])
    elif state == 'worksheet_creation':
        ws = helpers.create_worksheet(user_data[b'document'], text)

        db.set_user_field(chat_id, 'worksheet', ws.id)
        db.set_user_state(chat_id, 'ready')

        return registration_completed(chat_id=chat_id, bot=bot)
    elif state == 'category_add':
        db.set_user_state(chat_id, 'ready')
        db.add_user_category(chat_id, text)
        return list_categories(chat_id, bot=bot)
    elif state == 'ready':
        # ready to receive new spendings
        data = helpers.parse_new_spendings(text)

        if not data:
            return update.message.reply_text(c.TEXTS['ERROR_PARSING_SPENDINGS'])

        message = update.message.reply_text(c.TEXTS['STORING_SPENDINGS_IN_PROGRESS'])
        message_id = message.message_id

        db.store_user_spendings(chat_id, message_id, data)  # background processing starts after this
        return



def on_photo(bot, update):
    pass


def on_callback_query(bot, update):
    callback_query = update.callback_query
    query = callback_query.data

    chat_id = callback_query.from_user.id

    user_data = db.get_user_data(chat_id)
    state = user_data[b'state'].decode('utf-8')

    document = user_data[b'document']
    print(query)
    print(state)

    if query == 'empty':
        return

    if state == 'worksheet_selection':
        if query == 'None':
            db.set_user_state(chat_id, 'worksheet_creation')
            return callback_query.edit_message_text(text=c.TEXTS['WORKSHEET_CREATION'], reply_markup=None)

        if helpers.validate_worksheet(document.decode('utf-8'), query):
            db.set_user_field(chat_id, 'worksheet', query)

            if not helpers.is_worksheet_empty(document.decode('utf-8'), query):
                db.set_user_state(chat_id, 'configuring_worksheet')

                keyboard = [
                    [InlineKeyboardButton(c.TEXTS['REWRITE_WORKSHEET'], callback_data='clear')],
                    [InlineKeyboardButton(c.TEXTS['APPEND_WORKSHEET'], callback_data='append')]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                return callback_query.edit_message_text(text=c.TEXTS['WORKSHEET_CONFIGURATION'],
                                                        reply_markup=reply_markup)

            db.set_user_state(chat_id, 'ready')
            return registration_completed(chat_id=chat_id, bot=bot, callback_query=callback_query)
        else:
            return callback_query.edit_message_text(text='Error')
    elif state == 'configuring_worksheet':
        if query == 'clear':
            helpers.clear_worksheet(document.decode('utf-8'), user_data[b'worksheet'])

        return registration_completed(chat_id=chat_id, bot=bot, callback_query=callback_query)
    elif query.startswith('categories_'):
        query = query[11:]

        if query == 'enable':
            db.set_user_field(chat_id, 'categories_enabled', True)
            return list_categories(chat_id, callback_query=callback_query)
        elif query == 'disable':
            db.set_user_field(chat_id, 'categories_enabled', False)
            return enable_categories_button(callback_query=callback_query)
        elif query == 'add':
            db.set_user_state(chat_id, 'category_add')
            return callback_query.edit_message_text(text=c.TEXTS['CATEGORIES_INPUT_NEW'], reply_markup=None)
        elif query.startswith('del_'):
            category_to_remove = query[4:]
            db.remove_user_category(chat_id, category_to_remove)
            return list_categories(chat_id, callback_query=callback_query)


def main():
    """Run bot."""
    updater = Updater(c.TOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('connect', connect))
    dp.add_handler(MessageHandler(Filters.text, on_message))
    dp.add_handler(MessageHandler(Filters.photo, on_photo))
    dp.add_handler(CallbackQueryHandler(on_callback_query))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
