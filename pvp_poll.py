# -*- coding: utf-8 -*-
import logging
from zipapp import MAIN_TEMPLATE

logging.basicConfig(filename='log.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('Info')
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from datetime import timedelta
import trainernames
import database
import language_support
import copy

#A list of currently open pvp requests
pvprequests = {}
#All competitors for each request
competitors = {}
#The language strings
jsonresponse = language_support.responses
#The current version of software
ver ="1.5"
#Maintenance Mode
maintMode = False

"""
This method will show the current version of Software
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

    # Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]

    response = responses['version'] + ver
    context.bot.send_message(chat_id=update.message.chat_id, text=response)

"""
This method transforms /pvp into a request with clickable buttons
"""
def pvp(update, context):
    #Load the language settings for this group
    language = database.get_language(update.message.chat_id)
    responses = jsonresponse[language]
    duplicate_entry = False

    #Try to delete the /pvp command
    try:
        context.bot.delete_message(chat_id=update.message.chat_id,
                          message_id=update._effective_message['message_id'])
    #If we cannot delete the command, the bot probably doesn't have admin rights
    except:
        context.bot.send_message(chat_id=update.message.chat_id, text=responses['pvp_cant_delete'])
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id, update._effective_message['message_id'])

    if maintMode:
        try:
            direct_message = jsonresponse[language]['maint'] + "\n\[" + update.effective_chat.title + "]"
            context.bot.send_message(parse_mode='Markdown',
                                     chat_id=update.effective_user['id'],
                                     text=direct_message)
        except:
            logger.info("Cannot initiate private conversation with %s",
                        pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
        return

   # Check to see if the user is creating multiple polls in same chat board
    for val in pvprequests.keys():
        if update.message.chat_id in val:
            if update.effective_user.id == pvprequests[val]['user']:
                duplicate_entry = True
                try:
                    direct_message = jsonresponse[language]['dup_poll'] + "\n\[" + update.effective_chat.title + "]"
                    context.bot.send_message(parse_mode='Markdown',
                                    chat_id=pvprequests[val]['user'],
                                    text=direct_message)
                except:
                    logger.info("Cannot initiate private conversation with %s",
                                pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
                break

    if not duplicate_entry:
        #Check, if we have a name for this telegram user
        name = trainernames.get_trainername(update.effective_user.id)
        #Format the name properly if we have a user. Otherwise, we just take the users telegram name
        if name is not None:
            response = "[" + name + "](tg://user?id=" + str(update.effective_user.id) + ")" + responses['poll']
        else:
            response = update.effective_user.name + responses['poll']
        #Does the poll provide any arguments such as league
        if len(context.args) > 0:
            response += responses['pollinfo'] + ' '.join(context.args[0:])
            #Did the user provide information without specifying the league

        #Send the poll and add the buttons to it
        bot_message = context.bot.send_message(parse_mode='Markdown', chat_id=update.message.chat_id, text=response, reply_markup=pvp_keyboard(responses))
        logger.info('PvP request by %s (MessageID: %s, ChatID: %s) with arguments %s', update._effective_user.username, bot_message.message_id, bot_message.chat_id, context.args)
        #Store the message and create a list for the competitors
        pvprequests[bot_message.message_id, bot_message.chat_id] = {'user' : update.effective_user.id, 'date' : datetime.now(), 'text' : response, 'float' : 0, 'title' : update.effective_chat.title}
        competitors[bot_message.message_id, bot_message.chat_id] = []

"""
If a user clicks on the fight button, we will either add or revoke him from the poll
"""
def add_competitor(update, context):
    #Get the info about the message that was clicked
    query = update.callback_query
    #Get the current language 
    language = database.get_language(update._effective_chat.id)

    # Retrieve the user object and his name, if he has one defined
    user = update.effective_user
    name = trainernames.get_trainername(user.id)
    balloons = ""

    # Format the users name
    if name is not None:
        direct_message = "[" + name + "](tg://user?id=" + str(user.id) + ")"
    else:
        direct_message = '@' + user.username

    #remove user from competitor list
    if update.effective_user in competitors[query.message.message_id, update._effective_chat.id]:
        logger.info('%s user already in list %s', update.effective_user.username, pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
        return

    #add user too competitor list
    else:
        logger.info('%s joins from the PvP request from %s', update.effective_user.username, pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
        competitors[query.message.message_id, update._effective_chat.id].append(update.effective_user)

        direct_message += (jsonresponse[language]['accepted'] + "\n\[" + update.effective_chat.title + "]")

        #Try to send a private notification to the creator of the poll
        try:
            context.bot.send_message(parse_mode='Markdown', chat_id=pvprequests[update.effective_message.message_id, update.effective_chat.id]['user'], text=direct_message)
            logger.info("Sent a private notification to %s", pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
        #If the creator doesn't have a private chat with the bot we cannot send him a private notification
        except:
            logger.info("Cannot initiate private conversation with %s", pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
    
    """ Edit the pvp request and add the competitor"""
    #Get the initial request
    if pvprequests[update.effective_message.message_id, update.effective_chat.id]['float'] != 0:
        for i in range(pvprequests[update.effective_message.message_id, update.effective_chat.id]['float'], 4):
            balloons += "\U0001F388"

    response = pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'] + balloons

    #Add the name of each diruser to the request
    for user in competitors[query.message.message_id, update._effective_chat.id]:
        name = trainernames.get_trainername(user.id)
        if name is not None:
            response += "\n- [" + name + "](tg://user?id=" + str(update.effective_user.id) + ")"
        else:
            response += '\n- ' + user.name    
    #Update the message
    context.bot.edit_message_text(parse_mode='Markdown', chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          text=response,
                          reply_markup=pvp_keyboard(jsonresponse[language]))


""" If a user clicks on leave, we want to delete them from the current poll they signed up for"""
def remove_competitor(update, context):
    query = update.callback_query
    #Get the current language
    language = database.get_language(update._effective_chat.id)

    # Retrieve the user object and his name, if he has one defined
    user = update.effective_user
    name = trainernames.get_trainername(user.id)
    balloons = ""

    # Format the users name
    if name is not None:
        direct_message = "[" + name + "](tg://user?id=" + str(user.id) + ")"
    else:
        direct_message = '@' + user.username

    # remove user from competitor list
    if update.effective_user in competitors[query.message.message_id, update._effective_chat.id]:
        logger.info('%s revokes the PvP request from %s', update.effective_user.username,
                    pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])

        direct_message += jsonresponse[language]['removed'] + "\n\[" + update.effective_chat.title + "]"
        competitors[query.message.message_id, update._effective_chat.id].remove(update.effective_user)

        try:
            context.bot.send_message(parse_mode='Markdown',
                                    chat_id=pvprequests[update.effective_message.message_id, update.effective_chat.id][
                                      'user'],
                                     text=direct_message)
        except:
            logger.info("Cannot initiate private conversation with %s", pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'].split()[0])
    else:
        return

    """ Edit the pvp request and update the competitors"""
    #Get the initial request
    if pvprequests[update.effective_message.message_id, update.effective_chat.id]['float'] != 0:
        for i in range(pvprequests[update.effective_message.message_id, update.effective_chat.id]['float'], 4):
            balloons += "\U0001F388"

    response = pvprequests[update.effective_message.message_id, update.effective_chat.id]['text'] + balloons

    #Add the name of each diruser to the request
    for user in competitors[query.message.message_id, update._effective_chat.id]:
        name = trainernames.get_trainername(user.id)
        if name is not None:
            response += "\n- [" + name + "](tg://user?id=" + str(update.effective_user.id) + ")"
        else:
            response += '\n- ' + user.name
    #Update the message
    context.bot.edit_message_text(parse_mode='Markdown', chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          text=response,
                          reply_markup=pvp_keyboard(jsonresponse[language]))

""" If a user clicks on delete, we want to delete this poll and all the information that we held with it"""
def delete_poll(update, context):
    #Try to remove the request
    try:
        req = pvprequests.pop((update.effective_message.message_id,update.effective_chat.id))
        comp = competitors.pop((update.effective_message.message_id, update.effective_chat.id))
    #If we don't have a request with the message id and the chat id, we just throw an error
    except:
        logger.info('No PVP-request stored by %s, %s', update.effective_user.username, update.effective_user.id)
        logger.warning('(MessageID: %s, ChatID: %s)\nOpen requests:', update.effective_message.message_id, update.effective_chat.id)
        for pvp in pvprequests:
            logger.info(pvp)
        return
    #Checks, if the user is indeed the creator of the message
    if req['user'] != update.effective_user.id:
        #The user did not create the request - add it back to the open requests
        logger.info('%s (%s) has no permission to delete the pvp request (MessageID: %s, ChatID: %s)', update.effective_user.username, update.effective_user.id, update.effective_message.message_id, update.effective_chat.id)
        pvprequests[update.effective_message.message_id, update.effective_chat.id] = req
        competitors[update.effective_message.message_id, update.effective_chat.id] = comp
        return
    #The user is the owner of the message. Try to delete it
    query = update.callback_query
    logger.info('%s deleted his PvP request (MessageID: %s, ChatID: %s)', update.effective_user.username, update.effective_message.message_id, update.effective_chat.id)
    try:
        context.bot.delete_message(chat_id=query.message.chat_id, message_id=update.effective_message.message_id)    
    except:    
        logger.info('Cannot delete message Chat:%s MessageID:%s', update.message.chat_id, update._effective_message['message_id'])

"""
Just the button markup for fight, leave and delete
"""
def pvp_keyboard(response):
    keyboard = [[InlineKeyboardButton(response['fight'], callback_data='fight'),
                InlineKeyboardButton(response['leave'], callback_data='leave')],
                [InlineKeyboardButton(response['delete'], callback_data='delete')]]
    return InlineKeyboardMarkup(keyboard)

"""
There is also a new feature added that will delete the existing poll if 15 minutes and repost a max of 3 times
We call this the "float" feature.
"""
def float_poll(context):

    now = datetime.now()
    pcopy = copy.deepcopy(dict(pvprequests))

    # Iterate over each open request and see how old it is
    for pvpitem in pcopy:
        language = database.get_language(pvpitem[1])
        responses = jsonresponse[language]
        fighter_count = 0
        balloons = ""

        diff = (now - pvprequests[pvpitem]['date']).seconds

        # if the message was posted more than 15 minutes since last post or float, re-float it, max 3x
        if diff >= 600 + (600 * pvprequests[pvpitem]['float'] ):
            if pvprequests[pvpitem]['float'] < 3:
                pvprequests[pvpitem]['float'] += 1
                try:
                    context.bot.delete_message(chat_id=pvpitem[1], message_id=pvpitem[0])
                    logger.info("Deletion to enable message float %s", pvpitem)
                except:
                    # if the delete message failed - the poll is most likely gone
                    # in which case, we dont want to float again.  So pop the queues and go to next request
                    logger.info("PvP request was already deleted (by an admin?): %s", pvpitem)
                    pvprequests.pop(pvpitem)
                    competitors.pop(pvpitem)
                    continue

                for i in range(pvprequests[pvpitem]['float'], 4):
                    balloons += "\U0001F388"

                 # Re-Send the poll and add the buttons to it
                response = pvprequests[pvpitem]['text'] + " " + balloons

                # Send out the new poll
                try:
                    bot_message = context.bot.send_message(parse_mode='Markdown', chat_id=pvpitem[1],
                                                           text=response, disable_notification=True,
                                                           reply_markup=pvp_keyboard(responses))

                    #Update the new message key in the requests and delete the old key
                    pvprequests[bot_message.message_id, bot_message.chat_id] = pvprequests.pop(pvpitem)
                except:
                    bot_message = None
                    logger.info("Could not send poll: %s", pvpitem)

                for fighter in competitors[pvpitem]:
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
                    competitors[bot_message.message_id, bot_message.chat_id] = competitors.pop(pvpitem)
                else:
                    logger.info("Could not update competitors key list: Issue with bot_message: %s", bot_message)

                if fighter_count > 0:
                    context.bot.edit_message_text(parse_mode='Markdown', chat_id=bot_message.chat_id,
                                                message_id=bot_message.message_id,
                                                text=response,
                                                reply_markup=pvp_keyboard(jsonresponse[language]))

"""
We want to make sure, that messages will be deleted if they exist for over an hour
This is executed every ~5 minutes
"""    
def auto_delete(context):
    now = datetime.now()
    pcopy = dict(pvprequests)

    #Iterate over each open request and see how old it is
    for pvp_req in pcopy:
        language = database.get_language(pvp_req[1])
        responses = jsonresponse[language]

        diff = (now - pvprequests[pvp_req]['date']).seconds

        if diff > 2400:
            userid = pvprequests[pvp_req]['user']
            title = pvprequests[pvp_req]['title']
            arguments = pvprequests[pvp_req]['text'].split()[0]
            pvprequests.pop(pvp_req)
            competitors.pop((pvp_req[0], pvp_req[1]))

            try:
                logger.info("Auto delete pvp request: %s", pvp_req)
                context.bot.delete_message(chat_id=pvp_req[1], message_id=pvp_req[0])
            except:
                logger.info("PvP request was already deleted (by an admin?): %s", pvp_req)

            direct_message = responses['deleted_poll'] + "[" +  title +"]"
            try:
                context.bot.send_message(chat_id=userid, text=direct_message)
            except:
                logger.info("Cannot initiate private conversation with %s", arguments)

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

    # Try to delete the /pvp command
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
    for polls in pvprequests:
        if polls[1] not in active_chats:
            active_chats.append(polls[1])

        active_polls.append(polls)

    for item in active_chats:
        context.bot.send_message(chat_id=item, text=responses['maint'])

    for polls in active_polls:
        try:
            context.bot.delete_message(chat_id=polls[1], message_id=polls[0])
        except:
            logger.info('Cannot delete message Chat:%s MessageID:%s', polls[1], polls[0])

    pvprequests.clear()
    competitors.clear()

