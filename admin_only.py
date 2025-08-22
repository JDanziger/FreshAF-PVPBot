# -*- coding: utf-8 -*-
import logging
from time import sleep
from zipapp import MAIN_TEMPLATE

logging.basicConfig(filename='log.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('Info')
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from datetime import timedelta
import pvp_poll
import trainernames
import database
import language_support
import copy

#The language strings
jsonresponse = language_support.responses
#Maintenance Mode
maintMode = False
#The current version of software
ver ="1.6"

"""
This method will discover who are the admins in the group
"""
def is_admin(the_user, userlist):
    if the_user in (admin.user for admin in userlist):
        return True
    else:
        return False

"""
This method will show the current version of Software
"""
def version(update, context):
    #Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]

    # Try to delete the /pvp command
    try:
        context.bot.delete_message(chat_id=update.message.chat_id,
                                   message_id=update._effective_message['message_id'])
    # If we cannot delete the command, the bot probably doesn't have admin rights
    except:
        context.bot.send_message(chat_id=update.message.chat_id, text=responses['pvp_cant_delete'])
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id,
                    update._effective_message['message_id'])

    if not is_admin(update.effective_user, update.effective_chat.get_administrators()):
        return

    # Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]

    response = responses['version'] + ver
    context.bot.send_message(chat_id=update.message.chat_id, text=response)

"""
This function is created to show the admins all available admin commands
"""
def admin_help(update, context):
    # Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]

    # Try to delete the /adminhelp command
    try:
        context.bot.delete_message(chat_id=update.message.chat_id,
                                   message_id=update._effective_message['message_id'])
    # If we cannot delete the command, the bot probably doesn't have admin rights
    except:
        context.bot.send_message(chat_id=update.message.chat_id, text=responses['pvp_cant_delete'])
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id,
                    update._effective_message['message_id'])

    if not is_admin(update.effective_user, update.effective_chat.get_administrators()):
        return
    try:
        context.bot.send_message(parse_mode='Markdown', chat_id=update.message.chat_id, text=responses['adminhelp'])
    except Exception as e:
        context.bot.send_message(chat_id=update.message.chat_id, text=responses['pvp_cant_delete'])
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id,
                    update._effective_message['message_id'])

"""
This function is created to allow the maintenance of the bot.  It will halt new requests
and also delete all active polls
"""

def maintenance(update, context):
    global maintMode
    active_chats = []
    active_polls = []

    # Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]

    # Try to delete the /maint command
    try:
        context.bot.delete_message(chat_id=update.message.chat_id,
                                   message_id=update._effective_message['message_id'])
    # If we cannot delete the command, the bot probably doesn't have admin rights
    except:
        context.bot.send_message(chat_id=update.message.chat_id, text=responses['pvp_cant_delete'])
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id,
                    update._effective_message['message_id'])

    if is_admin(update.effective_user, update.effective_chat.get_administrators()):
        maintMode = True
    else:
        return

    # Gather all the chat groups with active polls
    for polls in pvp_poll.pvprequests:
        if polls[1] not in active_chats:
            active_chats.append(polls[1])

        active_polls.append(polls)

    for item in active_chats:
        context.bot.send_message(parse_mode='Markdown', chat_id=item, text=responses['maintwarn'])

    sleep(120) # Give the Board members 2 minutes 2 finish up existing polls

    for item in active_chats:
        context.bot.send_message(parse_mode='Markdown', chat_id=item, text=responses['maint'])

    for polls in active_polls:
        try:
            context.bot.delete_message(chat_id=polls[1], message_id=polls[0])
        except:
            logger.info('Cannot delete message Chat:%s MessageID:%s', polls[1], polls[0])

    pvp_poll.pvprequests.clear()
    pvp_poll.competitors.clear()


def floatall(update, context):
    # Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]

    # Try to delete the /floatall command
    try:
        context.bot.delete_message(chat_id=update.message.chat_id,
                                   message_id=update._effective_message['message_id'])
    # If we cannot delete the command, the bot probably doesn't have admin rights
    except:
        context.bot.send_message(chat_id=update.message.chat_id, text=responses['pvp_cant_delete'])
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id,
                    update._effective_message['message_id'])

    if not is_admin(update.effective_user, update.effective_chat.get_administrators()):
        return

    pcopy = copy.deepcopy(dict(pvp_poll.pvprequests))

    # Iterate over each open request and see how old it is
    for pvpitem in pcopy:
        language = database.get_language(pvpitem[1])
        responses = jsonresponse[language]
        fighter_count = 0
        balloons = ""

        try:
            context.bot.delete_message(chat_id=pvpitem[1], message_id=pvpitem[0])
            logger.info("Deletion to enable message float %s", pvpitem)
        except:
            # if the delete message failed - the poll is most likely gone
            # in which case, we dont want to float again.  So pop the queues and go to next request
            logger.info("PvP request was already deleted (by an admin?): %s", pvpitem)
            pvp_poll.pvprequests.pop(pvpitem)
            pvp_poll.competitors.pop(pvpitem)
            continue

        match pvp_poll.pvprequests[pvpitem]['float']:
            case 0:
                balloons = ""
            case 1:
                balloons = "\U0001F388" + "\U0001F388"  + "\U0001F388"
            case 2:
                balloons = "\U0001F388" + "\U0001F388"
            case 3 | 4:
                balloons = "\U0001F388"

        # Re-Send the poll and add the buttons to it
        response = pvp_poll.pvprequests[pvpitem]['text'] + " " + balloons

        # Send out the new poll
        try:
            bot_message = context.bot.send_message(parse_mode='Markdown', chat_id=pvpitem[1],
                                                    text=response, disable_notification=True,
                                                    reply_markup=pvp_poll.pvp_keyboard(responses))

            #Update the new message key in the requests and delete the old key
            pvp_poll.pvprequests[bot_message.message_id, bot_message.chat_id] = pvp_poll.pvprequests.pop(pvpitem)
        except Exception as e:
            bot_message = None
            logger.info("Could not send poll: %s", pvpitem)

        for fighter in pvp_poll.competitors[pvpitem]:
            fighter_count += 1
            userid = fighter['id']
            name = trainernames.get_trainername(userid)

            # Format the users name
            if name is not None:
                response += "\n- [" + name + "](tg://user?id=" + str(userid) + ")"
            else:
                response += '\n- ' + fighter['name']

        if bot_message is not None:
            #Update the new competitors key in the requests and delete the old key
            pvp_poll.competitors[bot_message.message_id, bot_message.chat_id] = pvp_poll.competitors.pop(pvpitem)
        else:
            logger.info("Could not update competitors key list: Issue with bot_message: %s", bot_message)

        if fighter_count > 0:
            context.bot.edit_message_text(parse_mode='Markdown', chat_id=bot_message.chat_id,
                                            message_id=bot_message.message_id,
                                            text=response,
                                            reply_markup=pvp_poll.pvp_keyboard(jsonresponse[language]))


