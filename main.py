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


def on_message(bot, update):
    chat_id = update.message.chat_id
    text = update.message.text

    user_data = db.get_user_data(chat_id)
    state = user_data.get('state', None)

    if state is None:
        state = c.DEFAULT_STATE
        db.set_user_state(chat_id, state)

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
        ws = helpers.create_worksheet(user_data['document'], text)

        db.set_user_field(chat_id, 'worksheet', ws.id)
        db.set_user_state(chat_id, 'ready')

        return update.message.reply_text(c.TEXTS['REGISTRATION_COMPLETED'])
    elif state == 'ready':
        pass


def on_photo(bot, update):
    pass


def on_callback_query(bot, update):
    callback_query = update.callback_query
    query = callback_query.data

    chat_id = callback_query.from_user.id

    user_data = db.get_user_data(chat_id)
    state = user_data['state']

    document = user_data['document']

    if state == 'worksheet_selection':
        if query == 'None':
            db.set_user_state(chat_id, 'worksheet_creation')
            return callback_query.edit_message_text(text=c.TEXTS['WORKSHEET_CREATION'], reply_markup=None)

        if helpers.validate_worksheet(document, query):
            db.set_user_field(chat_id, 'worksheet', query)

            if not helpers.is_worksheet_empty(document, query):
                db.set_user_state(chat_id, 'configuring_worksheet')

                keyboard = [
                    [InlineKeyboardButton(c.TEXTS['REWRITE_WORKSHEET'], callback_data='clear')],
                    [InlineKeyboardButton(c.TEXTS['APPEND_WORKSHEET'], callback_data='append')]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                return callback_query.edit_message_text(text=c.TEXTS['WORKSHEET_CONFIGURATION'],
                                                        reply_markup=reply_markup)

            db.set_user_state(chat_id, 'ready')
            return callback_query.edit_message_text(text=c.TEXTS['REGISTRATION_COMPLETED'], reply_markup=None)
        else:
            return callback_query.edit_message_text(text='Error')
    elif state == 'configuring_worksheet':
        if query == 'clear':
            helpers.clear_worksheet(document, user_data['worksheet'])

        return callback_query.edit_message_text(text=c.TEXTS['REGISTRATION_COMPLETED'], reply_markup=None)


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
